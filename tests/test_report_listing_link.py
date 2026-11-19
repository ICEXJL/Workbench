"""日报「上架链接 ID」字段的契约与持久化测试。

2026-11-16 新增：daily_report.listing_link_id，来自填报页「销售与上架」模块，
需要在日报进度列表中可查看。

长度上限为 4000 字符（数据库列是 TEXT）：一个运营每天可能粘贴十几个上架链接 ID，
早期按 VARCHAR(255) 设计时，粘贴超过 255 字符会被静默截断，导致 ID 丢失。
"""
import sys
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from schemas.schemas import DailyReportPayload
from services import report_service


class ListingLinkIdTests(unittest.TestCase):
    def payload(self, **extra):
        return DailyReportPayload(
            report_date=date.today(), listing_count=0, optimization_count=0,
            violation_triggered=False, infringement_triggered=False, stocking_audit_rate=100,
            reverse_product_count=0, all_issues_resolved=True, **extra)

    def test_payload_field_is_optional(self):
        self.assertIsNone(self.payload().model_dump()['listing_link_id'])
        self.assertEqual(
            self.payload(listing_link_id='PH-123').model_dump()['listing_link_id'], 'PH-123')

    def test_payload_accepts_long_multi_id_paste(self):
        """运营一次粘贴十几个 ID 时不能被拒或被截断（此前 255 上限会造成丢失）。"""
        text = ' '.join(['1738586084865115632'] * 100)  # 1999 字符
        self.assertGreater(len(text), 255)
        self.assertEqual(
            self.payload(listing_link_id=text).model_dump()['listing_link_id'], text)

    def test_payload_rejects_text_over_column_length(self):
        with self.assertRaises(ValidationError):
            self.payload(listing_link_id='x' * 4001)

    @patch.object(report_service, 'get_report', return_value={})
    @patch.object(report_service, 'run_execute')
    def test_save_strips_whitespace_and_blanks_become_null(self, execute, _get):
        cases = [('  PH-123  ', 'PH-123'), ('   ', None), ('', None), (None, None)]
        for sent, expected in cases:
            data = self.payload(listing_link_id=sent).model_dump()
            report_service.save_report({'userId': '17'}, data)
            sql, params = execute.call_args.args
            self.assertIn('listing_link_id', sql)
            self.assertIn('listing_link_id=VALUES(listing_link_id)', sql)
            self.assertEqual(params['listing_link_id'], expected, f'输入 {sent!r} 应存 {expected!r}')

    @patch.object(report_service, 'run_query', return_value=[{'listing_link_id': 'PH-123'}])
    def test_mine_read_selects_and_returns_field(self, query):
        self.assertEqual(report_service.get_report(17, '2026-11-16')['listing_link_id'], 'PH-123')
        self.assertIn('listing_link_id', query.call_args.args[0])

    @patch.object(report_service, 'filtered_operator_ids', return_value=[17])
    @patch.object(report_service, 'run_query', return_value=[])
    def test_list_selects_field_for_progress_table(self, query, _ids):
        report_service.list_reports(
            {'userId': '228', 'role': 'admin', 'department': None},
            '2026-11-16', '2026-11-16')
        self.assertIn('r.listing_link_id', query.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
