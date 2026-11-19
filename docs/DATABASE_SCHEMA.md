# 数据库表结构与风险说明

> 核验日期：2026-10-09。字段、索引、默认值和外键来自当前后端配置所连接数据库的 `information_schema` 只读核验，并与后端 SQL 使用情况交叉检查。本文不记录数据库地址、库名、账号、密码、哈希或业务明细。表行数未作为精确指标：InnoDB 的 `TABLE_ROWS` 是估算值。

## 1. `operation_security_audit` 是什么

这是后端的**安全事件审计表**，用于追踪认证失败和服务端权限拒绝，方便排查账号被锁、异常登录和越权访问。它不是运营业务流水，也不是记录每次日报修改的完整审计历史。

目前代码会记录以下事件：

| `action` | 含义 | 当前写入场景 |
| --- | --- | --- |
| `login_failed` | 登录失败 | 账号密码校验失败 |
| `login_blocked_account` | 账号限流 | 账号处于锁定期仍尝试登录 |
| `login_blocked_ip` | IP 限流 | IP 限流开启且来源 IP 被限制；该功能当前默认关闭 |
| `deny_role_required` | 角色权限不足 | 后端角色守卫拒绝访问 |

`detail` 当前保存简短文本：登录事件可能包含来源 IP，权限拒绝会包含角色和请求路径；代码不会把密码或 JWT 写入该表。审计写入失败会被捕获，不会中断登录/业务请求，因此它提高可追查性，但当前不保证审计写入失败时有可靠告警。

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增 | 审计记录编号，主键 |
| `username` | `VARCHAR(100)` | 是 | 无 | 涉及的登录账号；账号不存在时也可能记录用户输入 |
| `action` | `VARCHAR(100)` | 否 | 无 | 安全事件类型 |
| `detail` | `VARCHAR(500)` | 是 | 无 | 事件补充信息；当前是非结构化文本 |
| `created_at` | `DATETIME` | 否 | 当前时间 | 事件写入数据库的时间 |

索引：主键 `id`；普通索引 `idx_audit_created_at(created_at)`。没有账号、事件类型的索引，没有保留期或自动归档策略。

## 2. 当前后端直接使用的表

当前后端代码对数据库执行 SQL 的表共 9 张。下面列出核验到的字段结构；“无”表示数据库列没有定义默认值，“—”表示该列允许空值或不适用。代码位置用于说明用途，不代表该表只能被该处访问。

### 2.1 `denglu`：登录账号

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `username` | `VARCHAR(255)` | 否 | 无 | 登录账号 |
| `password` | `VARCHAR(255)` | 否 | 无 | 历史明文密码兼容字段；当前登录不读取它，修改密码时会清空 |
| `password_hash` | `VARCHAR(100)` | 否 | 无 | bcrypt 密码哈希，当前登录唯一使用的密码凭据 |
| `operator_id` | `INT UNSIGNED` | 是 | 无 | 关联 `operator.id` 的人员身份；数据库未设外键 |
| `must_change_password` | `TINYINT(1)` | 否 | `1` | 是否要求首次登录后修改密码，`1` 是、`0` 否 |

索引：**当前无主键、无索引、无唯一约束**。主要代码：`backend/services/sales_service.py`、`backend/routers/auth.py`。账号表无主键/用户名唯一约束是高优先级风险，详见第 5 节。

### 2.2 `operator`：人员和权限主档

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `id` | `INT UNSIGNED` | 否 | 自增 | 人员 ID，主键 |
| `real_name` | `VARCHAR(50)` | 否 | 无 | 人员姓名；当前有唯一索引 |
| `staff_no` | `VARCHAR(20)` | 是 | 无 | 员工编号 |
| `department` | `VARCHAR(50)` | 是 | 无 | 人员主档部门 |
| `role` | `VARCHAR(20)` | 否 | `operator` | 系统角色：`operator`、`leader`、`manager`、`admin` |
| `status` | `TINYINT` | 否 | 无 | 人员状态；当前逻辑以 `1` 表示有效/在职 |
| `created_at` | `DATETIME` | 否 | 无 | 记录创建时间 |
| `updated_at` | `DATETIME` | 否 | 无 | 记录更新时间 |

索引：主键 `id`；唯一索引 `uk_operator_real_name(real_name)`。主要代码：`backend/services/sales_service.py`、`backend/services/report_service.py`。这是权限角色和人员身份的权威来源；`name_roles_apt.roles` 仅用于目录展示，不应代替此处角色。

### 2.3 `dp_ry`：店铺、运营和组织属性映射

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `xh` | `INT` | 否 | 无 | 来源数据序号 |
| `dpbh` | `VARCHAR(255)` | 否 | 无 | 店铺编号 |
| `qy` | `VARCHAR(255)` | 否 | 无 | 区域/业务区域；销售范围查询使用它筛选“东南亚” |
| `fhck` | `VARCHAR(255)` | 否 | 无 | 发货仓库 |
| `yy` | `VARCHAR(255)` | 否 | 无 | 运营姓名；当前多处查询以姓名与 `operator.real_name` 匹配 |
| `zm` | `VARCHAR(255)` | 否 | 无 | 组别/组名，人员销售筛选使用 |
| `zg` | `VARCHAR(255)` | 否 | 无 | 主管/责任人来源字段；当前核心权限查询不以它作为授权依据，具体口径应由上游数据字典确认 |
| `fgs` | `VARCHAR(255)` | 否 | 无 | 分公司/区域组织字段 |
| `bm` | `VARCHAR(255)` | 否 | 无 | 部门来源字段，用于人员部门补齐 |
| `jc` | `VARCHAR(255)` | 否 | 无 | 部门简称/简称字段，人员销售筛选使用 |
| `fbs` | `VARCHAR(255)` | 否 | 无 | FBS 来源字段；当前核心查询未使用，具体业务含义应由上游数据字典确认 |
| `rzsj` | `VARCHAR(255)` | 否 | 无 | 入职时间来源字段；应用按日期展示/聚合，但数据库仍存为文本 |

索引：**当前无主键、无索引、无唯一约束**。主要代码：`backend/services/sales_service.py`、`backend/services/report_service.py`。它既承担店铺映射，也被用于人员/部门补齐，因此重复映射和姓名不一致会同时影响销售聚合、日报金额和可见数据。

### 2.4 `org_hierarchy`：运营、组长、主管关系

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `id` | `INT UNSIGNED` | 否 | 自增 | 关系记录 ID，主键 |
| `operator_id` | `INT UNSIGNED` | 否 | 无 | 运营人员 ID，逻辑关联 `operator.id` |
| `leader_id` | `INT UNSIGNED` | 否 | 无 | 组长人员 ID，逻辑关联 `operator.id` |
| `manager_id` | `INT UNSIGNED` | 否 | 无 | 主管人员 ID，逻辑关联 `operator.id` |
| `dept` | `VARCHAR(50)` | 是 | 无 | 组织关系中的部门备用值 |
| `effective_from` | `DATE` | 是 | 无 | 关系生效日期 |
| `effective_to` | `DATE` | 是 | 无 | 关系失效日期；字段注释约定空值表示仍有效 |
| `updated_at` | `DATETIME` | 否 | 无 | 关系更新时间 |

索引：主键 `id`；唯一索引 `uk_org_chain(operator_id,leader_id,manager_id)`；普通索引分别覆盖 `operator_id`、`leader_id`、`manager_id`。主要代码：`backend/services/report_service.py`、`backend/services/sales_service.py`、`backend/services/permission_scope.py`。当前权限 SQL 没有按 `effective_from/effective_to` 过滤；如果表中保留历史关系，必须确认是否会扩大当前可见范围。

### 2.5 `dny_data`：东南亚每日销售事实

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `dpbh` | `VARCHAR(255)` | 否 | 无 | 店铺编号 |
| `dds` | `VARCHAR(255)` | 否 | 无 | 订单数；目前以文本存储 |
| `xse` | `VARCHAR(255)` | 否 | 无 | 销售额；目前以文本存储，日报按 USD 口径展示 |
| `ckh` | `VARCHAR(255)` | 否 | 无 | 仓库号/仓库字段 |
| `rq` | `VARCHAR(255)` | 否 | 无 | 日期；目前以文本存储，代码依赖标准日期字符串格式 |

索引：普通索引 `idx_dny_rq_dpbh(rq,dpbh)`；无主键，也没有 `(日期, 店铺)` 唯一约束。主要代码：`backend/services/sales_service.py`、`backend/services/report_service.py`。日报累计销售额在应用层将来源金额乘以 `0.75` 后保存快照；该换算规则不由数据库字段记录。

### 2.6 `daily_report`：运营日报

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `id` | `INT UNSIGNED` | 否 | 自增 | 日报记录 ID，主键 |
| `operator_id` | `INT UNSIGNED` | 否 | 无 | 提交人 ID，逻辑关联 `operator.id` |
| `report_date` | `DATE` | 否 | 无 | 日报日期 |
| `monthly_sales` | `DECIMAL(18,2)` | 否 | `0.00` | 截至日报日的累计销售额快照；当前业务口径为 USD、源金额乘以 75% |
| `actual_listings` | `INT` | 否 | `0` | 实际上架数量 |
| `optimized_products` | `INT` | 否 | `0` | 产品优化数量 |
| `weekly_late_exceed` | `TINYINT` | 是 | 无 | 周延迟率/取消率是否超标；周度可选，通常 `0/1` |
| `violation_flag` | `TINYINT` | 否 | `0` | 是否触发违规/扣分，通常 `0/1` |
| `infringement_flag` | `TINYINT` | 否 | `0` | 是否链接侵权/禁售，通常 `0/1` |
| `weekly_badreview_links` | `INT` | 是 | 无 | 周商责差评达到阈值的链接数 |
| `weekly_misship_links` | `INT` | 是 | 无 | 周错发/破损达到阈值的链接数 |
| `review_ontime_rate` | `DECIMAL(5,2)` | 否 | `0.00` | 备货审核及时率百分比 |
| `reverse_product_cnt` | `INT` | 否 | `0` | 产品反推数量 |
| `fluctuate_shop_cnt` | `INT` | 否 | `0` | 店铺业绩波动店铺总数，当前由上涨数与下滑数相加得到 |
| `rising_shop_count` | `INT` | 否 | `0` | 上涨店铺数量 |
| `rising_shop_names` | `TEXT` | 是 | 无 | 上涨店铺名称；当前以 JSON 文本保存 |
| `falling_shop_count` | `INT` | 否 | `0` | 下滑店铺数量 |
| `falling_shop_names` | `TEXT` | 是 | 无 | 下滑店铺名称；当前以 JSON 文本保存 |
| `attention_notes` | `TEXT` | 是 | `NULL` | 选填注意事项，多行纯文本，空值隐藏；2026-11-12 新增 |
| `all_issues_resolved` | `TINYINT` | 否 | `0` | 当天问题是否都解决，通常 `0/1` |
| `submitted_at` | `DATETIME` | 否 | 当前时间 | 日报提交/最后更新时刻 |

索引：主键 `id`；唯一索引 `uk_report_user_date(operator_id,report_date)`，保证同一运营同一天只有一份日报并支持 upsert；普通索引 `idx_report_date(report_date)`。主要代码：`backend/services/report_service.py`、`backend/routers/reports.py`。

### 2.7 `target_monthly`：人员月度目标

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `id` | `INT UNSIGNED` | 否 | 自增 | 目标记录 ID，主键 |
| `operator_id` | `INT UNSIGNED` | 否 | 无 | 目标所属运营 ID，逻辑关联 `operator.id` |
| `department` | `VARCHAR(50)` | 是 | 无 | 配置时保存的部门快照 |
| `month` | `CHAR(7)` | 否 | 无 | 目标月份，格式 `YYYY-MM` |
| `sales_target` | `DECIMAL(18,2)` | 否 | `0.00` | 月销售额目标 |
| `listing_target` | `INT` | 否 | `0` | 月上架数量目标 |
| `status` | `TINYINT` | 否 | 无 | 目标状态；当前写入 `1` 表示启用 |
| `updated_at` | `DATETIME` | 否 | 无 | 目标更新时间 |

索引：主键 `id`；唯一索引 `uk_target_oper_month(operator_id,month)`；普通索引 `idx_target_month(month)`。主要代码：`backend/services/report_service.py`。

### 2.8 `name_roles_apt`：人员目录展示数据

| 字段 | 类型 | 可空 | 默认值 | 中文含义 |
| --- | --- | --- | --- | --- |
| `name` | `VARCHAR(255)` | 是 | 无 | 目录姓名 |
| `roles` | `VARCHAR(255)` | 是 | 无 | 目录角色/岗位描述 |
| `apt` | `VARCHAR(255)` | 是 | 无 | 组织路径或权限描述 |

索引：当前无主键、无索引、无唯一约束。主要代码：`backend/services/sales_service.py` 的人员目录查询。该表仅供管理员目录展示，不是登录账号或后端授权的权威来源。

## 3. 数据库内其他表

当前数据库元数据中另有 6 张表，但在本项目后端 Python SQL 中没有直接查询或写入；这不代表其他程序一定没有使用，删除前必须找表所有者确认。

| 表 | 当前结构所示用途 | 当前项目中的状态 |
| --- | --- | --- |
| `fbs_data` | 店铺、订单数、销售额、时间 | 后端没有 SQL 访问；`schemas.py` 仍有一条“从 fbs_data 重算”的过期注释，实际日报取数来自 `dny_data` |
| `fbs_dp` | FBS 店铺名与平台 ID 映射 | 后端没有 SQL 访问 |
| `zl_dp` | 店铺、上级/直属关系、组别、入职时间、部门等来源字段 | 后端没有 SQL 访问 |
| `hermes_conversation` | AI/助手会话头信息 | 后端没有 SQL 访问 |
| `hermes_message` | 会话消息内容和顺序 | 后端没有 SQL 访问 |
| `user` | 通用人员基础信息 | 后端没有 SQL 访问；表名 `user` 在部分 SQL 方言中是关键字，查询时通常需引用 |

建议先确认这些表是否由导入脚本、其他应用或人工报表使用，再决定是否保留、迁移或归档；本次不建议直接删除。

## 4. 逻辑关系与索引概览

```text
denglu.operator_id ──逻辑关联──> operator.id
                                  │
                                  ├── org_hierarchy.operator_id / leader_id / manager_id
                                  ├── daily_report.operator_id
                                  └── target_monthly.operator_id

dp_ry.yy ──按姓名匹配──> operator.real_name
dp_ry.dpbh ──店铺编号匹配──> dny_data.dpbh
daily_report(operator_id, report_date) ──唯一──> 每人每天一份日报
target_monthly(operator_id, month) ──唯一──> 每人每月一条目标
```

上图中的人员、姓名和店铺连接目前**大多是应用约定，不是数据库外键**。当前库未发现任何声明式外键约束。

已有的较关键索引：

| 表 | 索引 | 作用 |
| --- | --- | --- |
| `dny_data` | `(rq,dpbh)` | 按日期和店铺读取销售事实 |
| `daily_report` | 唯一 `(operator_id,report_date)`、普通 `(report_date)` | 日报 upsert、按日期查询 |
| `target_monthly` | 唯一 `(operator_id,month)`、普通 `(month)` | 月目标 upsert、按月份查询 |
| `operator` | 唯一 `(real_name)` | 人员身份匹配 |
| `org_hierarchy` | `(operator_id)`、`(leader_id)`、`(manager_id)` 和唯一关系链 | 组织范围查询 |
| `operation_security_audit` | `(created_at)` | 按时间检索审计记录 |

`denglu`、`dp_ry`、`name_roles_apt` 当前都没有索引；其中 `denglu` 和 `dp_ry` 是优先检查对象。

## 5. 主要隐患与改进建议

### P0：先处理完整性和安全边界

1. **`denglu` 缺少主键、用户名唯一约束和索引。** 账号重复时，登录查询使用 `LIMIT 1` 可能拿到不确定记录；账号规模增长后也会全表扫描。先只读检查重复账号和空白账号，再备份、清理冲突，最后增加主键/唯一索引。不要直接对生产表执行 DDL。
2. **业务关系没有外键。** `denglu.operator_id`、`daily_report.operator_id`、`target_monthly.operator_id`、`org_hierarchy` 的人员 ID 都可能出现孤儿引用。先盘点孤儿与历史例外，再逐表增加外键；默认优先考虑 `RESTRICT`，避免误删人员时连带删除日报/审计相关数据。
3. **审计表没有保留与告警策略。** 明确保留期、归档方式、谁可以查询；对“写入失败”增加独立日志/监控告警。避免把密码、Token、完整请求体或不必要的个人信息写入 `detail`。
4. **组织有效期字段没有进入当前权限 SQL。** 如果 `org_hierarchy` 中存在历史关系，旧主管/组长可能继续看到已不属于其范围的人员。确认业务是否需要历史可见范围，再统一在所有权限查询中应用有效期，并补四角色回归测试。

### P1：数据类型、映射质量与查询性能

1. **`dny_data.dds`、`xse`、`rq` 都是 `VARCHAR(255)`。** 订单数、金额、日期用字符串会依赖 MySQL 隐式转换/固定格式，非法值可能导致错误聚合或日期范围漏查。先建数据校验报告与清洗流程，再评估迁移为 `BIGINT/INT`、`DECIMAL(18,2)`、`DATE`；核对历史异常后再考虑唯一键 `(rq,dpbh)`。
2. **`dp_ry` 没有主键、索引和唯一性约束。** 当前按 `dpbh`、`yy`、`qy` 等连接/筛选，可能扫描全表；同店铺多条映射还可能放大销售汇总。先确定稳定行 ID 和允许的历史/多运营规则，去重后再增加主键及按执行计划验证的索引，例如 `(qy,dpbh)`、`(yy,qy)`。不要未经去重就加唯一约束。
3. **姓名连接容易因别名、空格和组织变更失配。** `dp_ry.yy` 按文本连接 `operator.real_name`，代码还需处理后缀身份。长期建议引入规范化人员 ID 映射，让店铺表和权限表使用 ID；迁移前保留名称别名对照并验证覆盖率。
4. **店铺涨跌名称以 JSON 文本放在 `TEXT` 列。** 当前适合整段读取/写入，但难以按店铺检索、统计，也没有 JSON 结构校验。若后续需要按店铺分析，拆为 `daily_report_shop_variation` 子表；若只是页面展示，可将列类型升级为 MySQL `JSON` 并保留迁移校验。
5. **关键取值范围没有数据库约束。** `TINYINT` 标志理论上可写入非 `0/1`，百分比也可超过 `0-100`；当前主要由 API 模型校验，导入脚本或人工 SQL 可以绕过。清理历史异常并确认 MySQL 版本后，给日报标志位、数量、及时率和目标字段增加适当的 `CHECK` 约束。

### P2：提高可维护性和业务可解释性

1. **当前没有版本化数据库迁移和回滚流程。** `backend/database.py` 启动时会检查并添加少量列、创建审计表；这不是完整迁移系统。建议引入 Alembic 或受控 SQL 迁移目录，每次变更记录版本、前置检查、锁表影响、备份和回滚方案，部署时由明确的迁移步骤执行。
2. **销售币种和 75% 计算口径没有随数据保存。** `dny_data` 没有币种字段，日报 `monthly_sales` 保存的是应用按 0.75 系数处理后的快照，但没有记来源版本、换算系数或计算时间。应由业务确认源金额币种与 75% 口径；必要时保存原始金额、调整后金额、币种、系数/规则版本和计算时间，避免未来无法解释历史快照。
3. **日报布尔字段默认 `0` 会把“未填/历史默认”与明确选择“否”混为一谈。** 周度字段用 `NULL` 表示未填较清楚；对需要区分缺报与否的指标，建议允许 `NULL` 或增加提交状态/字段完成度，并核实历史数据后再改变语义。
4. **目录和核心人员模型重复。** `name_roles_apt` 的角色/组织描述与 `operator`、`org_hierarchy` 有重叠，但目录字段没有主键/外键且允许空值。建议确定它是独立通讯录还是历史导入表；若仅展示，逐步改由规范人员表提供字段，避免把展示数据误用于授权。
5. **字段命名风格不统一。** `dp_ry`、`dny_data` 使用拼音缩写，其他表使用英文蛇形命名，维护者需依赖本文件和上游字典。可在新表中统一英文语义名，旧表通过视图/数据访问层逐步兼容，不建议一次性大规模重命名。

## 6. 数据库设计的优点与当前边界

**优点**

- 日报和月目标有复合唯一键，避免同一人员、日期/月度重复写入。
- 核心事实数据与业务录入分离：`dny_data` 提供销售事实，`daily_report` 保存提交快照，`target_monthly` 保存目标。
- `operator`、`org_hierarchy`、`dp_ry` 分别承担人员角色、汇报关系、店铺归属，授权逻辑可在服务端实现，而不只依赖前端菜单。
- `operation_security_audit` 独立记录认证和越权安全事件，且主业务不会因审计库写入失败而被中断。
- 主要高频数据表使用 InnoDB 和 `utf8mb4`，日报与月目标有适用的索引。

**边界/不足**

- 多张导入/映射表没有主键、唯一性约束或索引；数据完整性很大程度依赖代码和人工维护。
- 缺少声明式外键、字段 CHECK 约束和正式迁移/回滚流程。
- 源销售事实采用文本类型，姓名字符串承担关联键；数据质量问题会直接影响权限范围和金额汇总。
- 审计目前覆盖安全失败事件，不覆盖成功登录、改密、日报修改等业务操作，也没有明确的保留、检索授权和告警流程。

## 7. 代码依据

- 表初始化与审计表 DDL：[backend/database.py](../backend/database.py)
- 安全事件写入：[backend/services/audit_service.py](../backend/services/audit_service.py)
- 登录、限流与权限拒绝：[backend/routers/auth.py](../backend/routers/auth.py)
- 人员/销售数据访问：[backend/services/sales_service.py](../backend/services/sales_service.py)
- 日报、目标、可见范围和合规汇总：[backend/services/report_service.py](../backend/services/report_service.py)
- 请求模型：[backend/schemas/schemas.py](../backend/schemas/schemas.py)

本次核验只读，没有执行 `INSERT`、`UPDATE`、`DELETE` 或 DDL。文档描述的是核验时的数据库结构；生产执行任何结构调整前，仍需备份、核对数据质量和安排可回滚的迁移窗口。
