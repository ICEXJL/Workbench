import math
import re
from collections import OrderedDict
from typing import Any

from database import run_query


_LOGISTICS_TABLES = (
    "logistics_sku",
    "logistics_container",
    "logistics_replenish",
    "logistics_shipment",
)
# 2026-10-24 移除 logistics_shipment_container_map：
# 该表数据虽由接口返回，但前端从不渲染；柜级海运量（sea_qty）由
# logistics_container.load_time 与 logistics_shipment.handover 做月日匹配算出，
# 不依赖此表。保留查询只会每次多扫 2.7 万行，且其覆盖率仅 16%
# （25,178 / 154,887 个发货条码），展示价值低。如需恢复，见
# docs/API_LOGISTICS.md 的说明。


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
    container_sku_rows = _resolve_container_skus(terms, normalized_warehouse)
    selected_skus = _select_skus(profile_rows + container_sku_rows)
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


def _resolve_container_skus(terms: list[str], warehouse: str | None) -> list[dict]:
    placeholders, params = _bind_values("container_term", terms)
    params["warehouse"] = warehouse
    return run_query(
        f"""SELECT DISTINCT sku
              FROM logistics_container
             WHERE sku IN ({placeholders})
               AND (:warehouse IS NULL OR warehouse = :warehouse)
             ORDER BY sku""",
        params,
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
        warehouse_group = _ensure_group(grouped, profile, selected_warehouse)
        if warehouse_group is None:
            continue
        if warehouse_group["profile"] is None:
            warehouse_group["profile"] = profile
        warehouse_group["profiles"].append(profile)

    _append_rows(grouped, details.get("logistics_container", []), "containers", selected_warehouse)
    _append_rows(grouped, details.get("logistics_replenish", []), "replenish", selected_warehouse)
    _append_shipments(grouped, details.get("logistics_shipment", []), selected_warehouse)
    _attach_container_ocean_quantities(grouped)

    for sku_groups in grouped.values():
        for warehouse_group in sku_groups.values():
            # 升序：key 内部已用负号表达「倒序」，不能再加 reverse，
            # 否则未送仓优先的规则会被翻转。
            warehouse_group["containers"].sort(key=_container_sort_key)
            warehouse_group["shipments"].sort(
                key=_shipment_sort_key,
                reverse=True,
            )

    items = []
    for sku, warehouse_groups in grouped.items():
        first_profile = next(
            (group["profile"] for group in warehouse_groups.values() if group["profile"]),
            {},
        )
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
        group = _ensure_group(grouped, row, selected_warehouse)
        if group is not None:
            group[destination].append(row)


def _append_shipments(
    grouped: OrderedDict,
    rows: list[dict],
    selected_warehouse: str | None,
) -> None:
    for row in rows:
        group = _ensure_group(grouped, row, selected_warehouse)
        if group is not None:
            group["shipments"].append(dict(row))


def _attach_container_ocean_quantities(grouped: OrderedDict) -> None:
    """Attach emitted shipment quantities to containers with the same handover date."""
    for sku_groups in grouped.values():
        for warehouse_group in sku_groups.values():
            for container in warehouse_group["containers"]:
                matching_shipments = [
                    shipment
                    for shipment in warehouse_group["shipments"]
                    if _is_emitted_shipment(shipment)
                    and _same_logistics_date(
                        container.get("load_time"),
                        shipment.get("handover"),
                    )
                ]
                container["sea_qty"] = _sum_shipment_quantities(matching_shipments)


def _is_emitted_shipment(row: dict) -> bool:
    record_type = str(row.get("record_type") or "").strip().upper()
    return record_type in {"EMITTED", "SHIPPED", "已发货", "已出货"}


def _same_logistics_date(left: Any, right: Any) -> bool:
    left_parts = _container_date_parts(left)
    right_parts = _container_date_parts(right)
    if left_parts is None or right_parts is None:
        left_text = str(left or "").strip()
        right_text = str(right or "").strip()
        return bool(left_text) and left_text == right_text

    left_year, left_month, left_day = left_parts
    right_year, right_month, right_day = right_parts
    if (left_month, left_day) != (right_month, right_day):
        return False
    return left_year is None or right_year is None or left_year == right_year


def _sum_shipment_quantities(rows: list[dict]) -> int | float | None:
    if not rows:
        return None

    total = 0.0
    has_value = False
    for row in rows:
        try:
            value = float(row.get("qty2"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        total += value
        has_value = True

    if not has_value:
        return None
    return int(total) if total.is_integer() else total


def _ensure_group(
    grouped: OrderedDict,
    row: dict,
    selected_warehouse: str | None,
) -> dict | None:
    sku = _row_value(row, "sku")
    if sku is None:
        return None
    warehouse = _warehouse_value(row)
    if warehouse is None or (selected_warehouse is not None and warehouse != selected_warehouse):
        return None
    sku_groups = grouped.setdefault(sku, OrderedDict())
    return sku_groups.setdefault(
        warehouse,
        {
            "warehouse": warehouse,
            "profile": None,
            "profiles": [],
            "containers": [],
            "replenish": [],
            "shipments": [],
        },
    )


def _is_delivered(row: dict) -> bool:
    """货柜是否已实际送仓。"""
    return bool(row.get("actual_in")) or bool(
        re.search(r"已签收|已送仓|已入仓", str(row.get("status") or ""))
    )


def _container_sort_key(row: dict) -> tuple[int, int, int, str]:
    """货柜排序：未送仓优先 → 进度越靠后越前 → 装柜时间倒序。

    2026-10-24 调整。原实现 `int(delivered)` 配合 `reverse=True` 把已送仓的
    排在前面，而全库 133,190 个柜里 121,558 个（91%）已签收，导致在途柜被
    压到列表底部，运营要翻很久才能看到还没到的柜。

    新规则：
      · 未送仓的整组排在已送仓之前；
      · 未送仓内部按 `stage_seq` 降序——已到「送仓」环节只差签收的排最前，
        其次是到港、开船，对应「马上要收货」的处理优先级；
      · 同阶段内按装柜时间倒序；
      · 已送仓内部按实际送仓时间倒序（最近送仓的在前）。

    注意：`sort_key` 列在全库都是 0（ETL 未维护），不能作为排序依据，
    因此本函数不再引用它。
    """
    try:
        stage = int(row.get("stage_seq") or 0)
    except (TypeError, ValueError):
        stage = 0
    load_key = _container_date_key(row.get("load_time"), row.get("load_time"))
    load_text = str(row.get("load_time") or "")

    if _is_delivered(row):
        delivered_key = _container_date_key(row.get("actual_in"), row.get("load_time"))
        return (1, -delivered_key, -stage, load_text)

    return (0, -stage, -load_key, load_text)


def _shipment_sort_key(row: dict) -> int:
    date_parts = _container_date_parts(row.get("reg_date"))
    if date_parts is None:
        return 0
    year, month, day = date_parts
    return (year or 0) * 10000 + month * 100 + day


def _container_date_key(value: Any, load_time: Any = None) -> int:
    date_parts = _container_date_parts(value)
    if date_parts is None:
        return 0

    year, month, day = date_parts
    if year is None and load_time:
        load_parts = _container_date_parts(load_time)
        if load_parts is not None and load_parts[0] is not None:
            year = load_parts[0] + int(month < load_parts[1])

    return year * 10000 + month * 100 + day if year is not None else month * 100 + day


def _container_date_parts(value: Any) -> tuple[int | None, int, int] | None:
    text = str(value or "")
    match = re.search(r"(?<!\d)(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?!\d)", text)
    if match:
        year, month, day = map(int, match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return year, month, day
        return None

    match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})(?!\d)", text)
    if not match:
        return None
    month, day = map(int, match.groups())
    if 1 <= month <= 12 and 1 <= day <= 31:
        return None, month, day
    return None


def _row_value(row: dict, key: str) -> str | None:
    value = row.get(key)
    return str(value) if value is not None else None


def _warehouse_value(row: dict) -> str | None:
    value = row.get("warehouse")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
