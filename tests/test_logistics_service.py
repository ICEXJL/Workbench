import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

database_stub = ModuleType("database")
database_stub.run_query = lambda *_args, **_kwargs: []
sys.modules.setdefault("database", database_stub)


def test_list_query_terms_accepts_backslash_and_caps_at_twenty():
    from services.logistics_service import list_query_terms

    assert list_query_terms(" 1001\\1002\n1003 ") == ["1001", "1002", "1003"]
    assert len(list_query_terms("\\".join(str(i) for i in range(25)))) == 20


def test_validate_warehouse_allows_empty_and_rejects_unknown_value():
    from services.logistics_service import validate_warehouse

    assert validate_warehouse(None, ["PH-A"]) is None
    assert validate_warehouse("", ["PH-A"]) is None
    assert validate_warehouse("PH-A", ["PH-A"]) == "PH-A"
    with pytest.raises(ValueError, match="仓库"):
        validate_warehouse("UNKNOWN", ["PH-A"])


def test_empty_query_returns_empty_shape_without_database_calls(monkeypatch):
    from services import logistics_service

    def unexpected_query(*_args, **_kwargs):
        pytest.fail("empty query should not read logistics tables")

    monkeypatch.setattr(logistics_service, "run_query", unexpected_query)

    assert logistics_service.search_logistics("  ", None) == {
        "items": [],
        "query": "  ",
        "warehouse": None,
    }


def test_search_logistics_keeps_warehouse_in_each_table_query(monkeypatch):
    from services import logistics_service

    captured = []

    def fake_query(sql, params=None):
        captured.append((sql, params or {}))
        if "FROM logistics_sku" in sql:
            return [{"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [{"warehouse": "PH-A", "sku_count": 1}], "default_warehouse": None},
    )
    result = logistics_service.search_logistics("1001", "PH-A")

    assert result["items"][0]["sku"] == "1001"
    logistics_queries = [
        (sql, params)
        for sql, params in captured
        if "logistics_" in sql
    ]
    tables = (
        "logistics_sku",
        "logistics_container",
        "logistics_replenish",
        "logistics_shipment",
        "logistics_shipment_container_map",
    )
    for table in tables:
        table_queries = [(sql, params) for sql, params in logistics_queries if table in sql]
        assert table_queries, f"missing query for {table}"
        assert all("warehouse" in sql.lower() for sql, _ in table_queries)
        assert all("JOIN" not in sql.upper() for sql, _ in table_queries)
        assert all("1001" not in sql for sql, _ in table_queries)
        assert all("PH-A" in params.values() for _, params in table_queries)


def test_search_groups_profiles_by_warehouse_and_attaches_maps_to_shipments(monkeypatch):
    from services import logistics_service

    profiles = [
        {"sku": "1001", "custom_sku": "C-1", "warehouse": "PH-A", "product_name": "测试品", "stock": 5},
        {"sku": "1001", "custom_sku": "C-1", "warehouse": "PH-B", "product_name": "测试品", "stock": 9},
    ]

    def fake_query(sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" in normalized:
            return profiles
        if "from logistics_shipment_container_map" in normalized:
            return [
                {"sku": "1001", "warehouse": "PH-A", "badge_no": "B-1", "container_no": "C-A"},
                {"sku": "1001", "warehouse": "PH-B", "badge_no": "B-2", "container_no": "C-B"},
            ]
        if "from logistics_shipment" in normalized:
            return [
                {"sku": "1001", "warehouse": "PH-A", "badge_no": "B-1"},
                {"sku": "1001", "warehouse": "PH-B", "badge_no": "B-2"},
            ]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [], "default_warehouse": None},
    )

    result = logistics_service.search_logistics("1001", None)

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert [entry["warehouse"] for entry in item["warehouses"]] == ["PH-A", "PH-B"]
    assert [entry["profile"]["stock"] for entry in item["warehouses"]] == [5, 9]
    assert item["warehouses"][0]["shipments"][0]["container_maps"][0]["container_no"] == "C-A"
    assert item["warehouses"][1]["shipments"][0]["container_maps"][0]["container_no"] == "C-B"
