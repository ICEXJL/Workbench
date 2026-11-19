# HANDOFF：人员销售底部固定汇总

## 完成内容

- `/api/v1/sales/personnel` 增加 `summary.total_orders` 与 `summary.total_sales`，独立汇总所有匹配运营，排除分页参数。
- 人员销售页保留原有逐日列，仅固定显示底部筛选范围整体汇总行。
- 更新 `docs/API_SALES.md`、SPEC-012 和规格索引。

## 验证结果

- `PYTHONPATH=backend python -m pytest -q tests/test_personnel_sales.py tests/test_region_scope.py`：11 passed。
- `python -m compileall -q backend`：通过。
- `npm test`（frontend）：21 passed。
- `npm run build`（frontend）：通过；Vite 提示既有 ECharts 与入口 chunk 超过 500 kB。
- `git diff --check`：通过。
- HTTP 冒烟：前端 `/personnel` 返回 200，后端 `/health` 返回 `{"status":"ok"}`。

## 未完成项与风险

- 浏览器截图级视觉检查未能自动执行；需要在现有页面刷新后确认固定底部行的实际位置及窄屏表现。
- 当前后台 API 进程仍是旧进程。尝试按 PID 重启时被执行环境拦截，需重启本地后端以加载新响应字段；前端 Vite 页面保持运行。
- 数据结果沿用现有权限和销售 SQL 口径；未连接真实业务库验证汇总数值。

## 下一步

1. 运行人员销售和权限范围专项测试。
2. 运行后端编译检查、前端 Node 测试和 Vite 构建。
3. 浏览器检查 `/personnel` 底部固定行及筛选联动。

## 用户未提交改动

- 开始时 `git status --short --branch` 显示工作区干净。
