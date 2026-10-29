import inspect
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import ANY, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

database_stub = ModuleType("database")
database_stub.run_execute = lambda *_args, **_kwargs: 0
database_stub.run_query = lambda *_args, **_kwargs: []
sys.modules.setdefault("database", database_stub)

from routers import sales as sales_routes
from services import sales_service


def daily_sales_responses():
    return [
        [{"dpbh": "STORE-A", "dds": 12, "xse": 345.67, "ckh": "一仓", "rq": "2026-10-13"}],
        [{"total": 1}],
        [{"orders": 12, "sales": 345.67, "stores": 1}],
        [{"dpbh": "STORE-A"}],
    ]


class DailySalesSortingTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(sales_routes.router)
        user = {"role": "leader", "userId": "17"}
        app.dependency_overrides[sales_routes.get_current_user] = lambda: user
        self.client = TestClient(app)

    @patch("routers.sales.sales_service.get_daily_sales")
    def test_daily_route_defaults_to_sales_then_order_descending(self, get_daily_sales):
        get_daily_sales.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20, "summary": {}, "stores": []}

        response = self.client.get("/sales/daily")

        self.assertEqual(response.status_code, 200)
        get_daily_sales.assert_called_once_with(
            {"role": "leader", "userId": "17"}, (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"), None, 1, 20, "xse", "desc", None, None
        )

    @patch("routers.sales.sales_service.get_daily_sales")
    def test_daily_route_forwards_requested_sort_to_the_service(self, get_daily_sales):
        get_daily_sales.return_value = {"items": [], "total": 0, "page": 1, "page_size": 10, "summary": {}, "stores": []}

        response = self.client.get(
            "/sales/daily",
            params={"target_date": "2026-10-13", "page": 1, "page_size": 10, "sort_by": "dds", "sort_order": "asc"},
        )

        self.assertEqual(response.status_code, 200)
        get_daily_sales.assert_called_once_with(
            {"role": "leader", "userId": "17"}, "2026-10-13", None, 1, 10, "dds", "asc", None, None
        )

    @patch("routers.sales.sales_service.get_daily_sales")
    def test_daily_route_forwards_date_range(self, get_daily_sales):
        get_daily_sales.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20, "summary": {}, "stores": []}

        response = self.client.get(
            "/sales/daily",
            params={"start_date": "2026-10-01", "end_date": "2026-10-13"},
        )

        self.assertEqual(response.status_code, 200)
        get_daily_sales.assert_called_once_with(
            {"role": "leader", "userId": "17"}, ANY, None, 1, 20, "xse", "desc", "2026-10-01", "2026-10-13"
        )

    def test_daily_route_rejects_incomplete_or_reversed_date_range(self):
        self.assertEqual(self.client.get("/sales/daily", params={"start_date": "2026-10-01"}).status_code, 422)
        self.assertEqual(
            self.client.get("/sales/daily", params={"start_date": "2026-10-13", "end_date": "2026-10-01"}).status_code,
            422,
        )

    @patch("routers.sales.sales_service.get_daily_sales")
    def test_daily_route_rejects_sort_fields_outside_the_supported_metrics(self, get_daily_sales):
        response = self.client.get("/sales/daily", params={"sort_by": "dpbh; DROP TABLE dny_data"})

        self.assertEqual(response.status_code, 422)
        get_daily_sales.assert_not_called()

    @patch("services.sales_service.run_query")
    def test_default_sort_orders_sales_then_orders_before_pagination(self, run_query):
        run_query.side_effect = daily_sales_responses()

        sales_service.get_daily_sales(
            user={"role": "admin", "userId": "1"},
            target_date="2026-10-13",
            store=None,
            page=2,
            page_size=10,
        )

        items_sql, params = run_query.call_args_list[0].args
        self.assertIn(
            "ORDER BY CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4)) DESC, "
            "CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4)) DESC, d.dpbh ASC LIMIT :limit OFFSET :offset",
            items_sql,
        )
        self.assertEqual(params["offset"], 10)

    @patch("services.sales_service.run_query")
    def test_selected_order_sort_is_global_and_preserves_operator_scope(self, run_query):
        parameters = inspect.signature(sales_service.get_daily_sales).parameters
        self.assertIn("sort_by", parameters)
        self.assertIn("sort_order", parameters)
        run_query.side_effect = daily_sales_responses()

        sales_service.get_daily_sales(
            user={"role": "leader", "userId": "17"},
            target_date="2026-10-13",
            store=None,
            page=3,
            page_size=10,
            sort_by="dds",
            sort_order="asc",
        )

        items_sql, params = run_query.call_args_list[0].args
        self.assertIn(
            "ORDER BY CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4)) ASC, "
            "CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4)) DESC, d.dpbh ASC LIMIT :limit OFFSET :offset",
            items_sql,
        )
        self.assertIn("REPLACE(TRIM(p.yy), '代维护', '') IN", items_sql)
        self.assertEqual(params["scope_id"], 17)
        self.assertEqual(params["offset"], 20)

    @patch("services.sales_service.run_query")
    def test_date_range_aggregates_each_store_before_pagination(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "STORE-A", "dds": 20, "xse": 500, "ckh": "一仓、二仓", "period_start": "2026-10-01", "period_end": "2026-10-13"}],
            [{"total": 1}],
            [{"orders": 20, "sales": 500, "stores": 1}],
            [{"dpbh": "STORE-A"}],
        ]

        result = sales_service.get_daily_sales(
            user={"role": "admin", "userId": "1"},
            target_date="2026-10-13",
            store=None,
            page=1,
            page_size=20,
            start_date="2026-10-01",
            end_date="2026-10-13",
        )

        items_sql, params = run_query.call_args_list[0].args
        self.assertIn("GROUP BY d.dpbh", items_sql)
        self.assertIn("ORDER BY xse DESC, dds DESC, dpbh ASC", items_sql)
        self.assertEqual(params["start_date"], "2026-10-01")
        self.assertEqual(result["period_start"], "2026-10-01")
        self.assertEqual(result["period_end"], "2026-10-13")

    def test_sort_clause_only_interpolates_allowlisted_columns_and_directions(self):
        make_clause = getattr(sales_service, "daily_sales_sort_clause", None)
        self.assertTrue(callable(make_clause))
        if not callable(make_clause):
            return

        xse = "CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4))"
        dds = "CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4))"
        self.assertEqual(make_clause("xse", "asc"), f"{xse} ASC, {dds} DESC, d.dpbh ASC")
        self.assertEqual(make_clause("dds", "desc"), f"{dds} DESC, {xse} DESC, d.dpbh ASC")
        self.assertEqual(make_clause("xse; DROP TABLE dny_data", "desc"), f"{xse} DESC, {dds} DESC, d.dpbh ASC")


if __name__ == "__main__":
    unittest.main()
