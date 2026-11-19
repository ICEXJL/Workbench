# 销售接口说明

## 经营总览店铺销售

`GET /api/v1/sales/daily`

默认查询昨天的数据；前端以 `start_date=昨天`、`end_date=昨天` 初始化。支持 `start_date`、`end_date`、`store`、`page`、`page_size`、`sort_by` 和 `sort_order`，按闭区间聚合每个可见店铺的订单量和销售额。日期范围必须使用 `YYYY-MM-DD`，且开始日期不能晚于结束日期；`target_date` 仅保留为旧客户端兼容参数。前端提供周度汇总（昨天及往前 6 天）、本月汇总（本月 1 日至昨天）和上月汇总快捷按钮，点击后会同步更新日期范围。

范围查询返回的 `items` 按店铺聚合，`ckh` 为该店铺涉及的仓库列表，响应额外返回 `period_start` 与 `period_end`。`summary` 始终对应完整筛选范围，不受分页影响；`stores` 只包含当前用户权限范围内、在该时间范围有数据的店铺。权限过滤在后端执行。

## 运营人员近 7 日销售

`GET /api/v1/sales/personnel`

查询基准日期当天及之前 6 天（共 7 天）的东南亚运营销售数据，日期区间两端均包含。未传 `cxrq` 时默认基准日期为昨天。支持 `cxrq`、`department`、`group`、`operator`、`page` 和 `page_size` 参数；默认按 20 名运营分页。

### 响应字段

- `items`：每名运营一条记录，聚合其名下店铺和平台；按 7 日 `total_sales` 从高到低排列。
- `dd7` / `xs7` 至 `dd1` / `xs1`：表格按最近日期到最早日期展示；`dd7` / `xs7` 对应 `cxrq`，`dd1` / `xs1` 对应 `cxrq` 前第 6 天。
- `total_orders` / `total_sales`：该运营查询区间的订单总数和销售额（USD）；`total_sales` 用于排序。
- `avg_sales`：该运营 7 天销售额除以 7，保留两位小数，显示在“平台”列右侧的“七日日均（USD）”列。
- `summary.total_orders` / `summary.total_sales`：当前登录用户权限范围及部门/组别/运营筛选范围内，所有运营在 7 天窗口的订单数与销售额合计；不受分页影响。
- `total`、`page`、`page_size`：运营人数及分页状态。
- `options`：权限范围内可用的部门、组别和运营筛选项。

`items` 的 `total_orders` / `total_sales` 是当前运营名下各店铺账号的 7 日合计；`summary` 是同一权限、筛选及日期条件下所有可见运营的整体合计。人员销售页保留原有逐日列，仅在表格底部固定展示整体汇总行。

## 人员销售自定义日期与店铺明细

`GET /api/v1/sales/personnel` 支持 `start_date`、`end_date`，两者必须同时提供，按闭区间汇总；未提供时保留旧客户端的 `cxrq` 七日查询兼容行为。当前人员销售页面默认传入昨天至昨天，返回 `total_orders`、`total_sales` 和按区间天数计算的 `avg_sales`。

`GET /api/v1/sales/personnel/{operator_name}/stores` 返回该运营在权限范围内名下的全部店铺，支持 `start_date`、`end_date`。店铺即使在日期范围内没有销售记录也会返回，订单数和销售额为 0；结果按销售额、订单数降序及店铺编号升序排列。接口复用后端组织范围校验，不能通过前端参数查看越权运营。
