# TASK：日报账号店铺销售额改用 dny_data

状态：implemented  
日期：2026-09-30

## 目标

日报金额由当前登录账号对应的 `operator.id`，经 `dp_ry.yy` 取该账号全部店铺，再从 `dny_data` 按 `dpbh` 汇总 `xse`。不再从 `fbs_data` 取日报金额。

保留已确认口径：USD、当月 1 日至日报日（含）、所有映射店铺、不按 `qy` 或 `fbs` 过滤、日报当天数据未到齐时不展示且不允许提交、已提交历史记录仍读快照。

## 已确认的只读数据事实

- `dny_data` 字段为 `dpbh/dds/xse/ckh/rq`，均为 `VARCHAR NOT NULL`；存在 `(rq, dpbh)` 非唯一索引 `idx_dny_rq_dpbh`。
- 全表 209,862 行、1,499 个店铺编号，当前 `MAX(rq)=2026-09-30`。
- 朱文剑（`operator.id=89`）在 `dp_ry` 有 15 个映射店铺，全部能在 `dny_data` 找到；9 月包含 434 个店铺-日期组合。
- `Shopee-PH90(三仓)` 在 `dp_ry.yy` 中归属朱文剑，`dny_data` 有 9 月 1 日至 30 日共 30 行，`SUM(xse)=1518.68`；在 `fbs_data` 中没有该店铺记录。
- 朱文剑映射店铺的 9 月数据不存在同店同日重复，日期和 `xse` 数值均可解析。全表存在 38,903 行空 `dpbh`/空 `rq` 记录，但不会进入已映射店铺和当月日期过滤结果。
- `fbs_data` 与 `dny_data` 三家重叠店铺的行数或金额不同；禁止按缺失店铺混用/回退到 `fbs_data`。

## 影响范围

- `backend/services/report_service.py`：销售摘要来源、水位列和明细日期列改为 `dny_data.rq`。
- `backend/routers/reports.py`：源错误响应标记改为 `dny_data`。
- `tests/test_daily_report_sales.py`：覆盖新来源 SQL、全映射店铺汇总和当天水位门禁。
- `specs/SPEC-011-日报累计销售额自动取数.md`、`specs/INDEX.md`、`docs/API_REPORTS.md`、`AGENTS.md`：同步数据口径。
- 不改 `dny_data`/`fbs_data`、`dp_ry`、数据库结构或历史日报，不改人员销售页面口径。

## Acceptance Criteria

- 当前账号只按 JWT 的 `userId` 确定；服务端以 `operator.real_name -> dp_ry.yy -> dp_ry.dpbh -> dny_data.dpbh` 汇总所有映射店铺。
- 累计金额为 `dny_data.xse` 在当月 1 日至日报日的合计，`dny_data.dds` 不作为销售额。
- 只有 `MAX(dny_data.rq) >= report_date` 才返回可用金额；未达到时返回 `not_ready`/null，POST 返回 409。
- 对朱文剑 2026-09-30，结果包含 `Shopee-PH90(三仓)` 的 9 月数据；不读取 `fbs_data`，不按店铺做来源 fallback。
- 历史快照、目标完成率、保存/权限/API 结构不变。

## 回滚

只回滚本 TASK 涉及的 service、router、test 和文档变更即可；不执行数据库回滚，因为未变更数据库结构或业务数据。保留既有未提交改动。

## 验证

- `python -m unittest discover -s tests -v`：14 项通过。
- `python -m compileall -q .`（`backend/`）：通过。
- `npm run build`（`frontend/`）：通过；仍有既有 ECharts/入口 chunk 超过 500 kB 的 Vite 提示。
- 真实只读调用 `get_cumulative_sales(89, 2026-09-30)`：`available`、`190604.60 USD`、`data_as_of=2026-09-30`，来源为 `dny_data`；未执行日报提交或业务写入。
- 本地 8001 后端已重启，`/health` 返回 `ok`；5174 日报页面刷新后显示朱文剑 2026-09-30 的 DNY 汇总 `$190,604.60`，区间和水位均为 2026-09-01 至 2026-09-30；未提交日报。

交接记录：`tasks/2026-09-30-report-sales-from-dny-data-HANDOFF.md`。
