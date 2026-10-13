import re
from collections import OrderedDict
from typing import Any

from database import run_query


_LOGISTICS_TABLES = (
    "logistics_sku",
    "logistics_container",
    "logistics_replenish",
    "logistics_shipment",
    "logistics_shipment_container_map",
)


def list_query_terms(query: str) -> list[str]:
    """Split user input into at most twenty non-empty search terms."""
    return [term.strip() for term in re.split(r"[\\\n,]+", query or "") if term.strip()][:20]


def validate_warehouse(warehouse: str | None, warehouses: list[str]) -> str | None:
    """Return a normalized warehouse or reject a value outside the known list."""
    normalized = (warehouse or "").strip()
    if not normalized:
        return None
    if normalized not in warehouses:
        raise ValueError(f"未知仓库: {normalized}")
    return normalized


def get_warehouses() -> dict:
    """Return the available warehouses and the number of distinct SKUs in each."""
    rows = run_query(
        """SELECT warehouse, COUNT(DISTINCT sku) AS sku_count
           FROM logistics_sku
          WHERE sku IS NOT NULL
            AND warehouse IS NOT NULL AND TRIM(warehouse) <> ''
          GROUP BY warehouse
          ORDER BY warehouse"""
    )
    return {
        "warehouses": rows,
        "default_warehouse": None,
    }


def search_logistics(query: str, warehouse: str | None) -> dict:
    """Resolve logistics profiles and load each related table independently."""
    terms = list_query_terms(query)
    normalized_warehouse = (warehouse or "").strip() or None
    empty_result = {
        "items": [],
        "query": query,
        "warehouse": normalized_warehouse,
    }
    if not terms and normalized_warehouse is None:
        return empty_result

    warehouse_data = get_warehouses()
    known_warehouses = _warehouse_names(warehouse_data)
    normalized_warehouse = validate_warehouse(normalized_warehouse, known_warehouses)
    if not terms:
        empty_result["warehouse"] = normalized_warehouse
        return empty_result

    profile_rows = _resolve_profiles(terms, normalized_warehouse)
    selected_skus = _select_skus(profile_rows)
    if not selected_skus:
        return {
            "items": [],
            "query": query,
            "warehouse": normalized_warehouse,
        }

    selected_profiles = [
        row for row in profile_rows if _row_value(row, "sku") in selected_skus
    ]
    details = _load_detail_rows(selected_skus, normalized_warehouse)
    items = _group_results(selected_profiles, details, normalized_warehouse)
    return {
        "items": items,
        "query": query,
        "warehouse": normalized_warehouse,
    }


def _warehouse_names(warehouse_data: dict) -> list[str]:
    entries = warehouse_data.get("warehouses", []) if isinstance(warehouse_data, dict) else []
    names = []
    for entry in entries:
        if isinstance(entry, dict):
            value = entry.get("warehouse")
        else:
            value = entry
        if value is not None and str(value).strip():
            names.append(str(value).strip())
    return names


def _resolve_profiles(terms: list[str], warehouse: str | None) -> list[dict]:
    placeholders, params = _bind_values("term", terms)
    params["warehouse"] = warehouse
    exact_rows = run_query(
        f"""SELECT *
              FROM logistics_sku
             WHERE (sku IN ({placeholders}) OR custom_sku IN ({placeholders}))
               AND (:warehouse IS NULL OR warehouse = :warehouse)""",
        params,
    )
    if exact_rows:
        return exact_rows

    if len(terms) != 1:
        return []

    matching_sku_rows = run_query(
        """SELECT DISTINCT sku
              FROM logistics_sku
             WHERE product_name LIKE :product_term
               AND sku IS NOT NULL
               AND (:warehouse IS NULL OR warehouse = :warehouse)
             ORDER BY sku
             LIMIT :profile_limit""",
        {
            "product_term": f"%{terms[0]}%",
            "warehouse": warehouse,
            "profile_limit": 20,
        },
    )
    selected_skus = [_row_value(row, "sku") for row in matching_sku_rows]
    selected_skus = [sku for sku in selected_skus if sku is not None]
    if not selected_skus:
        return []

    profile_placeholders, profile_params = _bind_values("profile_sku", selected_skus)
    profile_params["warehouse"] = warehouse
    return run_query(
        f"""SELECT *
              FROM logistics_sku
             WHERE sku IN ({profile_placeholders})
               AND (:warehouse IS NULL OR warehouse = :warehouse)
             ORDER BY sku, warehouse""",
        profile_params,
    )


def _bind_values(prefix: str, values: list[str]) -> tuple[str, dict[str, str]]:
    names = [f":{prefix}_{index}" for index in range(len(values))]
    return ", ".join(names), {
        f"{prefix}_{index}": value for index, value in enumerate(values)
    }


def _select_skus(profile_rows: list[dict]) -> list[str]:
    selected = []
    seen = set()
    for row in profile_rows:
        sku = _row_value(row, "sku")
        if sku is None or sku in seen:
            continue
        seen.add(sku)
        selected.append(sku)
        if len(selected) == 20:
            break
    return selected


def _load_detail_rows(skus: list[str], warehouse: str | None) -> dict[str, list[dict]]:
    placeholders, params = _bind_values("sku", skus)
    params["warehouse"] = warehouse
    details = {}
    for table in _LOGISTICS_TABLES[1:]:
        details[table] = run_query(
            f"""SELECT *
                  FROM {table}
                 WHERE sku IN ({placeholders})
                   AND (:warehouse IS NULL OR warehouse = :warehouse)""",
            params,
        )
    return details


def _group_results(
    profile_rows: list[dict],
    details: dict[str, list[dict]],
    selected_warehouse: str | None,
) -> list[dict]:
    grouped: OrderedDict[str, OrderedDict[str | None, dict[str, Any]]] = OrderedDict()
    for profile in profile_rows:
        sku = _row_value(profile, "sku")
        if sku is None:
            continue
        warehouse = _warehouse_value(profile)
        if selected_warehouse is not None and warehouse != selected_warehouse:
            continue
        sku_groups = grouped.setdefault(sku, OrderedDict())
        warehouse_group = sku_groups.setdefault(
            warehouse,
            {
                "warehouse": warehouse,
                "profile": profile,
                "profiles": [],
                "containers": [],
                "replenish": [],
                "shipments": [],
                "container_maps": [],
            },
        )
        warehouse_group["profiles"].append(profile)

    _append_rows(grouped, details.get("logistics_container", []), "containers", selected_warehouse)
    _append_rows(grouped, details.get("logistics_replenish", []), "replenish", selected_warehouse)
    _append_shipments(grouped, details.get("logistics_shipment", []), selected_warehouse)
    _attach_container_maps(
        grouped,
        details.get("logistics_shipment_container_map", []),
        selected_warehouse,
    )

    items = []
    for sku, warehouse_groups in grouped.items():
        first_profile = next(iter(warehouse_groups.values()))["profile"]
        item = {
            "sku": sku,
            "custom_sku": first_profile.get("custom_sku"),
            "product_name": first_profile.get("product_name"),
            "warehouses": list(warehouse_groups.values()),
        }
        items.append(item)
    return items


def _append_rows(
    grouped: OrderedDict,
    rows: list[dict],
    destination: str,
    selected_warehouse: str | None,
) -> None:
    for row in rows:
        group = _find_group(grouped, row, selected_warehouse)
        if group is not None:
            group[destination].append(row)


def _append_shipments(
    grouped: OrderedDict,
    rows: list[dict],
    selected_warehouse: str | None,
) -> None:
    for row in rows:
        group = _find_group(grouped, row, selected_warehouse)
        if group is None:
            continue
        shipment = dict(row)
        shipment["container_maps"] = []
        group["shipments"].append(shipment)


def _attach_container_maps(
    grouped: OrderedDict,
    rows: list[dict],
    selected_warehouse: str | None,
) -> None:
    for row in rows:
        group = _find_group(grouped, row, selected_warehouse)
        if group is None:
            continue
        badge_no = _badge_no(row)
        matching_shipments = [
            shipment
            for shipment in group["shipments"]
            if _badge_no(shipment) == badge_no and badge_no is not None
        ]
        if matching_shipments:
            matching_shipments[0]["container_maps"].append(row)
        else:
            group["container_maps"].append(row)


def _find_group(
    grouped: OrderedDict,
    row: dict,
    selected_warehouse: str | None,
) -> dict | None:
    sku = _row_value(row, "sku")
    if sku not in grouped:
        return None
    warehouse = _warehouse_value(row)
    if selected_warehouse is not None and warehouse != selected_warehouse:
        return None
    sku_groups = grouped[sku]
    if warehouse in sku_groups:
        return sku_groups[warehouse]
    return None


def _badge_no(row: dict) -> Any:
    return row.get("badge_no") or row.get("shipment_badge_no")


def _row_value(row: dict, key: str) -> str | None:
    value = row.get(key)
    return str(value) if value is not None else None


def _warehouse_value(row: dict) -> str | None:
    value = row.get("warehouse")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
