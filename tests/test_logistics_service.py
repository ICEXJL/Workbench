import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

database_stub = ModuleType("database")
database_stub.run_query = lambda *_args, **_kwargs: []
database_stub.run_execute = lambda *_args, **_kwargs: 0
sys.modules.setdefault("database", database_stub)


def test_logistics_router_exposes_read_only_paths():
    from routers.logistics import router

    paths = {(route.path, tuple(sorted(route.methods))) for route in router.routes}
    assert ("/logistics/warehouses", ("GET",)) in paths
    assert ("/logistics/search", ("GET",)) in paths


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

    def unexpected_warehouse_lookup():
        pytest.fail("empty query without warehouse should not load warehouses")

    monkeypatch.setattr(logistics_service, "run_query", unexpected_query)
    monkeypatch.setattr(logistics_service, "get_warehouses", unexpected_warehouse_lookup)

    assert logistics_service.search_logistics("  ", None) == {
        "items": [],
        "query": "  ",
        "warehouse": None,
    }


def test_search_logistics_rejects_unknown_warehouse_for_empty_query(monkeypatch):
    from services import logistics_service

    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [{"warehouse": "PH-A"}], "default_warehouse": None},
    )

    with pytest.raises(ValueError, match="仓库"):
        logistics_service.search_logistics("", "UNKNOWN")


def test_is_delivered_requires_actual_arrival():
    """判「已送仓」看实际送仓时间或签收状态，不能只看 stage_seq。

    边界：stage_seq=5（进度到送仓）但状态仍是在途、且无 actual_in 的柜，
    属于「还差签收确认」，应算未送达，才能排在已签收的柜前面。
    """
    from services import logistics_service as ls

    assert ls._is_delivered({"actual_in": "10.10", "status": "在途"}) is True
    assert ls._is_delivered({"actual_in": None, "status": "已签收"}) is True
    assert ls._is_delivered({"actual_in": None, "status": "已送仓"}) is True
    assert ls._is_delivered({"actual_in": None, "status": "在途"}) is False
    assert ls._is_delivered({"actual_in": "", "status": "在途", "stage_seq": 5}) is False


def test_containers_sort_undelivered_first():
    """货柜排序：未送仓优先 → 进度靠后优先 → 已送仓按送仓时间倒序。

    背景：全库 91% 的货柜已签收，若按「已送仓优先」排序，在途柜会被压到
    列表底部，运营要翻很多屏才能看到还没到的柜。
    """
    from services import logistics_service as ls

    containers = [
        {"container_no": "D1", "load_time": "9.1上午", "stage_seq": 5,
         "status": "已签收", "actual_in": "10.10"},
        {"container_no": "U1", "load_time": "10.1上午", "stage_seq": 2,
         "status": "在途", "actual_in": None},
        {"container_no": "U2", "load_time": "9.20上午", "stage_seq": 3,
         "status": "在途", "actual_in": None},
        {"container_no": "D2", "load_time": "8.1上午", "stage_seq": 5,
         "status": "已签收", "actual_in": "10.20"},
        {"container_no": "U3", "load_time": "10.10上午", "stage_seq": 5,
         "status": "在途", "actual_in": None},
    ]

    ordered = [c["container_no"] for c in sorted(containers, key=ls._container_sort_key)]

    # 未送仓：stage 5(在途) → 3 → 2；已送仓：送仓时间 10.20 在 10.10 之前
    assert ordered == ["U3", "U2", "U1", "D2", "D1"]


def test_sort_keeps_all_containers():
    """排序不得丢行（曾用 reverse 参数，改动时容易误加导致顺序翻转）。"""
    from services import logistics_service as ls

    containers = [
        {"container_no": f"C{i}", "load_time": f"9.{i}上午", "stage_seq": i % 5 + 1,
         "status": "已签收" if i % 2 else "在途", "actual_in": "10.1" if i % 2 else None}
        for i in range(1, 11)
    ]
    ordered = sorted(containers, key=ls._container_sort_key)
    assert len(ordered) == 10
    assert {c["container_no"] for c in ordered} == {c["container_no"] for c in containers}


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
    )
    for table in tables:
        table_queries = [(sql, params) for sql, params in logistics_queries if table in sql]
        assert table_queries, f"missing query for {table}"
        assert all("warehouse" in sql.lower() for sql, _ in table_queries)
        assert all("JOIN" not in sql.upper() for sql, _ in table_queries)
        assert all("1001" not in sql for sql, _ in table_queries)
        assert all("PH-A" in params.values() for _, params in table_queries)


def test_search_does_not_query_container_map_table(monkeypatch):
    """回归：2026-10-24 起不再查询 logistics_shipment_container_map。

    移除原因：该表数据前端从未渲染；柜级海运量（sea_qty）由
    `container.load_time` 与 `shipment.handover` 做月日匹配算出，
    不依赖此表；且其覆盖率仅 16%（25,178 / 154,887 个发货条码）。
    保留查询只会每次多扫 2.7 万行。

    此测试防止后续改动无意中把它加回查询链。
    """
    from services import logistics_service

    assert "logistics_shipment_container_map" not in logistics_service._LOGISTICS_TABLES

    captured = []

    def fake_query(sql, params=None):
        captured.append(sql)
        if "FROM logistics_sku" in sql:
            return [{"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [{"warehouse": "PH-A", "sku_count": 1}], "default_warehouse": None},
    )
    logistics_service.search_logistics("1001", "PH-A")

    offending = [sql for sql in captured if "shipment_container_map" in sql.lower()]
    assert not offending, f"不应再查询 shipment_container_map，实际查询：{offending}"


def test_search_groups_profiles_by_warehouse(monkeypatch):
    from services import logistics_service

    profiles = [
        {"sku": "1001", "custom_sku": "C-1", "warehouse": "PH-A", "product_name": "测试品", "stock": 5},
        {"sku": "1001", "custom_sku": "C-1", "warehouse": "PH-B", "product_name": "测试品", "stock": 9},
    ]

    def fake_query(sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" in normalized:
            return profiles
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
    # 2026-10-24 起不再向发货记录挂 container_maps（映射表已移出查询）
    assert "container_maps" not in item["warehouses"][0]["shipments"][0]
    assert "container_maps" not in item["warehouses"][0]


def test_search_does_not_assign_rows_without_warehouse_to_only_group(monkeypatch):
    from services import logistics_service

    def fake_query(sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" in normalized:
            return [{"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}]
        if "from logistics_shipment" in normalized:
            return [
                {"sku": "1001", "badge_no": "MISSING"},
                {"sku": "1001", "warehouse": "", "badge_no": "EMPTY"},
            ]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [], "default_warehouse": None},
    )

    result = logistics_service.search_logistics("1001", None)

    assert result["items"][0]["warehouses"][0]["shipments"] == []


def test_product_name_fallback_limits_rows_in_sql(monkeypatch):
    from services import logistics_service

    captured = []

    def fake_query(sql, params=None):
        captured.append((sql, params or {}))
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" in normalized and "product_name like" not in normalized:
            return []
        if "from logistics_sku" in normalized and "product_name like" in normalized:
            return [{"sku": str(index)} for index in range(20)]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [{"warehouse": "PH-A"}], "default_warehouse": None},
    )

    logistics_service.search_logistics("测试", "PH-A")

    product_sql = next(
        sql for sql, _ in captured
        if "product_name LIKE" in sql
    )
    product_params = next(
        params for sql, params in captured
        if "product_name LIKE" in sql
    )
    assert "SELECT DISTINCT sku" in product_sql
    assert "ORDER BY sku" in product_sql
    assert "LIMIT :profile_limit" in product_sql
    assert "warehouse" in product_sql.lower()
    assert product_params["profile_limit"] == 20


def test_product_name_fallback_loads_all_profiles_for_selected_skus(monkeypatch):
    from services import logistics_service

    captured = []

    def fake_query(sql, params=None):
        captured.append((sql, params or {}))
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" not in normalized:
            return []
        if "custom_sku" in normalized:
            return []
        if "product_name like" in normalized:
            return [{"sku": "1001"}, {"sku": "1002"}]
        if "sku in" in normalized:
            return [
                {"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"},
                {"sku": "1001", "warehouse": "PH-B", "product_name": "测试品"},
                {"sku": "1002", "warehouse": "PH-A", "product_name": "测试品"},
            ]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {
            "warehouses": [{"warehouse": "PH-A"}, {"warehouse": "PH-B"}],
            "default_warehouse": None,
        },
    )

    result = logistics_service.search_logistics("测试", None)

    assert [entry["warehouse"] for entry in result["items"][0]["warehouses"]] == ["PH-A", "PH-B"]
    profile_queries = [
        (sql, params)
        for sql, params in captured
        if "FROM logistics_sku" in sql
        and "sku IN" in sql
        and "custom_sku" not in sql.lower()
    ]
    assert len(profile_queries) == 1
    profile_sql, profile_params = profile_queries[0]
    assert "product_name" not in profile_sql.lower()
    assert "warehouse" in profile_sql.lower()
    assert set(profile_params) >= {"profile_sku_0", "profile_sku_1", "warehouse"}


def test_search_finds_container_sku_without_a_sku_profile(monkeypatch):
    from services import logistics_service

    container = {
        "sku": "1003",
        "warehouse": "PH-A",
        "load_time": "7.16下午",
        "status": "在途",
        "warehouse_desc": "三仓628+六仓265",
        "carrier": "Carrier A",
        "stage_seq": 3,
        "stage_name": "到港",
        "eta": "7.28",
        "actual_in": None,
        "tracking": "7.20已开船/7.24已到港",
        "sort_key": 3,
    }

    def fake_query(sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if "from logistics_sku" in normalized:
            return []
        if "select distinct sku" in normalized and "from logistics_container" in normalized:
            return [{"sku": "1003"}]
        if "from logistics_container" in normalized:
            return [container]
        return []

    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    monkeypatch.setattr(
        logistics_service,
        "get_warehouses",
        lambda: {"warehouses": [{"warehouse": "PH-A"}], "default_warehouse": None},
    )

    result = logistics_service.search_logistics("1003", "PH-A")

    assert len(result["items"]) == 1
    group = result["items"][0]["warehouses"][0]
    assert group["profile"] is None
    assert group["containers"][0]["tracking"] == "7.20已开船/7.24已到港"


def test_group_results_orders_containers_within_same_stage_by_load_time_desc():
    """同一阶段内按装柜时间倒序。

    注意：`logistics_container.sort_key` 列在全库 133,190 行中都是 0
    （ETL 未维护），不能作为排序依据，因此本测试改用真实日期文本验证
    装柜时间倒序，而不是依赖 sort_key。
    """
    from services.logistics_service import _group_results

    profile = {"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}
    containers = [
        {"sku": "1001", "warehouse": "PH-A", "container_no": "C-OLD",
         "load_time": "2026.8.1上午", "status": "在途", "stage_seq": 3},
        {"sku": "1001", "warehouse": "PH-A", "container_no": "C-NEW",
         "load_time": "2026.10.1上午", "status": "在途", "stage_seq": 3},
        {"sku": "1001", "warehouse": "PH-A", "container_no": "C-MID",
         "load_time": "2026.9.1上午", "status": "在途", "stage_seq": 3},
    ]

    result = _group_results([profile], {"logistics_container": containers}, "PH-A")

    assert [row["container_no"] for row in result[0]["warehouses"][0]["containers"]] == [
        "C-NEW",
        "C-MID",
        "C-OLD",
    ]


def test_group_results_places_transit_containers_before_signed_ones():
    """未送仓的货柜排在已送仓之前（2026-10-24 需求变更）。

    原行为是「已签收优先」，但全库 91% 的货柜已签收，导致在途柜被压到
    列表底部。现改为未送仓优先；已送仓内部仍按实际送仓时间倒序。
    """
    from services.logistics_service import _group_results

    profile = {"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}
    containers = [
        {"sku": "1001", "warehouse": "PH-A", "container_no": "OLD00000001", "status": "已签收", "actual_in": "2026-09-11", "load_time": "2026.9.20"},
        {"sku": "1001", "warehouse": "PH-A", "container_no": "NEW00000002", "status": "已签收", "actual_in": "2026-10-02", "load_time": "2026.8.17"},
        {"sku": "1001", "warehouse": "PH-A", "container_no": "SEA00000003", "status": "在途", "actual_in": None, "load_time": "2026.10.14"},
    ]

    result = _group_results([profile], {"logistics_container": containers}, "PH-A")

    assert [row["container_no"] for row in result[0]["warehouses"][0]["containers"]] == [
        "SEA00000003",
        "NEW00000002",
        "OLD00000001",
    ]


def test_group_results_assigns_ocean_quantity_to_matching_container_only():
    from services.logistics_service import _group_results

    profile = {"sku": "2254577", "warehouse": "PH-SAN-RAFAEL-3", "product_name": "测试品"}
    containers = [
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "container_no": "SNBU8489366",
            "load_time": "9.4",
            "status": "已签收",
        },
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "container_no": "OTHER000001",
            "load_time": "9.5",
            "status": "在途",
        },
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "container_no": "NO-SHIPMENT",
            "load_time": "9.6",
            "status": "在途",
        },
    ]
    shipments = [
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "record_type": "EMITTED",
            "handover": "2026-09-04",
            "qty2": 5000,
        },
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "record_type": "EMITTED",
            "handover": "9.5",
            "qty2": 16800,
        },
        {
            "sku": "2254577",
            "warehouse": "PH-SAN-RAFAEL-3",
            "record_type": "PENDING",
            "handover": "9.6",
            "qty2": 99999,
        },
    ]

    result = _group_results(
        [profile],
        {"logistics_container": containers, "logistics_shipment": shipments},
        "PH-SAN-RAFAEL-3",
    )

    quantities = {
        row["container_no"]: row["sea_qty"]
        for row in result[0]["warehouses"][0]["containers"]
    }
    assert quantities == {
        "SNBU8489366": 5000,
        "OTHER000001": 16800,
        "NO-SHIPMENT": None,
    }


def test_group_results_orders_ocean_shipments_by_latest_registration_date():
    from services.logistics_service import _group_results

    profile = {"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}
    shipments = [
        {"sku": "1001", "warehouse": "PH-A", "reg_date": "2026-04-28", "badge_no": "OLD"},
        {"sku": "1001", "warehouse": "PH-A", "reg_date": "2026-09-10", "badge_no": "MID"},
        {"sku": "1001", "warehouse": "PH-A", "reg_date": "2026-09-29", "badge_no": "NEW"},
        {"sku": "1001", "warehouse": "PH-A", "reg_date": None, "badge_no": "NO-DATE"},
    ]

    result = _group_results([profile], {"logistics_shipment": shipments}, "PH-A")

    assert [row["reg_date"] for row in result[0]["warehouses"][0]["shipments"]] == [
        "2026-09-29",
        "2026-09-10",
        "2026-04-28",
        None,
    ]
