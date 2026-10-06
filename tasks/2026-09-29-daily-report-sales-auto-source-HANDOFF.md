# HANDOFF：日报累计销售额自动取数

> 历史记录：初始实现使用 `fbs_data`，后续已按用户确认改为 `dny_data`。当前有效来源以 `SPEC-011` 和 `2026-09-30-report-sales-from-dny-data-HANDOFF.md` 为准。

## 当前状态

SPEC-011 已按用户确认的业务口径实现。业务代码、测试、API 文档、SPEC、索引和 TASK 均已同步。未修改数据库结构/数据，未做历史日报回填。

## 实现行为

- 按 JWT `userId` 找到 `operator.real_name`，取得其在 `dp_ry` 中全部去重的 `dpbh`，不按区域或 `fbs` 过滤。
- 按日报月份首日至日报日（含）合计 `fbs_data.xse`，金额两位小数、USD。
- 以 `fbs_data` 全表 `MAX(sj)` 作为同步水位。低于日报日时 GET 给出 `not_ready`/空金额，POST 返回 `409`。
- GET 同时返回既有 `report`、`target`、`identity` 和 `sales_summary`。历史已提交日报使用 `monthly_sales` 快照。
- POST 对旧 `cumulative_sales` 保持兼容但忽略其值，始终由服务端重算。源 SQL/数据格式错误时不写记录；GET 保留日报字段并返回 `source_error`，POST 返回 `503`。
- 前端销售额只读；未就绪显示破折号并禁用提交，不以 `$0.00` 代表缺失。真实零额显示为 `$0.00`。

## 验证结果

- `python -m unittest discover -s tests -v`：11 项通过。
- `python -m compileall -q .`（`backend/`）：通过。
- `npm run build`（`frontend/`）：通过。已有 bundle 体积警告：ECharts chunk 和主 chunk 超过 500 kB。
- OpenAPI 报表路由检查通过。
- 本地后端健康检查通过；Vite `5173` 返回 HTTP 200。
- 当前后端进程未启用热重载，运行环境策略拒绝替换 `8000` 进程。为让用户查看新代码，已不改仓库配置地并行启动新版 FastAPI `8001` 和 Vite `5174`，代理健康检查通过；原有 `8000/5173` 未中断。新版页面地址为 `http://localhost:5174/report/submit`，新端口可能要求用户重新登录。

## 风险 / 未确认项

- `fbs_data.sj` 全表水位无法判定某个运营的单店是否迟到；源表没有批次完成标记。若上游添加此信息，应以正式 Spec 调整。
- `xse` 没有币种/会计定义元数据；USD 按用户口径处理，但退款和平台费用口径不能从数据库确认。
- `dp_ry` 和 `fbs_data` 缺少查询索引，后续应基于线上数据量评估并单独设计迁移/回滚。
- 当前日报列为 `NOT NULL DEFAULT 0.00`，未就绪时暂缓整份日报提交。若业务需要先提交其他字段，应另行批准 nullable/missing 状态的数据模型变更。

## 下一步

1. 在 `http://localhost:5174/report/submit` 浏览器验证只读金额、日期区间、零额和未就绪状态；需用户使用合法账号登录，不在测试中写入真实日报。
2. 与上游确认 `fbs_data.MAX(sj)` 是否代表全量批次完成；若不代表，新增数据批次状态契约。
3. 对照 `specs/SPEC-011-日报累计销售额自动取数.md` 与线上运行情况复核后，才考虑优化查询索引。

## 工作区保护

任务开始前已有未提交改动：`backend/services/sales_service.py`、`frontend/src/views/dashboard/PersonnelSales.vue`、`frontend/src/views/report/DailyReportList.vue`，以及 `.idea/`、`.workbuddy-ai/`、`.workbuddy/`、`AGENTS.md`、`.ai/`、`docs/`、`specs/`、`tasks/`、`tests/` 和一个 Word 验收清单。保留这些文件，不回退或清理无关改动。
