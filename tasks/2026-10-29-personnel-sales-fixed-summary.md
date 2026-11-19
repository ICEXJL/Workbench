# 人员销售底部固定汇总

## 目标

在人员销售页底部固定展示当前用户权限范围及筛选范围内全部运营的近 7 日订单总数和销售额，不受分页影响。

## 范围

- 后端 `/api/v1/sales/personnel` 返回 `summary.total_orders` 和 `summary.total_sales`。
- 汇总查询复用运营销售查询的角色可见范围、部门/组别/运营条件及 7 天日期窗口。
- 前端保留原有逐日列，并在表格底部固定显示筛选范围整体汇总。
- 不修改数据库结构和销售数据口径。

## 验收标准

- [x] 汇总 SQL 基于逐运营聚合，不包含分页限制，并复用权限、筛选、日期条件。
- [x] 页面底部单独固定一行，汇总显示所有当前筛选范围的订单数和销售额，不增加每名运营的合计列。
- [x] 筛选或日期更新后汇总与表格数据使用同一响应刷新。
- [x] 更新销售 API 文档和领域规格。
- [x] 专项测试、后端编译、前端测试与生产构建通过。

## 验证

- `PYTHONPATH=backend python -m pytest -q tests/test_personnel_sales.py tests/test_region_scope.py`：11 passed。
- `python -m compileall -q backend`：通过。
- `npm test`（frontend）：21 passed。
- `npm run build`（frontend）：通过；有既有大 chunk 警告。
- `git diff --check`：通过。

## 风险与未确认项

- 汇总沿用人员销售现有 `dp_ry` 与 `dny_data` 映射及重复映射行为，不改变数据口径。
- 页面仍遵循现有规则：无运营记录时显示表格空态，底部汇总为零。
