"""回归测试：区域过滤（2026-10-16 移除 qy='东南亚' 硬编码）。

背景：罗莉娅（id=145, leader）作为组长只查到自己，查不到组员
覃美娟、马欢。根因不是权限逻辑错，而是 `dp_ry` 里这两人的店铺
全部标记为 `qy='MY'`，而 `sales_service` 三处SQL 硬编码 `qy='东南亚'`，
把她们在权限范围内却被区域过滤掉。

修复：移除区域过滤，可见范围完全由 `_scope_clause` 的权限逻辑决定。
本测试锁定两件事：
1. 生成/执行的 SQL 不再含 qy='东南亚'
2. 非东南亚区（如 MY）的组员能被 leader 查到
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from services import sales_service  # noqa: E402


def user(role: str, uid: int, name: str) -> dict:
    return {"sub": name, "userId": str(uid), "realName": name,
            "role": role, "department": None, "mustChangePassword": False}


LEADER_LUOLIYA = user("leader", 145, "罗莉娅")
LEADER_XIAYI = user("leader", 50, "夏伊_W")
OPERATOR_QIN = user("operator", 169, "覃美娟")
ADMIN = user("admin", 228, "向警律")


class TestNoRegionHardcode(unittest.TestCase):
    """源码层面：不得再出现 qy='东南亚' 硬编码。"""

    def _source(self) -> str:
        path = sales_service.__file__
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_no_qy_danya_nanxiang_in_code(self):
        src = self._source()
        # 去掉注释行后再检查，避免注释里的说明文字被误判
        code_lines = [ln for ln in src.splitlines() if not ln.strip().startswith("#")]
        code = "\n".join(code_lines)
        self.assertNotIn("qy='东南亚'", code,
                         "sales_service 不得再硬编码 qy='东南亚'（2026-10-16 已移除）")
        self.assertNotIn('qy="东南亚"', code)

    def test_scope_clause_has_no_region_filter(self):
        clause, _ = sales_service._scope_clause(LEADER_LUOLIYA, "p")
        self.assertNotIn("qy=", clause, "范围子句不应含区域过滤")


class TestLeaderCanSeeNonSEAGroupMembers(unittest.TestCase):
    """行为层面：MY 区组员必须能被 leader 查到。"""

    def test_luoliya_sees_group_members(self):
        """罗莉娅应能看到 3 人：自己 + 覃美娟 + 马欢（后两人在 MY 区）。"""
        rows = [
            {"yy": "罗莉娅", "dpbh": "Lazada-PH39(一仓)"},
            {"yy": "覃美娟", "dpbh": "Shopee-MY17"},          # MY 区
            {"yy": "马欢", "dpbh": "Shopee-MY20"},             # MY 区
        ]
        captured = {}

        def fake(sql, params=None):
            captured["sql"] = sql
            if "COUNT(DISTINCT p.yy)" in sql:
                return [{"total": 3}]
            if "ORDER BY total_sales" in sql:
                return rows
            return []

        with mock.patch.object(sales_service, "run_query", side_effect=fake):
            res = sales_service.get_personnel_sales(
                LEADER_LUOLIYA, "2026-10-05", None, None, None, 1, 50)

        names = {r["yy"] for r in res["items"]}
        self.assertEqual(names, {"罗莉娅", "覃美娟", "马欢"},
                         "组长必须能看到 MY 区的组员")
        self.assertEqual(res["total"], 3)
        self.assertNotIn("东南亚", captured["sql"])

    def test_operator_still_sees_only_self(self):
        """移除区域过滤不得放宽权限：operator 仍只能看到自己。"""
        rows = [{"yy": "覃美娟", "dpbh": "Shopee-MY17"}]

        def fake(sql, params=None):
            if "COUNT(DISTINCT p.yy)" in sql:
                return [{"total": 1}]
            if "ORDER BY total_sales" in sql:
                return rows
            return []

        with mock.patch.object(sales_service, "run_query", side_effect=fake):
            res = sales_service.get_personnel_sales(
                OPERATOR_QIN, "2026-10-05", None, None, None, 1, 50)
        self.assertEqual([r["yy"] for r in res["items"]], ["覃美娟"])

    def test_daily_sales_visibility_has_no_region_filter(self):
        """经营总览的可见性判断也不应含区域过滤。"""
        captured = {}

        def fake(sql, params=None):
            captured.setdefault("sqls", []).append(sql)
            if "COUNT(DISTINCT d.dpbh) stores" in sql:
                return [{"orders": 0, "sales": 0, "stores": 0}]
            if "COUNT(*) total" in sql:
                return [{"total": 0}]
            return []

        with mock.patch.object(sales_service, "run_query", side_effect=fake):
            sales_service.get_daily_sales(LEADER_LUOLIYA, "2026-10-05", None, 1, 20)

        for sql in captured["sqls"]:
            self.assertNotIn("qy='东南亚'", sql)

    def test_options_query_has_no_region_filter(self):
        """筛选下拉选项也不能带区域过滤，否则组员无法被选中。"""
        captured = {}

        def fake(sql, params=None):
            captured["sql"] = sql
            if "COUNT(DISTINCT p.yy)" in sql:
                return [{"total": 3}]
            return []

        with mock.patch.object(sales_service, "run_query", side_effect=fake):
            sales_service.get_personnel_sales(
                LEADER_LUOLIYA, "2026-10-05", None, None, None, 1, 50)
        self.assertNotIn("qy='东南亚'", captured["sql"])


class TestScopeIsolationUnchanged(unittest.TestCase):
    """移除区域过滤后，四角色隔离必须保持单调。"""

    def test_scope_clause_structure_preserved(self):
        """范围子句仍必须以姓名白名单为核心（权限未被削弱）。"""
        clause, params = sales_service._scope_clause(LEADER_LUOLIYA, "p")
        self.assertIn("org_hierarchy", clause, "leader 范围仍必须基于 org_hierarchy")
        self.assertIn("h.leader_id=:scope_id", clause)
        self.assertIn("scope_id", params)

    def test_admin_has_empty_scope(self):
        clause, params = sales_service._scope_clause(ADMIN, "p")
        self.assertEqual(clause.strip(), "", "admin 不应有范围限制")

    def test_operator_scope_is_self_only(self):
        clause, params = sales_service._scope_clause(OPERATOR_QIN, "p")
        self.assertIn("scope_id", params)
        self.assertEqual(int(params["scope_id"]), 169)


if __name__ == "__main__":
    unittest.main(verbosity=2)
