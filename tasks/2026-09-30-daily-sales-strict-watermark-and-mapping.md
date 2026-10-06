# TASK：日报销售额恢复严格当天水位并排查店铺覆盖

> 历史记录：日报销售额数据源后来由用户更正为 `dny_data`；当前实现依据 `dny_data.rq` 水位，见 `2026-09-30-report-sales-from-dny-data.md`。本文件中的 FBS 数据诊断不再是当前依据。

状态：implemented  
日期：2026-09-30

## 目标

- 按用户最新确认，日报累计销售额只在 `fbs_data` 全表水位达到日报当天时展示和允许提交。
- 解释朱文剑累计金额为零/未显示的原因，并区分人员映射、源数据覆盖和有效零金额。
- 不擅自调整 `dp_ry` 店铺归属，不写入业务数据库。

## 数据库只读诊断

- 当前日报日期：2026-09-30；核查期间 `fbs_data.MAX(sj)` 从 2026-09-28 前进到 2026-09-29。最新查询下当天仍应为 `not_ready`、金额为 `null`、提交应被阻止；9 月 29 日查询已可用。
- 朱文剑对应启用人员记录 `operator.id=89`，`role=leader`。
- `operator.real_name` 与 `dp_ry.yy` 精确匹配 15 个不同店铺编号；首尾及常见空格规范化后数量仍为 15，未发现姓名空格造成的漏配。
- 这 15 个映射编号中，只有 3 个在 `fbs_data` 全历史出现过；另 12 个在 `fbs_data` 完全没有记录。最新查询确认 9 月源表仍只覆盖这 3 个店铺。源数据缺席不能被解释成有效零销售额。
- 对缺失的 12 个编号再去掉括号仓库后缀并做前缀匹配，仍未发现其他源编号；未发现由括号后缀造成的别名匹配问题。
- `dp_ry` 仅有 `yy/qy/fbs/rzsj` 等字段，没有可由当前代码确认的在营状态字段；这 12 个编号是否仍在运营以及是否与 FBS 上游编号一致为 `[NEEDS_CONFIRMATION]`。
- 当前查到的 12 个无历史源数据映射编号：
  - `Lazada-PH63(三仓)`
  - `Lazada-PH85(三仓)`
  - `Shopee-PH289(三仓)`
  - `Shopee-PH90(三仓)`
  - `Shopee-PH91(三仓)`
  - `TikTok-3PF-BL-02(三仓)`
  - `TikTok-3PF-BRHK-05(三仓)`
  - `TikTok-3PF-JM-01(三仓)`
  - `TikTok-3PF-MJ-03(三仓)`
  - `TikTok-3PF-YDU-01(三仓)`
  - `TikTok-3PF-YDU-01MY`
  - `TIKTOK-WGC-11(三仓)`

## 实现范围

- `backend/services/report_service.py`：只在源水位达到日报日时计算累计销售额。
- `tests/test_daily_report_sales.py`：覆盖日报前一天不就绪、日报当天可用。
- `specs/SPEC-011-日报累计销售额自动取数.md`、`docs/API_REPORTS.md`、`AGENTS.md`：同步为严格当天规则。
- 不改 `dp_ry`、`fbs_data`、历史日报或数据库结构。

## 验收标准

- 日报日期 2026-09-30、源水位 2026-09-29 或更早：GET 金额为 `null` 且状态 `not_ready`；POST 返回 409 且不写入。
- 日报日期 2026-09-30、源水位达到 2026-09-30：汇总区间为 2026-09-01 至 2026-09-30。
- 用户可用权威在营店铺清单核对上列 12 个编号；未经确认不得更改分配或自动补映射。

## 验证

- `python -m unittest discover -s tests -v`：14 项通过。
- `python -m compileall -q .`（`backend/`）：通过。
- `npm run build`（`frontend/`）：通过；保留 ECharts 与入口 chunk 超过 500 kB 的既有警告。
- 已重启本项目后端 `8001`，`/health` 返回 `ok`；未触碰 `5173/8000`。
- 浏览器 `/report/submit` 当前日期为 2026-09-30，显示 `—`、数据未就绪并禁用提交；没有写入日报。
- 单测确认源水位为日报日前一天时不执行销售额查询且返回 `not_ready`；水位达到日报日后才返回 `available`。
