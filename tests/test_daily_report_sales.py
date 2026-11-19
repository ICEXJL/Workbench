import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

database_stub = ModuleType("database")
database_stub.run_execute = lambda *_args, **_kwargs: 0
database_stub.run_query = lambda *_args, **_kwargs: []
sys.modules.setdefault("database", database_stub)

from services import report_service
from routers import reports as report_routes
from schemas.schemas import DailyReportPayload


class CumulativeSalesTests(unittest.TestCase):
    def setUp(self):
        self.report_date = date(2026, 9, 28)

    @patch("services.report_service.run_query")
    def test_sums_all_mapped_shops_then_applies_75_percent_factor(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}, {"dpbh": "SHOP-B"}],
            [{"latest_date": "2026-09-29"}],
            [
                {"dpbh": "SHOP-A", "rq": "2026-08-31", "xse": "100.00"},
                {"dpbh": "SHOP-A", "rq": "2026-09-01", "xse": "10.20"},
                {"dpbh": "SHOP-A", "rq": "2026-09-28", "xse": "0"},
                {"dpbh": "SHOP-B", "rq": "2026-09-15", "xse": "4.30"},
                {"dpbh": "SHOP-B", "rq": "2026-09-29", "xse": "500.00"},
                {"dpbh": "OTHER", "rq": "2026-09-15", "xse": "900.00"},
            ],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["amount"], Decimal("10.88"))
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(result["period_start"], "2026-09-01")
        self.assertEqual(result["period_end"], "2026-09-28")
        self.assertEqual(run_query.call_args_list[0].args[1], {"operator_id": 17})
        self.assertEqual(run_query.call_args_list[2].args[1]["period_start"], "2026-09-01")
        self.assertEqual(run_query.call_args_list[2].args[1]["period_end"], "2026-09-28")
        queries = [call.args[0].lower() for call in run_query.call_args_list]
        self.assertIn("max(rq)", queries[1])
        self.assertIn("from dny_data", queries[1])
        self.assertIn("from dny_data", queries[2])
        self.assertIn("rq >= :period_start", queries[2])
        self.assertTrue(all("fbs_data" not in query for query in queries))

    @patch("services.report_service.run_query")
    def test_previous_day_source_watermark_is_not_ready(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}, {"dpbh": "SHOP-B"}],
            [{"latest_date": "2026-09-27"}],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "not_ready")
        self.assertIsNone(result["amount"])
        self.assertEqual(result["data_as_of"], "2026-09-27")
        self.assertEqual(run_query.call_count, 2)

    @patch("services.report_service.run_query")
    def test_source_watermark_on_report_date_is_ready(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-28"}],
            [{"dpbh": "SHOP-A", "rq": "2026-09-28", "xse": "10.20"}],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["amount"], Decimal("7.65"))
        self.assertEqual(result["period_end"], "2026-09-28")
        self.assertEqual(run_query.call_args_list[2].args[1]["period_end"], "2026-09-28")

    @patch("services.report_service.run_query")
    def test_applies_factor_before_rounding_to_cents(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-28"}],
            [{"dpbh": "SHOP-A", "rq": "2026-09-28", "xse": "1.01"}],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["amount"], Decimal("0.76"))

    @patch("services.report_service.run_query")
    def test_source_more_than_one_day_behind_returns_no_amount(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-26"}],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "not_ready")
        self.assertIsNone(result["amount"])
        self.assertEqual(result["data_as_of"], "2026-09-26")
        self.assertEqual(run_query.call_count, 2)

    @patch("services.report_service.run_query")
    def test_previous_month_watermark_does_not_create_reversed_mtd_period(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-30"}],
        ]

        result = report_service.get_cumulative_sales(17, date(2026, 10, 1))

        self.assertEqual(result["status"], "not_ready")
        self.assertIsNone(result["amount"])
        self.assertEqual(result["period_start"], "2026-10-01")
        self.assertEqual(run_query.call_count, 2)

    @patch("services.report_service.run_query")
    def test_zero_total_is_a_valid_available_value(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-28"}],
            [{"dpbh": "SHOP-A", "rq": "2026-09-28", "xse": "0.00"}],
        ]

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["amount"], Decimal("0.00"))

    @patch("services.report_service.run_query")
    def test_missing_mapping_is_not_reported_as_zero(self, run_query):
        run_query.return_value = []

        result = report_service.get_cumulative_sales(17, self.report_date)

        self.assertEqual(result["status"], "mapping_missing")
        self.assertIsNone(result["amount"])
        self.assertEqual(run_query.call_count, 1)

    @patch("services.report_service.run_query")
    def test_invalid_source_amount_is_not_silently_converted_to_zero(self, run_query):
        run_query.side_effect = [
            [{"dpbh": "SHOP-A"}],
            [{"latest_date": "2026-09-28"}],
            [{"dpbh": "SHOP-A", "rq": "2026-09-28", "xse": "invalid"}],
        ]

        with self.assertRaises(report_service.CumulativeSalesDataError):
            report_service.get_cumulative_sales(17, self.report_date)

    def test_client_sales_value_is_optional_and_not_part_of_server_calculation(self):
        payload = DailyReportPayload(
            report_date=self.report_date,
            cumulative_sales=Decimal("999999.99"),
            listing_count=0,
            optimization_count=0,
            violation_triggered=False,
            infringement_triggered=False,
            stocking_audit_rate=100,
            reverse_product_count=0,
            all_issues_resolved=True,
        )

        self.assertEqual(payload.cumulative_sales, Decimal("999999.99"))
        self.assertIsNone(
            DailyReportPayload.model_validate(
                payload.model_dump(exclude={"cumulative_sales"})
            ).cumulative_sales
        )

    @patch("routers.reports.report_service.get_report", return_value=None)
    @patch("routers.reports.report_service.save_report")
    @patch("routers.reports.report_service.get_cumulative_sales")
    def test_submit_saves_zero_without_waiting_for_sales_summary(
        self, get_cumulative_sales, save_report, _get_report
    ):
        save_report.return_value = {"submitted_at": "2026-09-29T12:00:00"}
        payload = DailyReportPayload(
            report_date=date.today(),
            listing_count=0,
            optimization_count=0,
            violation_triggered=False,
            infringement_triggered=False,
            stocking_audit_rate=100,
            reverse_product_count=0,
            all_issues_resolved=True,
        )
        background_tasks = BackgroundTasks()

        result = report_routes.submit_daily_report(
            payload, background_tasks, {"userId": "17", "role": "operator"}
        )

        self.assertEqual(result["message"], "提交成功")
        self.assertEqual(save_report.call_args.args[1]["cumulative_sales"], Decimal("0.00"))
        self.assertEqual(len(background_tasks.tasks), 1)
        get_cumulative_sales.assert_not_called()

    @patch("routers.reports.report_service.update_sales_snapshot")
    @patch("routers.reports.report_service.save_report")
    @patch("routers.reports.report_service.get_report", return_value={
        "cumulative_sales": Decimal("12.34"), "stocking_audit_rate": 100
    })
    @patch("routers.reports.report_service.get_cumulative_sales", return_value={
        "status": "available", "amount": Decimal("10.88")
    })
    def test_submit_ignores_client_amount_and_refreshes_authoritative_value_in_background(
        self, get_cumulative_sales, _get_report, save_report, update_sales_snapshot
    ):
        save_report.return_value = {"submitted_at": "2026-09-29T12:00:00"}
        payload = DailyReportPayload(
            report_date=date.today(),
            cumulative_sales=Decimal("999999.99"),
            listing_count=0,
            optimization_count=0,
            violation_triggered=False,
            infringement_triggered=False,
            stocking_audit_rate=100,
            reverse_product_count=0,
            all_issues_resolved=True,
        )
        background_tasks = BackgroundTasks()

        report_routes.submit_daily_report(
            payload, background_tasks, {"userId": "17", "role": "operator"}
        )

        self.assertEqual(save_report.call_args.args[1]["cumulative_sales"], Decimal("12.34"))
        get_cumulative_sales.assert_not_called()
        background_tasks.tasks[0].func(*background_tasks.tasks[0].args)
        update_sales_snapshot.assert_called_once_with(17, date.today(), Decimal("10.88"))

    @patch("routers.reports.report_service.get_report", return_value={
        "cumulative_sales": Decimal("12.34"), "stocking_audit_rate": Decimal("100.00")
    })
    @patch("routers.reports.report_service.save_report")
    @patch("routers.reports.report_service.get_cumulative_sales", side_effect=SQLAlchemyError("source unavailable"))
    def test_sales_source_failure_does_not_block_submit_or_overwrite_saved_snapshot(
        self, get_cumulative_sales, save_report, _get_report
    ):
        save_report.return_value = {"submitted_at": "2026-09-29T12:00:00"}
        payload = DailyReportPayload(
            report_date=date.today(),
            listing_count=0,
            optimization_count=0,
            violation_triggered=False,
            infringement_triggered=False,
            stocking_audit_rate=100,
            reverse_product_count=0,
            all_issues_resolved=True,
        )
        background_tasks = BackgroundTasks()

        result = report_routes.submit_daily_report(
            payload, background_tasks, {"userId": "17", "role": "operator"}
        )
        self.assertEqual(result["message"], "提交成功")
        self.assertEqual(save_report.call_args.args[1]["cumulative_sales"], Decimal("12.34"))

        with self.assertLogs("routers.reports", level="ERROR"):
            background_tasks.tasks[0].func(*background_tasks.tasks[0].args)
        get_cumulative_sales.assert_called_once_with(17, date.today())

    @patch("routers.reports.report_service.get_cumulative_sales", side_effect=SQLAlchemyError("source unavailable"))
    @patch("routers.reports.report_service.get_target", return_value=None)
    @patch("routers.reports.report_service.get_report", return_value=None)
    def test_get_keeps_daily_report_available_when_sales_source_fails(
        self, _get_report, _get_target, _get_cumulative_sales
    ):
        result = report_routes.my_daily_report(date.today(), {"userId": "17", "role": "operator"})

        self.assertIsNone(result["report"])
        self.assertEqual(result["sales_summary"]["status"], "source_error")
        self.assertEqual(result["sales_summary"]["source"], "dny_data")
        self.assertIsNone(result["sales_summary"]["amount"])

    @patch("routers.reports.report_service.get_cumulative_sales")
    @patch("routers.reports.report_service.get_target", return_value=None)
    @patch("routers.reports.report_service.get_report", return_value=None)
    def test_form_data_can_load_without_waiting_for_sales_summary(
        self, _get_report, _get_target, get_cumulative_sales
    ):
        result = report_routes.my_daily_report(
            date.today(),
            {"userId": "17", "role": "operator"},
            include_sales_summary=False,
        )

        self.assertIsNone(result["report"])
        self.assertEqual(result["sales_summary"]["status"], "pending")
        get_cumulative_sales.assert_not_called()

    @patch("routers.reports.report_service.get_cumulative_sales", return_value={"status": "mapping_missing", "amount": None})
    @patch("routers.reports.report_service.get_target", return_value=None)
    @patch("routers.reports.report_service.get_report", return_value=None)
    def test_sales_summary_can_be_loaded_separately(self, _get_report, _get_target, get_cumulative_sales):
        result = report_routes.my_daily_sales_summary(
            date.today(), {"userId": "17", "role": "operator"}
        )

        self.assertEqual(result["status"], "mapping_missing")
        self.assertIsNone(result["amount"])
        get_cumulative_sales.assert_called_once_with(17, date.today())

    @patch("routers.reports.report_service.get_cumulative_sales")
    @patch("routers.reports.report_service.get_target", return_value=None)
    @patch("routers.reports.report_service.get_report")
    def test_past_report_keeps_its_saved_sales_snapshot(
        self, get_report, _get_target, get_cumulative_sales
    ):
        report_date = date.today() - timedelta(days=1)
        get_report.return_value = {"cumulative_sales": Decimal("14.50")}

        result = report_routes.my_daily_report(report_date, {"userId": "17", "role": "operator"})

        self.assertEqual(result["sales_summary"]["amount"], Decimal("14.50"))
        self.assertEqual(result["sales_summary"]["source"], "daily_report")
        self.assertEqual(result["sales_summary"]["status"], "snapshot")
        get_cumulative_sales.assert_not_called()

    @patch("routers.reports.report_service.get_report", return_value=None)
    @patch("routers.reports.report_service.save_report")
    @patch("routers.reports.report_service.get_cumulative_sales", side_effect=SQLAlchemyError("source unavailable"))
    def test_sales_source_failure_is_deferred_until_after_submit(self, get_cumulative_sales, save_report, _get_report):
        payload = DailyReportPayload(
            report_date=date.today(),
            listing_count=0,
            optimization_count=0,
            violation_triggered=False,
            infringement_triggered=False,
            stocking_audit_rate=100,
            reverse_product_count=0,
            all_issues_resolved=True,
        )

        background_tasks = BackgroundTasks()
        result = report_routes.submit_daily_report(
            payload, background_tasks, {"userId": "17", "role": "operator"}
        )

        self.assertEqual(result["message"], "提交成功")
        self.assertEqual(save_report.call_args.args[1]["cumulative_sales"], Decimal("0.00"))
        with self.assertLogs("routers.reports", level="ERROR"):
            background_tasks.tasks[0].func(*background_tasks.tasks[0].args)
        get_cumulative_sales.assert_called_once_with(17, date.today())


if __name__ == "__main__":
    unittest.main()
