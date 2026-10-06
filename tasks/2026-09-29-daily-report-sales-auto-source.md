# TASK：日报累计销售额自动取数

> 历史记录：本任务记录初始 FBS 方案；当前来源已由用户更正为 `dny_data`，以 `2026-09-30-report-sales-from-dny-data.md` 为准。

状态：implemented（SPEC-011 的业务口径已由用户确认）  
日期：2026-09-29

## 目标

日报累计销售额由当前登录运营在 `dp_ry` 分配的全部店铺，从 `fbs_data.xse` 自动汇总；按 USD 展示；区间为当月 1 日至日报日（含）；服务端提交时重算，并保存到既有 `daily_report.monthly_sales` 快照。

## 已确认规则

- 不按 `qy` 或 `fbs` 字段过滤店铺。
- 源表水位未覆盖日报日时不展示累计额、不允许人工补录、不提交整份日报。
- 合法零额有效；历史日报继续显示已有快照。
- `cumulative_sales` 是兼容用 API 属性，实际数据库列为 `daily_report.monthly_sales`。
- `monthly_sales` 当前为 `DECIMAL(18,2) NOT NULL DEFAULT 0.00`，本任务不修改数据库结构。

## 实现范围

- `backend/services/report_service.py`：JWT 主体关联运营与全部去重店铺、按月区间汇总、判断 `fbs_data` 全表日期水位、严格解析金额。
- `backend/routers/reports.py`：GET 返回 `sales_summary`；POST 忽略客户端金额、服务端重算；源未就绪返回 `409`，源数据错误返回 `503`。
- `backend/schemas/schemas.py`：`cumulative_sales` 变为可选兼容字段。
- `frontend/src/views/report/DailyReportForm.vue`：只读金额、区间和水位提示、等待/错误状态及未就绪时禁用提交；完成率使用同一服务端金额。
- `docs/API_REPORTS.md`、`specs/SPEC-011-日报累计销售额自动取数.md`、`specs/INDEX.md`：同步 API、业务规则及状态。
- `tests/test_daily_report_sales.py`：添加自动汇总和接口规则单测。

## 验收结果

- **AC-1**：月初前与日报日后数据不计入，月初和日报日行参与汇总；测试覆盖多店和其他店铺排除。
- **AC-2**：主体来源为服务端 `userId`；SQL 店铺查询以该 ID 关联运营名，参数化传递。
- **AC-3**：前端没有金额输入控件；完成率使用服务端自动金额。
- **AC-4**：旧客户端伪造金额不会覆盖服务端重算值；数据未就绪或 SQL 错误不写入。
- **AC-5**：USD、两位小数、统计区间和 `data_as_of` 已实现。
- **AC-6**：映射缺失、未就绪、零金额、金额解析错误与数据库源错误分别处理。
- **AC-7**：历史列表/记录快照读取逻辑未修改；历史日报 GET 显示原快照。

## 验证

- `python -m unittest discover -s tests -v`：11 项通过。
- `python -m compileall -q .`（`backend/`）：通过。
- `npm run build`（`frontend/`）：通过；Vite 报告既有 ECharts/主 bundle 超过 500 kB 警告。
- OpenAPI 路由加载检查：通过。
- `GET http://127.0.0.1:8000/health`：`{"status":"ok"}`。
- `http://127.0.0.1:5173/`：HTTP 200。
- 原 `8000` 后端进程未启用热重载且被运行环境策略保护。另起新版后端 `8001` 和前端 `5174`，已确认 Vite 页面 HTTP 200、代理健康检查通过、未登录日报接口返回 401。预览地址为 `http://localhost:5174/report/submit`；新端口的登录态独立。
- SQL 仅执行只读结构/聚合检查；未写业务库、无 DDL、无历史回填。

## 风险与后续

- `fbs_data` 为稀疏日表，因此使用全表 `MAX(sj)` 作为同步水位；无法识别单个店铺单独晚到。若上游提供批次完成标记，需重新评估。
- 生产 SQL 表没有 `fbs_data` 或 `dp_ry` 索引，运营映射较大时动态 `IN` 列表和月份扫描可能变慢；当前未做 DDL。
- `fbs_data` 没有币种字段；USD 是本次业务确认，不是数据库可验证属性。
- 数据未就绪时暂缓整份日报提交是由 `monthly_sales NOT NULL DEFAULT 0.00` 导出的实现决定；如需其他行为，先批准数据库迁移/异常填报 Spec。

## 回滚策略

只回退本任务列出的接口、service、schema、表单、测试及文档改动；不清理原先存在的未提交文件，不改数据库数据或结构。回滚前重新检查 `git status --short` 并逐文件核对。
