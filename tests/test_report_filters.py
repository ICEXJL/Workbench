"""日报列表的部门/组别筛选回归测试（纯单元，不连数据库）。

背景：日报列表页原来只有日期和运营两个筛选，缺部门/组别。
新增筛选时必须满足三个约束：
1. 筛选在**后端**做，不能只过滤前端当前页
2. 筛选只能在**权限范围内收窄**，不能扩大可见范围
3. 部门/组别来源于 `dp_ry`，一人可能属于多个部门或多个组别（顿号分隔）

本测试锁定这三条，防止后续改动把筛选退回前端或突破权限范围。
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from services import report_service  # noqa: E402


def user(role: str, uid: int, name: str = "tester") -> dict:
    return {"sub": name, "userId": str(uid), "realName": name,
            "role": role, "department": "武汉一部", "mustChangePassword": False}


ADMIN = user("admin", 1, "admin")
LEADER = user("leader", 3, "组长甲")


def people_fixture() -> list[dict]:
    """模拟 visible_people 的返回：含多部门、多组别、空值三类边界。"""
    return [
        {"id": 5, "real_name": "运营A", "department": "武汉一部",
         "group_name": "组长甲", "role": "operator"},
        {"id": 6, "real_name": "运营B", "department": "武汉一部",
         "group_name": "组长甲、组长乙", "role": "operator"},   # 多组别
        {"id": 7, "real_name": "运营C", "department": "武汉二部",
         "group_name": "组长乙", "role": "operator"},
        {"id": 8, "real_name": "运营D", "department": "武汉一部、深圳一部",
         "group_name": "组长甲", "role": "operator"},          # 多部门
        {"id": 9, "real_name": "运营E", "department": None,
         "group_name": None, "role": "operator"},              # 全空
        {"id": 3, "real_name": "组长甲", "department": "武汉一部",
         "group_name": "组长甲", "role": "leader"},
    ]


class TestSplitMultiValue(unittest.TestCase):
    """部门/组别是顿号分隔的多值字符串，必须先拆分再比对。"""

    def test_split_by_enumeration_comma(self):
        self.assertEqual(report_service._split_multi("组长甲、组长乙"),
                         {"组长甲", "组长乙"})

    def test_split_none_returns_empty_set(self):
        self.assertEqual(report_service._split_multi(None), set())
        self.assertEqual(report_service._split_multi(""), set())

    def test_split_strips_whitespace(self):
        self.assertEqual(report_service._split_multi(" 武汉一部 、 武汉二部 "),
                         {"武汉一部", "武汉二部"})

    def test_split_single_value(self):
        self.assertEqual(report_service._split_multi("武汉一部"), {"武汉一部"})


class TestFilteredOperatorIds(unittest.TestCase):
    """按部门/组别在权限范围内收窄人员 id。"""

    def _run(self, visible_ids, department=None, group=None):
        with mock.patch.object(report_service, "visible_operator_ids",
                               return_value=visible_ids), \
             mock.patch.object(report_service, "visible_people",
                               return_value=people_fixture()):
            return report_service.filtered_operator_ids(
                ADMIN, department=department, group=group)

    def test_no_filter_returns_all_visible(self):
        ids = self._run([5, 6, 7, 8, 9, 3])
        self.assertEqual(ids, [3, 5, 6, 7, 8, 9])

    def test_filter_by_department(self):
        ids = self._run([5, 6, 7, 8, 9, 3], department="武汉二部")
        self.assertEqual(ids, [7], "只有运营C 属于武汉二部")

    def test_filter_by_group(self):
        ids = self._run([5, 6, 7, 8, 9, 3], group="组长乙")
        self.assertEqual(ids, [6, 7], "运营B 是多组别，应命中组长乙")

    def test_department_and_group_combined(self):
        ids = self._run([5, 6, 7, 8, 9, 3], department="武汉一部", group="组长乙")
        self.assertEqual(ids, [6], "武汉一部 + 组长乙 只有运营B")

    def test_multi_department_person_matches_each(self):
        for dept in ("武汉一部", "深圳一部"):
            ids = self._run([5, 6, 7, 8, 9, 3], department=dept)
            self.assertIn(8, ids, f"运营D 属于{dept}，应被命中")

    def test_null_department_excluded_when_filtering(self):
        ids = self._run([5, 6, 7, 8, 9, 3], department="武汉一部")
        self.assertNotIn(9, ids, "部门为空的人不应出现在具体部门的筛选结果里")

    def test_filter_never_exceeds_visible_scope(self):
        """关键安全约束：筛选只能收窄，不能扩大。"""
        ids = self._run([5], department=None, group=None)
        self.assertEqual(ids, [5], "权限范围只有 1 人时，不得返回其他人")

    def test_filter_rejects_person_outside_scope(self):
        """即使 fixture 里有人，也不得越过 visible_operator_ids 的边界。"""
        ids = self._run([5], department="武汉二部")
        self.assertEqual(ids, [], "运营C 在 fixture 里但不在权限范围内，不应返回")

    def test_unknown_department_returns_empty(self):
        ids = self._run([5, 6, 7, 8, 9, 3], department="不存在的部门")
        self.assertEqual(ids, [])


class TestListReportsAcceptsFilters(unittest.TestCase):
    """list_reports / compliance_overview 必须接受并应用筛选参数。"""

    def test_list_reports_signature_has_filters(self):
        import inspect
        params = inspect.signature(report_service.list_reports).parameters
        self.assertIn("department", params, "list_reports 必须支持 department 参数")
        self.assertIn("group", params, "list_reports 必须支持 group 参数")

    def test_compliance_signature_has_filters(self):
        import inspect
        params = inspect.signature(report_service.compliance_overview).parameters
        self.assertIn("department", params,
                      "compliance_overview 必须支持 department，否则卡片数与表格不一致")
        self.assertIn("group", params)

    def test_list_reports_uses_filtered_ids(self):
        """验证 list_reports 确实调用了 filtered_operator_ids 而不是直接 visible_operator_ids。"""
        with mock.patch.object(report_service, "filtered_operator_ids",
                               return_value=[]) as filt, \
             mock.patch.object(report_service, "visible_operator_ids",
                               return_value=[5]) as vis:
            result = report_service.list_reports(
                ADMIN, "2026-10-01", "2026-10-19", department="武汉一部")
        self.assertEqual(result, [])
        filt.assert_called_once()
        self.assertEqual(filt.call_args.kwargs.get("department"), "武汉一部")

    def test_empty_scope_short_circuits_without_query(self):
        """筛选后无人时不应再查日报表。"""
        with mock.patch.object(report_service, "filtered_operator_ids",
                               return_value=[]), \
             mock.patch.object(report_service, "run_query") as q:
            out = report_service.list_reports(ADMIN, "2026-10-01", "2026-10-19",
                                              department="空部门")
        self.assertEqual(out, [])
        q.assert_not_called()


class TestRoutePassesFilters(unittest.TestCase):
    """路由层必须把 department/group 传给 service。"""

    def _src(self) -> str:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend", "routers", "reports.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_daily_route_has_department_param(self):
        src = self._src()
        idx = src.find("def daily_reports(")
        self.assertNotEqual(idx, -1)
        segment = src[idx:idx + 600]
        self.assertIn("department", segment, "日报列表路由必须接收 department")
        self.assertIn("group", segment, "日报列表路由必须接收 group")

    def test_daily_route_forwards_to_service(self):
        src = self._src()
        idx = src.find("def daily_reports(")
        segment = src[idx:idx + 800]
        self.assertIn("department=department", segment,
                      "路由必须把 department 透传给 service")
        self.assertIn("group=group", segment)

    def test_compliance_route_has_department_param(self):
        src = self._src()
        idx = src.find("def compliance(")
        self.assertNotEqual(idx, -1)
        segment = src[idx:idx + 600]
        self.assertIn("department", segment,
                      "合规汇总路由也必须支持 department，保持与表格口径一致")


class TestPeopleReturnsDeptAndGroup(unittest.TestCase):
    """`/report/people` 必须同时返回部门和组别，供前端做联动下拉。"""

    def test_visible_people_sql_selects_group_name(self):
        with open(report_service.__file__, encoding="utf-8") as f:
            src = f.read()
        idx = src.find("def visible_people(")
        segment = src[idx:idx + 1200]
        self.assertIn("group_name", segment, "visible_people 必须返回组别字段")
        self.assertIn("department", segment, "visible_people 必须返回部门字段")


if __name__ == "__main__":
    unittest.main(verbosity=2)
