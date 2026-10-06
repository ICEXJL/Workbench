# SPEC-012：经营数据工作台领域规格（销售查询与运营日报）

状态：`implemented`（现状契约已固化；REQ-012-19/20 安全整改已于 2026-10-06 落地并验证）  
创建日期：2026-10-06  
最后更新：2026-10-06  
来源：仓库代码只读核查、`backend/routers/*`、`backend/services/*`、`backend/schemas/schemas.py`、配置 MySQL 结构观察、实测越权请求

## Overview

本项目是面向东南亚跨境电商运营团队的**内部经营数据只读工作台 + 运营日报填报系统**。仓库目录名为 `project005_订单管理系统`，`backend/main.py` 的应用标题亦为"订单管理系统 API"，但代码与数据库中**不存在订单实体**：无订单表、无订单创建/修改/取消接口、无订单状态机。`dny_data.dds` 是按日汇总结论的订单数量（非订单行）。

系统实际承担两项职责：

1. **经营数据查询（只读）**：从 `dny_data`（日销售事实）、`dp_ry`（店铺归属）、`org_hierarchy`（组织层级）读取，按登录人角色过滤可见范围。
2. **运营日报（月度写路径）**：运营按日提交 13+ 项指标，服务端从 `dny_data` 复算累计销售额并保存快照。

本 Spec 的"核心业务流程"因此定义为**销售查询流**与**日报生命周期（含唯一的状态流转与覆盖语义）**，而非订单 CRUD。命名沿用历史，但领域模型以代码为准。

## Scope

- 固化现有 16 个业务接口的领域契约：认证、经营总览、人员销售、趋势与分布、日报、月度目标、合规汇总、人员目录。
- 明确唯一写入路径 `POST /api/v1/report/daily` 的upsert（同日覆盖）语义与状态流转。
- 明确角色可见范围算法（`operator` / `leader` / `manager` / `admin`）及两处实现必须一致的约束。
- 固化累计销售额从 `dny_data` 自动取数的口径（承接 SPEC-011）。
- **新增**：管理端接口后端角色限制、登录限流、强密钥启动校验、遗留明文密码列清理。
- 数据模型字段定义以 2026-10-06 只读观察为准。

## Out of Scope

- 新建订单实体、订单 CRUD 或订单状态机；这属于新业务，需独立立项与数据来源定义。
- 修改或重建 `dny_data` / `fbs_data` 上游同步。
- 自动修复 `dp_ry` 中缺失或错误的店铺归属。
- 补齐 T04/T10 未提交人员补行与部门/店铺/状态筛选（另立需求）。
- 数据库表结构变更；本次安全整改不含 DDL。
- 币种与会计口径的最终定义（依赖上游数据生产方）。

## User Stories

- **REQ-012-01**：作为运营，我希望看到且仅看到本人名下店铺的销售数据。
- **REQ-012-02**：作为组长/主管，我希望看到本人管辖范围内人员及其店铺的销售汇总。
- **REQ-012-03**：作为管理端，我希望查看全公司趋势、分布与人员目录。
- **REQ-012-04**：作为运营，我希望每日提交运营日报；当天可反复修改并覆盖当天记录。
- **REQ-012-05**：作为运营，我希望累计销售额由系统自动计算，无需手工填写且不被他人伪造。
- **REQ-012-06**：作为组长/主管/管理端，我希望查看可见范围内成员的日报填报与合规汇总。
- **REQ-012-07**：作为管理端，我希望为指定运营配置月度销售与listing 目标。
- **REQ-012-08**：作为系统管理员，我希望越权访问被后端拒绝并留下审计记录。

## Functional Requirements

- **REQ-012-09**：所有业务接口必须校验 JWT；无 Token 或 Token 失效返回 `401`。
- **REQ-012-10**：首次登录（`mustChangePassword=true`）除 `/auth/me` 与 `/auth/change-password` 外一律返回 `403 PASSWORD_CHANGE_REQUIRED`。
- **REQ-012-11**：销售类查询必须在服务端按角色注入范围条件，不得依赖前端过滤。
- **REQ-012-12**：`/sales/daily` 默认返回昨日；支持指定日期、店铺筛选、服务端分页（10–100 条/页），并返回 `items`、`total`、`summary`、`stores`。
- **REQ-012-13**：`/sales/personnel` 按基准日当天及前 6 天（共 7 天）聚合，按运营汇总并降序排名；不得展示个人级或跨运营合计列。
- **REQ-012-14**：`/report/daily` POST 仅允许非admin 且仅允许 `report_date` 等于服务器当日；admin 返回 `403`。
- **REQ-012-15**：同一 `(operator_id, report_date)` 重复提交必须更新同一条记录（upsert），不得插入重复行。
- **REQ-012-16**：提交时服务端必须重新计算累计销售额并覆盖写入快照，无条件忽略客户端传入的 `cumulative_sales`。
- **REQ-012-17**：`/report/target` POST 仅 admin；GET 仅当目标运营在本人可见范围内。
- **REQ-012-18**：`/report/compliance` 对 `operator` 返回 `403`。
- **REQ-012-19**（已实现）：`/sales/stats/regional`、`/sales/stats/platform`、`/sales/distribution/region`、`/sales/distribution/warehouse`、`/sales/management`、`/report/people` 必须在后端限制为 admin。
- **REQ-012-20**（已实现）：登录失败需按账号限流并写入 `operation_security_audit`。

## Business Rules

- **BR-012-01**：登录主体唯一来源为 JWT `userId`；任何接口不得以请求参数切换主体。
- **BR-012-02**：角色可见运营范围（`report_service.visible_operator_ids`）：`admin` = 全部 `status=1`；`manager` = `org_hierarchy.manager_id` 匹配 ∪ 本人；`leader` = `org_hierarchy.leader_id` 匹配 ∪ 本人；`operator` = 仅本人。`org_hierarchy.effective_from/to` 存在但当前查询未启用时间过滤。
- **BR-012-03**：店铺可见性（`sales_service._scope_clause`）按 `dp_ry.yy` 匹配运营姓名，并以 `operator.real_name` 为标准名，同时兼容 `real_name LIKE '标准名\_%'` 的历史别名（`status=0`）；`admin` 不加条件。
- **BR-012-04**：`dp_ry.qy='东南亚'` 为店铺可见性的必要条件；日报销售额口径则**不过滤** `qy` / `fbs`（承接 SPEC-011 BR-016）。两处口径差异是既定设计，不得互相套用。
- **BR-012-05**：累计销售额 = 当前运营全部映射店铺（`dpbh` 去重）在 `dny_data` 中 `rq` 落在月初至 `report_date`（含）的 `SUM(xse)`；`dds` 为订单数量，不作为销售额。
- **BR-012-06**：以 `dny_data` 全表 `MAX(rq)` 为同步水位；水位未达 `report_date` 时不计算金额，POST 返回 `409`。
- **BR-012-07**：`daily_report` 唯一键 `(operator_id, report_date)`；`monthly_sales` 为提交时快照，历史记录不随 `dny_data` 变化重算。
- **BR-012-08**：周度字段（`weekly_delay_exceeded`、`weekly_bad_review_links`、`weekly_wrong_damage_links`）仅允许 `report_date.weekday() == 1`（周二）提交；非周二提交且携带任一周度字段返回 `422`。
- **BR-012-09**：`stocking_audit_rate`（备货审核及时率）仅在周一/周三采集；其他日期服务端保留当天既有值，首次提交记为 `100`。
- **BR-012-10**：`volatile_store_count` 由 `rising_shop_count + falling_shop_count` 服务端汇总，客户端传值被忽略；上涨/下滑店铺数量必须与名称数量一致，否则 `422`。
- **BR-012-11**：店铺名称列表接受字符串（按 `,`、`，`、`、`、换行分隔）或数组，统一去空去重后以 JSON 文本存储于 `rising_shop_names` / `falling_shop_names`。
- **BR-012-12**：新密码须 8–128 字符、UTF-8 不超过 72 字节、且同时含ASCII 字母与数字。
- **BR-012-13**：`SECRET_KEY` 为默认值或长度不足时，服务端必须拒绝启动。
- **BR-012-14**：管理端接口拒绝非 admin 时必须写入 `operation_security_audit`。

## Data Model

以下为 2026-10-06 对配置 MySQL 的只读观察，非表结构变更承诺。

### `daily_report`（运营日报，唯一业务写入表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `int unsigned` | PK, auto | — |
| `operator_id` | `int unsigned` | NOT NULL，复合唯一 | 运营 ID，来自 JWT |
| `report_date` | `date` | NOT NULL，复合唯一，索引 `idx_report_date` | 仅允许当日 |
| `monthly_sales` | `decimal(18,2)` | NOT NULL DEFAULT 0.00 | 服务端复算的累计销售额快照；API 别名 `cumulative_sales` |
| `actual_listings` | `int` | NOT NULL DEFAULT 0 | API 别名 `listing_count` |
| `optimized_products` | `int` | NOT NULL DEFAULT 0 | API 别名 `optimization_count` |
| `weekly_late_exceed` | `tinyint` | NULL | API 别名 `weekly_delay_exceeded`，周二项 |
| `violation_flag` | `tinyint` | NOT NULL DEFAULT 0 | API 别名 `violation_triggered` |
| `infringement_flag` | `tinyint` | NOT NULL DEFAULT 0 | API 别名 `infringement_triggered` |
| `weekly_badreview_links` | `int` | NULL | 周二项 |
| `weekly_misship_links` | `int` | NULL | API 别名 `weekly_wrong_damage_links`，周二项 |
| `review_ontime_rate` | `decimal(5,2)` | NOT NULL DEFAULT 0.00 | API 别名 `stocking_audit_rate`，0–100 |
| `reverse_product_cnt` | `int` | NOT NULL DEFAULT 0 | API 别名 `reverse_product_count` |
| `fluctuate_shop_cnt` | `int` | NOT NULL DEFAULT 0 | API 别名 `volatile_store_count`，服务端汇总 |
| `rising_shop_count` | `int` | NOT NULL DEFAULT 0 | 上涨店铺数 |
| `rising_shop_names` | `text` | NULL | JSON 数组文本 |
| `falling_shop_count` | `int` | NOT NULL DEFAULT 0 | 下滑店铺数 |
| `falling_shop_names` | `text` | NULL | JSON 数组文本 |
| `all_issues_resolved` | `tinyint` | NOT NULL DEFAULT 0 | 全部问题已处理 |
| `submitted_at` | `datetime` | NOT NULL DEFAULT CURRENT_TIMESTAMP | 每次覆盖刷新 |

索引：`uk_report_user_date (operator_id, report_date)` 唯一、`idx_report_date` 非唯一。约 450 行。

### 其他相关表

| 表 | 关键字段 | 用途与观察 |
| --- | --- | --- |
| `denglu` | `username`、`password`、`password_hash`、`operator_id`、`must_change_password` | 225 行；全部账号已有 bcrypt `$2b$12$` 哈希；`password` 列仍残留 220 行明文（已无代码读取） |
| `operator` | `id` PK、`real_name` 唯一、`staff_no`、`department`、`role`、`status`、`created_at`、`updated_at` | 224 行；`status=1` 为启用 |
| `org_hierarchy` | `id` PK、`operator_id`、`leader_id`、`manager_id`、`dept`、`effective_from`、`effective_to`、`updated_at` | 219 行；时间字段当前未参与过滤 |
| `dp_ry` | `dpbh`、`yy`、`qy`、`fbs` 等 `VARCHAR(255) NOT NULL` | 1,479 行；无主键/唯一约束 |
| `dny_data` | `dpbh`、`dds`、`xse`、`ckh`、`rq` 均 `VARCHAR NOT NULL` | 约 206,655 行；索引 `idx_dny_rq_dpbh(rq,dpbh)` 非唯一；`rq`/`xse` 为字符串 |
| `fbs_data` / `fbs_dp` / `zl_dp` | — | 存在但**不参与**日报金额口径（承接 SPEC-011） |
| `target_monthly` | `id` PK、`operator_id`、`department`、`month char(7)`、`sales_target decimal(18,2)`、`listing_target`、`status`、`updated_at` | 132 行；按运营+月份覆盖 |
| `name_roles_apt` | `name`、`roles`、`apt` | 3,579 行；`/sales/management` 返回内容 |
| `operation_security_audit` | `id` BIGINT PK AI、`username`、`action`、`detail`、`created_at` | 已建表但**当前 0 行**，无任何写入代码 |

## API Contract

现有 16 个业务接口（`/api/v1` 前缀，`/health` 独立）：

| 方法 | 路径 | 用途 | 权限 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 登录并签发 JWT | 公开 |
| POST | `/auth/change-password` | 改密并换发 Token | 任意已登录（含首登） |
| GET | `/auth/me` | 当前身份 | 任意已登录 |
| GET | `/sales/daily` | 店铺日销售分页 | 按角色范围 |
| GET | `/sales/personnel` | 近 7 日人员销售分页 | 按角色范围 |
| GET | `/sales/stats/regional` | 区域趋势 | **需改admin（实测泄露）** |
| GET | `/sales/stats/platform` | 平台趋势 | **需改 admin（实测泄露）** |
| GET | `/sales/distribution/region` | 区域分布 | **需改 admin（实测泄露）** |
| GET | `/sales/distribution/warehouse` | 仓库分布 | **需改 admin（实测泄露）** |
| GET | `/sales/management` | 人员目录（3,564 条） | **需改 admin（实测泄露）** |
| GET | `/report/daily` | 日报列表 | 按可见范围 |
| POST | `/report/daily` | 提交/覆盖日报 | 非 admin 且仅当日 |
| GET | `/report/daily/mine` | 本人日报 + 目标 + 销售摘要 | 任意已登录 |
| GET | `/report/target` | 读取月目标 | 目标须在可见范围 |
| POST | `/report/target` | 配置月目标 | admin |
| GET | `/report/people` | 可见人员 | **需确认是否限 admin** |
| GET | `/report/compliance` | 合规汇总 | 非 operator |

- **API-012-01**：不得新增或移除上表接口；新增必须先更新本Spec 与 `docs/API_*.md`。
- **API-012-02**：`/report/daily/mine` 响应为 `{report, target, identity, sales_summary}`；`sales_summary.status` ∈ `available` / `not_ready` / `mapping_missing` / `source_error` / `snapshot`，含 `amount`、`currency`、`period_start`、`period_end`、`data_as_of`、`source`。
- **API-012-03**：水位未覆盖时 GET 返回 `not_ready`（日报其他字段仍可读），POST 返回 `409`；源库不可用时 GET 返回 `source_error`，POST 返回 `503`。
- **API-012-04**：历史已提交日报的 `sales_summary.status` 为 `snapshot`，`amount` 取库中快照，`data_as_of` 为 `null`。
- **API-012-05**（已实现）：越权访问返回 `403`，并写入 `operation_security_audit`（`action` 建议 `deny_admin_endpoint`，`detail` 记录路径与主体）。
- **API-012-06**（已实现）：登录失败达阈值返回 `429`。

## UI Requirements

- **UI-012-01**：前端路由守卫按角色过滤菜单；**这不是安全边界**，仅体验层。
- **UI-012-02**：经营总览与人员销售按筛选条件隔离缓存当前页，并静默预取后两页；缓存不得扩大后端返回范围。
- **UI-012-03**：累计销售额为只读展示，无输入控件，不参与必填校验；金额与完成率分子使用同一后端值。
- **UI-012-04**：未就绪时以破折号显示，禁止显示为 `$0.00`；金额未就绪时禁用整份日报提交。
- **UI-012-05**：拦截器统一处理 401（清身份回登录）、403（无权限/首登改密）、网络错误。
- **UI-012-06**：页面金额标注 USD，并展示统计区间与源表数据最新日期。

## State Machine

系统唯一的状态流转是**日报生命周期**（无订单状态机）：

```text
[未提交]
   │ POST /report/daily (report_date == today, 校验通过, status == available)
   ▼
[已提交 snapshot] ──── 同日再次 POST ────► [已提交 snapshot 覆盖更新]
   │                                              submitted_at 刷新
   ▼
读取 GET /report/daily/mine
   ├─ report_date < today 且存在记录 ──► status = snapshot (amount 取库中值)
   ├─ MAX(dny_data.rq) >= report_date ──► status = available (服务端复算)
   ├─ 水位早于 report_date ────────────► status = not_ready，POST 409
   ├─ 无 dp_ry 映射───────────────────► status = mapping_missing
   └─ 源库/转换异常───────────────────► status = source_error，POST 503

无删除路径：日报记录不提供删除接口，纠错方式为同日覆盖。
```

被拒绝的提交不产生状态变更：非当日/admin → `403`；非周二带周度字段 → `422`；数量与名称不一致 → `422`；金额未就绪 → `409`；源异常 → `503`。

## Acceptance Criteria

- **AC-012-01**：以 `operator` 身份登录，其可见店铺集合严格等于 `dp_ry` 中 `yy` 匹配本人（含历史别名）的店铺，且 `qy='东南亚'`；不含他人店铺。
- **AC-012-02**：以 `leader` / `manager` 登录，可见运营集合等于 BR-012-02 定义集合；改写 URL 中的 `operator_id` 不改变返回范围。
- **AC-012-03**：`/sales/daily` 默认返回昨日，分页 `total` 与筛选条件一致，`summary` 为全可见范围汇总（不受分页影响）。
- **AC-012-04**：`/sales/personnel` 结果按运营聚合降序，区间恰为基准日及前 6 天，不含个人级明细列。
- **AC-012-05**：非 admin 提交他人或非当日日报被拒：admin → `403`；非当日 → `403`。
- **AC-012-06**：同一天连续两次 POST，`daily_report` 中该 `(operator_id, report_date)` 仍为 1 行，`submitted_at` 更新，`monthly_sales` 为服务端复算值。
- **AC-012-07**：请求体伪造 `cumulative_sales` 时，落库值仍等于服务端复算值。
- **AC-012-08**：非周二携带周度字段 → `422`；上涨/下滑数量与名称数量不等 → `422`。
- **AC-012-09**：非周一/周三提交时，`stocking_audit_rate` 保留当天既有值；首次提交该日期记为 `100`。
- **AC-012-10**：`dny_data.MAX(rq) < report_date` 时，GET 返回 `not_ready` 且 `amount` 为 `null`，POST 返回 `409` 且不写库。
- **AC-012-11**：读取历史已提交日报时，返回 `status=snapshot`，金额等于落库快照，不按当前 `dny_data` 重算。
- **AC-012-12**：`operator` 访问 `/report/compliance` → `403`；非 admin 访问 `POST /report/target` → `403`。
- **AC-012-13**：`operator` / `leader` / `manager` 访问 5 个管理端接口全部返回 `403`，且审计表新增对应记录；admin 访问仍为 `200` 且响应内容不变。
- **AC-012-14**：以默认 `SECRET_KEY` 或长度 < 32 的配置启动时进程立即失败并给出明确提示。
- **AC-012-15**：同一账号 5 分钟内登录失败达 5 次后返回 `429`，且审计表记录失败事件。
- **AC-012-16**：修改请求中的 `operator_id`、姓名或 `userId` 均不能读取或写入他人数据，主体恒为有效 JWT `userId`。
- **AC-012-17**：四个角色各自登录后，页面可见店铺数与 `dp_ry` 只读抽样一致（须以权威店铺清单核对后断言）。

## Test Cases

- **TEST-012-01**：范围测试——四个角色可见运营 ID 集合与 BR-012-02 一致；别名运营不重复计数。
- **TEST-012-02**：越权测试——非 admin 访问 6 个管理端接口断言 `403`；admin 断言 `200` 且条目数不变。
- **TEST-012-03**：审计测试——触发一次越权后 `operation_security_audit` 新增一行，`action`/`username` 非空。
- **TEST-012-04**：upsert 测试——同日两次提交断言行数不变、`submitted_at` 递增、金额为复算值。
- **TEST-012-05**：校验测试——非当日、非周二带周度字段、数量/名称不一致、伪造金额四类输入分别断言状态码。
- **TEST-012-06**：销售额边界测试——月初前排除、月初与日报日包含、日报日后排除；`rq`/`xse` 非法文本不得静默为 0。
- **TEST-012-07**：水位测试——水位落后一天返回 `not_ready` 且不执行汇总；水位达标返回 `available` 且 `period_end` 为日报日。
- **TEST-012-08**：快照回归——历史日报读取不被新版本回算或改写。
- **TEST-012-09**：密钥与限流测试——弱密钥启动失败；超阈值登录返回 `429`。
- **TEST-012-10**：前端测试——403/401 拦截行为、金额只读、未就绪显示破折号且禁用提交。
- **TEST-012-11**：分页测试——`total` 不随页码变化；`summary` 为全范围汇总而非当页汇总。

## Traceability Matrix

| Requirement | Business Rule | API/UI | Acceptance | Tests |
| --- | --- | --- | --- | --- |
| REQ-012-09、REQ-012-10 | BR-012-01 | 全部接口 | AC-012-16 | TEST-012-01 |
| REQ-012-11 | BR-012-02、BR-012-03、BR-012-04 | API-012-01 | AC-012-01、AC-012-02、AC-012-17 | TEST-012-01 |
| REQ-012-12、REQ-012-13 | BR-012-03 | `/sales/daily`、`/sales/personnel` | AC-012-03、AC-012-04、AC-012-11 | TEST-012-11 |
| REQ-012-14、REQ-012-15 | BR-012-07、BR-012-08、BR-012-09、BR-012-10、BR-012-11 | API-012-02 | AC-012-05、AC-012-06、AC-012-08、AC-012-09 | TEST-012-04、TEST-012-05 |
| REQ-012-16 | BR-012-05、BR-012-06、BR-012-07 | API-012-03、API-012-04、UI-012-03 | AC-012-07、AC-012-10、AC-012-11 | TEST-012-06、TEST-012-07、TEST-012-08 |
| REQ-012-17 | BR-012-02 | `/report/target` | AC-012-12 | TEST-012-01 |
| REQ-012-18 | BR-012-02 | `/report/compliance` | AC-012-12 | TEST-012-02 |
| REQ-012-19 | BR-012-14 | API-012-05 | AC-012-13 | TEST-012-02、TEST-012-03 |
| REQ-012-20 | BR-012-13 | API-012-06 | AC-012-14、AC-012-15 | TEST-012-09 |

## Risks

- **RSK-012-01**：管理端接口目前无后端限制，实测 `operator` 可获取全公司数据（`/sales/management` 单次 349 KB / 3,564 条）。这是当前最高优先级风险。
- **RSK-012-02**：`SECRET_KEY` 当前为默认值 `please-change-this-in-production`，等于密钥公开；可伪造任意角色（含 admin）的 Token。
- **RSK-012-03**：`denglu.password` 残留 220 行明文，虽无代码读取，但构成凭据泄露面。
- **RSK-012-04**：数据库密码已在聊天中出现，需轮换；轮换与更换 `SECRET_KEY` 会导致全体人员重新登录。
- **RSK-012-05**：范围算法在 `sales_service._scope_clause` 与 `report_service.visible_operator_ids` 两处独立实现，存在漂移风险；任何修改必须同步。
- **RSK-012-06**：`dp_ry` / `dny_data` 关键列为字符串且无唯一约束，同店同日重复行会被逐行累加。
- **RSK-012-07**：3 名启用 `operator` 无 `dp_ry` 映射，空结果不能等同于真实零销售额。
- **RSK-012-08**：`daily_report.monthly_sales` 为 `NOT NULL DEFAULT 0.00`，数据未就绪时必须阻止整份提交，无法部分保存。
- **RSK-012-09**：项目无隔离测试库，`tests/` 仅 2 个单元测试文件；禁止对真实业务库写测试数据。
- **RSK-012-10**：前端构建存在 ECharts（约 1,037 kB）与入口 chunk（约 1,535 kB）超 500 kB 警告，为性能风险而非构建失败。
- **RSK-012-11**：仓库名与应用标题含"订单"，与实际领域不符，可能导致后续开发者误判系统边界。

## Open Questions

- **OQ-012-01**：`/report/people` 当前仅返回本人可见人员（实测 operator 得 1 条），危害小；是否一并限制为 admin 待业务确认。
- **OQ-012-02**：`dny_data.xse` 的上游会计定义（退款、取消单、测试订单是否计入）无法从本库确认；页面按用户确认显示 USD，属 [NEEDS_CONFIRMATION]。
- **OQ-012-03**：登录限流阈值未确认。提案：同账号 5 分钟内失败 5 次锁定 15 分钟；需权衡东南亚跨时区办公误伤风险。
- **OQ-012-04**：轮换数据库密码与 `SECRET_KEY` 的执行窗口与通知方式待确认；换密钥会使全部现存 Token 立即失效。
- **OQ-012-05**：朱文剑名下的 12 个 `dp_ry` 店铺编号在源表全历史无记录，仍需运营系统权威店铺清单核对归属（承接 SPEC-011 OQ-013）。
- **OQ-012-06**：是否将项目/应用名称从"订单管理系统"更名为贴合实际的名称，需业务确认后统一处理。

## Deviation Notes

本Spec 与既有文档不一致之处，以代码为准并记录如下：

| 文档说法 | 代码/数据库事实 |
| --- | --- |
| README：「明文密码比对仍在」 | 已修复。`_password_matches` 仅走 `bcrypt.checkpw`；225 个账号全部具备 `$2b$12$` 哈希，无仅明文账号 |
| README：「需完成密码哈希迁移」 | 已完成。遗留 `password` 列明文无代码读取，仅需清理 |
| README/AGENTS：「统计接口 service 未接收用户范围」 | 属实。`/sales/stats/*`、`/sales/distribution/*`、`/sales/management` 共6 个接口无范围过滤，实测可越权 |
| `schemas.py` 注释：累计销售额「recalculates from fbs_data」 | 注释过期。实际来源为 `dny_data`（承接 SPEC-011） |
| 目录名/应用标题：「订单管理系统」 | 无订单实体、无订单表、无订单状态机；`dny_data.dds` 为日汇总订单数量 |