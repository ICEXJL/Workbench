# 日报接口说明

业务前缀：`/api/v1`。以下接口均需 Bearer Token。

## 查询本人日报与销售摘要

`GET /api/v1/report/daily/mine?report_date=YYYY-MM-DD`

前端可传 `include_sales_summary=false` 先读取日报、目标和身份，跳过销售汇总；随后可独立调用 `GET /api/v1/report/daily/mine/sales-summary?report_date=YYYY-MM-DD` 加载销售摘要，避免销售数据查询阻塞表单操作。省略该参数时仍返回完整销售摘要，保持原接口行为。

日报主体始终取自当前 JWT 的 `userId`，不接受客户端指定运营 ID。响应保留原有 `report`、`target`、`identity`，并新增 `sales_summary`：

| 字段 | 说明 |
| --- | --- |
| `amount` | 累计销售额，JSON 数值；实时值按全部映射店铺月累计销售额的 75% 计算并保留两位小数；未就绪或无店铺映射时为 `null` |
| `currency` | `USD` |
| `period_start` / `period_end` | 日历月第一天至日报日，首尾均包含；只有源水位达到日报日时才返回金额 |
| `data_as_of` | `dny_data` 全表最新 `rq` 日期；历史快照没有该元数据时为 `null` |
| `source` | `dny_data` 或历史快照 `daily_report` |
| `status` | `available`、`not_ready`、`mapping_missing`、`source_error`、`snapshot`；基础信息快速模式另有 `pending` |

当日报日期早于服务器当天且已存在日报时，`sales_summary` 使用已保存快照，不读取新源值。其他情况从 `operator.real_name -> dp_ry.yy -> dp_ry.dpbh -> dny_data.dpbh` 汇总当前运营的全部映射店铺，不按区域或 `fbs` 标记过滤。销售额取 `dny_data.xse`，日期取 `dny_data.rq`；不查询或回退到 `fbs_data`。源表全局最新日期必须达到日报日才可计算，并按月初至日报日汇总，再乘以 75% 并四舍五入到美分；若水位未达到，返回 `not_ready`、`amount: null`，即使仅落后一天也不展示。有效零额返回 `0.00`，不是 `null`。

源数据库不可用或日期/金额格式异常时，GET 仍返回日报其他字段，并以 `source_error` 和 `amount: null` 表示销售额暂不可用。无映射时返回 `mapping_missing`，`amount` 为 `null`。

## 提交或更新本人今日日报

`POST /api/v1/report/daily`

日报日期、角色、必填项、周度字段和店铺波动规则沿用现有校验。请求中的 `cumulative_sales` 仅为旧客户端兼容，服务端忽略客户端值。提交请求不再同步等待销售汇总：新建日报立即以 `0.00` 保存，更新日报立即保留已有销售额快照；响应后的后台任务会按 JWT 主体和 `report_date` 查询销售额，查询可用时再更新 `daily_report.monthly_sales`。日报列表和目标完成率读取该快照。当前前端不发送该字段。

| HTTP 状态 | 条件 |
| --- | --- |
| `403` | 管理端提交，或提交日期不是当天，或既有角色/日期规则不满足 |
| `422` | 周度字段、店铺业绩波动名称数量等请求内容不符合规则 |
| `200` | 日报已保存；销售摘要由响应后的后台任务异步刷新，销售源暂不可用不会阻塞本次提交 |

`daily_report.monthly_sales` 为 `DECIMAL(18,2) NOT NULL DEFAULT 0.00`，无需修改表结构。未映射或源数据未就绪时，页面显示本次使用的金额；已有有效快照不会因源数据暂不可用而被覆盖。接口不回填历史日报。

## 查询权限范围内的日报和填报人员

- `GET /api/v1/report/daily?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&operator_id=ID` 返回权限范围内已提交的日报记录。
- `GET /api/v1/report/people` 返回权限范围内可参与日报的有效人员，用于日报列表筛选和补齐未提交行。
- 两个接口均排除 `operator.role='admin'` 的管理端账号；管理端不参与运营日报填报。`admin` 调用时只会看到启用的非管理端人员。
- 前端将已提交日报与 `/report/people` 中尚未提交的人员合并展示，因此上述两个接口都必须保持该角色过滤。
