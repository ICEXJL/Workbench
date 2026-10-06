# 日报接口说明

业务前缀：`/api/v1`。以下接口均需 Bearer Token。

## 查询本人日报与销售摘要

`GET /api/v1/report/daily/mine?report_date=YYYY-MM-DD`

日报主体始终取自当前 JWT 的 `userId`，不接受客户端指定运营 ID。响应保留原有 `report`、`target`、`identity`，并新增 `sales_summary`：

| 字段 | 说明 |
| --- | --- |
| `amount` | 累计销售额，JSON 数值；未就绪或无店铺映射时为 `null` |
| `currency` | `USD` |
| `period_start` / `period_end` | 日历月第一天至日报日，首尾均包含；只有源水位达到日报日时才返回金额 |
| `data_as_of` | `dny_data` 全表最新 `rq` 日期；历史快照没有该元数据时为 `null` |
| `source` | `dny_data` 或历史快照 `daily_report` |
| `status` | `available`、`not_ready`、`mapping_missing`、`source_error` 或 `snapshot` |

当日报日期早于服务器当天且已存在日报时，`sales_summary` 使用已保存快照，不读取新源值。其他情况从 `operator.real_name -> dp_ry.yy -> dp_ry.dpbh -> dny_data.dpbh` 汇总当前运营的全部映射店铺，不按区域或 `fbs` 标记过滤。销售额取 `dny_data.xse`，日期取 `dny_data.rq`；不查询或回退到 `fbs_data`。源表全局最新日期必须达到日报日才可计算，并按月初至日报日汇总；若未达到，返回 `not_ready`、`amount: null`，即使仅落后一天也不展示。有效零额返回 `0.00`，不是 `null`。

源数据库不可用或日期/金额格式异常时，GET 仍返回日报其他字段，并以 `source_error` 和 `amount: null` 表示销售额暂不可用。无映射时返回 `mapping_missing`，`amount` 为 `null`。

## 提交或更新本人今日日报

`POST /api/v1/report/daily`

日报日期、角色、周度字段和店铺波动规则沿用现有校验。请求中的 `cumulative_sales` 现在可选，仅为旧客户端兼容；服务端会忽略该值，以 JWT 主体和 `report_date` 重新计算，并将计算结果保存到 `daily_report.monthly_sales`。当前前端不发送该字段。

| HTTP 状态 | 条件 |
| --- | --- |
| `403` | 管理端提交，或提交日期不是当天，或既有角色/日期规则不满足 |
| `409` | `dny_data` 最新日期早于日报日期、尚未覆盖本月可计算区间，或当前运营没有可用店铺映射；不会写入日报 |
| `503` | 源数据库不可用或销售额/日期格式异常；不会写入日报 |

`daily_report.monthly_sales` 当前为 `DECIMAL(18,2) NOT NULL DEFAULT 0.00`。因此累计金额未就绪时整份日报提交会暂缓，避免数据库默认值将缺数伪装为有效零额。接口不改变表结构，也不回填历史日报。
