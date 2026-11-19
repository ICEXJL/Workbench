import unittest
import sys
from types import ModuleType
from unittest.mock import patch

database_stub = ModuleType("database")
database_stub.run_execute = lambda *_args, **_kwargs: 0
database_stub.run_query = lambda *_args, **_kwargs: []
sys.modules.setdefault("database", database_stub)

from services import sales_service


class PersonnelSalesTests(unittest.TestCase):
    @patch("services.sales_service.run_query")
    def test_returns_operator_account_totals_and_sales_ranking(self, run_query):
        run_query.side_effect = [
            [{"total": 23}],
            [{"yy": "运营甲", "total_orders": 36, "total_sales": 1234.5, "avg_sales": 176.36, "dd1": 4, "xs1": 120.0, "dd7": 8, "xs7": 300.0}],
            [{"total_orders": 987, "total_sales": 65432.1}],
            [{"jc": "深圳二部", "zm": "二组", "yy": "运营甲"}],
        ]

        result = sales_service.get_personnel_sales(
            user={"role": "admin", "userId": "1"},
            cxrq_str="2026-09-27",
            department=None,
            group=None,
            operator=None,
            page=2,
            page_size=10,
        )

        self.assertEqual(result["total"], 23)
        self.assertEqual(result["items"][0]["yy"], "运营甲")
        self.assertEqual(result["items"][0]["total_sales"], 1234.5)
        self.assertEqual(result["items"][0]["total_orders"], 36)
        self.assertEqual(result["items"][0]["avg_sales"], 176.36)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["summary"], {"total_orders": 987, "total_sales": 65432.1})

        count_sql = run_query.call_args_list[0].args[0]
        items_sql = run_query.call_args_list[1].args[0]
        self.assertIn("COUNT(DISTINCT p.yy)", count_sql)
        self.assertIn("GROUP BY p.yy ORDER BY total_sales DESC,yy", items_sql)
        self.assertIn("ROUND(COALESCE(SUM(d.xse),0) / 7, 2) avg_sales", items_sql)
        self.assertIn(" dd1", items_sql)
        self.assertIn(" dd7", items_sql)
        self.assertIn("d.rq BETWEEN DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 6 DAY", items_sql)
        self.assertIn("AND DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 0 DAY", items_sql)
        self.assertIn("INTERVAL 6 DAY,'%Y-%m-%d') THEN d.dds ELSE 0 END) dd1", items_sql)
        self.assertIn("INTERVAL 0 DAY,'%Y-%m-%d') THEN d.dds ELSE 0 END) dd7", items_sql)
        self.assertEqual(run_query.call_args_list[1].args[1]["offset"], 10)

    @patch("services.sales_service.run_query")
    def test_summary_uses_same_scope_filters_and_date_window_without_pagination(self, run_query):
        run_query.side_effect = [
            [{"total": 1}],
            [],
            [{"total_orders": 12, "total_sales": 345.67}],
            [],
        ]

        result = sales_service.get_personnel_sales(
            user={"role": "leader", "userId": "145"},
            cxrq_str="2026-10-28",
            department="深圳二部",
            group="二组",
            operator=None,
            page=3,
            page_size=10,
        )

        summary_sql, summary_params = run_query.call_args_list[2].args
        self.assertIn("SUM(d.dds) operator_orders", summary_sql)
        self.assertIn("SUM(d.xse) operator_sales", summary_sql)
        self.assertIn("SUM(operator_orders),0) total_orders", summary_sql)
        self.assertIn("SUM(operator_sales),0),2) total_sales", summary_sql)
        self.assertIn("org_hierarchy", summary_sql)
        self.assertIn("p.jc=:department", summary_sql)
        self.assertIn("p.zm=:group_name", summary_sql)
        self.assertIn("INTERVAL 6 DAY", summary_sql)
        self.assertIn("INTERVAL 0 DAY", summary_sql)
        self.assertNotIn("LIMIT", summary_sql.upper())
        self.assertNotIn("OFFSET", summary_sql.upper())
        self.assertNotIn("limit", summary_params)
        self.assertNotIn("offset", summary_params)
        self.assertEqual(summary_params["department"], "深圳二部")
        self.assertEqual(summary_params["group_name"], "二组")
        self.assertEqual(result["summary"]["total_orders"], 12)


if __name__ == "__main__":
    unittest.main()
