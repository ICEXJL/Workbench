# 销售接口说明

## 运营人员近 7 日销售

`GET /api/v1/sales/personnel`

查询基准日期当天及之前 6 天（共 7 天）的东南亚运营销售数据，日期区间两端均包含。未传 `cxrq` 时默认基准日期为昨天。支持 `cxrq`、`department`、`group`、`operator`、`page` 和 `page_size` 参数；默认按 20 名运营分页。

### 响应字段

- `items`：每名运营一条记录，聚合其名下店铺和平台；按 7 日 `total_sales` 从高到低排列。
- `dd7` / `xs7` 至 `dd1` / `xs1`：表格按最近日期到最早日期展示；`dd7` / `xs7` 对应 `cxrq`，`dd1` / `xs1` 对应 `cxrq` 前第 6 天。
- `total_orders` / `total_sales`：该运营查询区间的订单总数和销售额（USD）；`total_sales` 用于排序，页面不单独显示合计列。
- `total`、`page`、`page_size`：运营人数及分页状态。
- `options`：权限范围内可用的部门、组别和运营筛选项。

`total_sales` 是当前运营名下各店铺账号的 7 日合计；不展示跨运营总额或个人合计列。
