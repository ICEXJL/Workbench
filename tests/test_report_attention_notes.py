import sys
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from schemas.schemas import DailyReportPayload
from services import report_service

class AttentionNotesTests(unittest.TestCase):
    def payload(self, **extra):
        return DailyReportPayload(report_date=date.today(), listing_count=0, optimization_count=0,
            violation_triggered=False, infringement_triggered=False, stocking_audit_rate=100,
            reverse_product_count=0, all_issues_resolved=True, **extra)

    def test_payload_preserves_multiline_text_and_defaults_empty(self):
        text = '需跟进补货\n第二行 <普通文本>'
        self.assertEqual(self.payload(attention_notes=text).model_dump()['attention_notes'], text)
        self.assertIsNone(self.payload().model_dump()['attention_notes'])

    @patch.object(report_service, 'get_report', return_value={})
    @patch.object(report_service, 'run_execute')
    def test_upsert_persists_and_can_clear_notes(self, execute, _get):
        for value in ['请跟进\n补货', None, '']:
            data = self.payload(attention_notes=value).model_dump()
            report_service.save_report({'userId': '17'}, data)
            sql, params = execute.call_args.args
            self.assertIn(':attention_notes', sql)
            self.assertIn('attention_notes=VALUES(attention_notes)', sql)
            self.assertEqual(params['attention_notes'], value)

    @patch.object(report_service, 'run_query', return_value=[{'attention_notes': '跟进'}])
    def test_mine_read_selects_and_returns_notes(self, query):
        self.assertEqual(report_service.get_report(17, '2026-11-12')['attention_notes'], '跟进')
        self.assertIn('attention_notes', query.call_args.args[0])

    def test_legacy_rows_have_empty_notes(self):
        self.assertIsNone(report_service._decode_report({})['attention_notes'])

    @patch.object(report_service, 'filtered_operator_ids', return_value=[17])
    @patch.object(report_service, 'run_query', return_value=[{'attention_notes': '提醒'}])
    def test_list_retains_notes_in_scoped_query(self, query, _scope):
        result = report_service.list_reports({'role': 'leader','userId':'3'}, '2026-11-01', '2026-11-12')
        self.assertEqual(result[0]['attention_notes'], '提醒')
        self.assertIn('r.attention_notes', query.call_args.args[0])
        self.assertEqual(query.call_args.args[1]['p0'], 17)

class AttentionNotesApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers import reports
        self.routes = reports
        self.app = FastAPI()
        self.app.include_router(reports.router, prefix='/api/v1')
        self.client = TestClient(self.app)
        self.user = {'userId':'17', 'role':'operator'}

    def login(self, role='operator'):
        self.user['role'] = role
        self.app.dependency_overrides[self.routes.get_current_user] = lambda: self.user

    def test_unauthenticated_read_and_write_are_rejected(self):
        for response in [self.client.get('/api/v1/report/daily'), self.client.post('/api/v1/report/daily', json={})]:
            self.assertEqual(response.status_code, 401)

    def test_submit_mine_and_list_roundtrip_without_database(self):
        self.login()
        record = {}
        def save(user, data):
            record.update(data, operator_id=int(user['userId']), submitted_at='2026-11-12T12:00:00')
            return dict(record)
        def get(*args, **kwargs):
            return dict(record) if record else None
        with patch.object(report_service, 'save_report', side_effect=save), patch.object(report_service, 'get_report', side_effect=get), patch.object(report_service, 'get_target', return_value=None), patch.object(self.routes, '_refresh_sales_snapshot'), patch.object(report_service, 'list_reports', side_effect=lambda *a, **k: [dict(record)]):
            for value in ['跟进补货\n明天复核 <文本>', '']:
                payload = AttentionNotesTests().payload(attention_notes=value).model_dump(mode='json')
                result = self.client.post('/api/v1/report/daily', json=payload)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()['report']['attention_notes'], value)
                mine = self.client.get('/api/v1/report/daily/mine', params={'include_sales_summary':False})
                self.assertEqual(mine.json()['report']['attention_notes'], value)
                self.assertEqual(self.client.get('/api/v1/report/daily').json()[0]['attention_notes'], value)

    def test_admin_cannot_submit_and_other_operator_notes_are_not_queried(self):
        self.login('admin')
        response = self.client.post('/api/v1/report/daily', json=AttentionNotesTests().payload(attention_notes='x').model_dump(mode='json'))
        self.assertEqual(response.status_code, 403)
        for role in ['operator','leader','manager','admin']:
            with self.subTest(role=role), patch.object(report_service, 'filtered_operator_ids', return_value=[17]), patch.object(report_service, 'run_query') as query:
                self.assertEqual(report_service.list_reports({'role':role,'userId':'17'}, '2026-11-01','2026-11-12', operator_id=999), [])
                query.assert_not_called()

    def test_sales_refresh_does_not_overwrite_notes(self):
        from decimal import Decimal
        with patch.object(report_service, 'run_execute') as execute:
            report_service.update_sales_snapshot(17, date.today(), Decimal('10'))
        self.assertNotIn('attention_notes', execute.call_args.args[0])

class AttentionNotesMigrationTests(unittest.TestCase):
    def test_startup_only_adds_column_when_missing(self):
        import importlib.util
        from unittest.mock import MagicMock
        spec = importlib.util.spec_from_file_location('notes_database_test', Path(__file__).resolve().parents[1] / 'backend/database.py')
        database = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database)
        for exists in [False, True]:
            with self.subTest(exists=exists):
                connection = MagicMock()
                def execute(statement, params=None):
                    result = MagicMock()
                    result.scalar_one.return_value = int(exists) if params == {'column':'attention_notes'} else 1
                    return result
                connection.execute.side_effect = execute
                with patch.object(database, 'engine') as engine:
                    engine.begin.return_value.__enter__.return_value = connection
                    database.init_business_tables()
                ddl = [str(call.args[0]) for call in connection.execute.call_args_list if 'ALTER TABLE daily_report ADD COLUMN attention_notes' in str(call.args[0])]
                self.assertEqual(len(ddl), 0 if exists else 1)

if __name__ == '__main__': unittest.main()


