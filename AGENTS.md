# AI Development Entry Point

本文件是 `project005_订单管理系统` 的 AI 开发入口。仓库中的运行代码是事实来源；README、交接文档、PRD 和验收清单用于补充背景，若彼此不一致，必须先核对代码并在任务记录中说明差异。

## 1. Project Overview

### 项目是什么

这是一个面向东南亚跨境电商运营团队的内部经营数据工作台。当前系统将登录认证、按权限查询销售数据、运营日报填报与查看、月度目标配置、趋势/分布分析和人员目录集中到一个 Vue + FastAPI 应用中。

### 解决的业务问题

- 用在线日报替代运营人员通过 Excel 手工填报和主管人工汇总。
- 让运营、组长、主管和管理端看到与其组织范围匹配的店铺、人员销售和日报数据。
- 将本月累计销售额、月度目标和完成率放到填报流程中，减少人工核对。
- 提供东南亚店铺日销售、人员近 7 日销售、区域/平台趋势和昨日分布视图。

### 当前阶段

项目处于开发验收阶段，不应视为已完成的生产系统。**安全 P0 与权限 P0 已于 2026-10-06 落地并实测闭环**（bcrypt 明文比对已清除、登录限流、越权审计、5 个管理端接口 admin 守卫、SECRET_KEY 弱值启动校验）。RBAC 已于同日完成四角色实测验收：admin/leader/operator/manager 接口矩阵 36/36符合预期，店铺、人员、日报三层范围隔离均验证为真实服务端过滤（leader 28 店铺为 admin 1009 家的严格子集、独有 0），越权专项 8 项全部被拦下，审计表实有 33 条 `deny_role_required`。当前真实剩余风险：日报列表缺部门/店铺/状态筛选、`/report/daily` 后端不返回未提交人员、`org_hierarchy` 调整后无回归测试、范围变更无 CI 守护、业务口径待业务确认。仓库仍无 CI/CD、无数据库迁移/回滚脚本、无 Docker/反向代理配置，后端仅有 42 项单元测试（其中 18 项为权限回归）、前端无自动化测试。

### 核心用户

- `operator`：填写本人当日日报，查看本人可见销售/日报数据。
- `leader`：查看组内运营范围，填写本人日报。
- `manager`：查看名下运营范围（含组内人员），填写本人日报。
- `admin`：查看全量数据、配置月度目标、查看管理分析和人员目录。

角色名称和组织关系来自数据库及 JWT。管理端账号别名等具体账号清单不是前端业务契约，不能在新代码中硬编码扩展。

### Git context

当前分支为 `main`，HEAD 为 `0da52f6`（`docs: 补齐规格、任务记录与 AI 流程文档`），提交历史为 `0da52f6` → `22959a3`（安全 P0 + ECharts 按需引入）→ `d304506` → `4b84024`。

远程仓库**已配置**：`origin` = `https://github.com/ICEXJL/Workbench.git`（2026-10-06 设为公开）。本地提交**尚未推送** —— 本机代理 `127.0.0.1:56975` 对 `github.com:443` 的 CONNECT 返回 502（`api.github.com` 不受影响），需在代理白名单放行 `github.com` 后执行 `git push -u origin main`。

`.idea/`、`.workbuddy/`、`.playwright-mcp/` 等本地目录已在 `.gitignore` 中排除，**不得提交**。每次任务开始仍必须重新运行 `git status --short`，不要依赖本段快照。

## 2. Technology Stack

| 层 | 当前实现 | 事实来源/注意事项 |
| --- | --- | --- |
| 前端 | Vue 3、Vue Router 4、Pinia 2、Ant Design Vue 4、Axios、ECharts 5、Vite 6 | 入口为 `frontend/src/main.js`；页面按路由懒加载。代码还直接导入 `dayjs`，但 `frontend/package.json` 未声明它为直接依赖，需单独确认并补齐依赖时再修改。 |
| 后端 | FastAPI、Uvicorn、Pydantic 2、SQLAlchemy 2、PyMySQL、python-jose、bcrypt、python-dotenv、pandas | 依赖版本约束在 `backend/requirements.txt`；业务查询主要是 SQLAlchemy `text()` 原生 SQL，没有独立 ORM model 层。 |
| 认证 | JWT HS256、bcrypt 密码哈希、Bearer Token | 实现位于 `backend/routers/auth.py` 和 `backend/services/sales_service.py`。**已完成**：bcrypt 校验（无明文比对）、`SECRET_KEY` 弱值启动校验、登录限流（`services/login_throttle.py`，单进程内存态）、越权审计（`services/audit_service.py`）。**仍需**：多实例部署需将限流改为 Redis 共享存储 |
| 数据库 | MySQL，SQLAlchemy Engine 连接池，`utf8mb4` | 连接配置来自 `backend/.env` 或进程环境变量；真实凭据不在仓库文档中。 |
| API | REST 风格 FastAPI，统一业务前缀 `/api/v1`，健康检查 `/health`，自动 OpenAPI `/openapi.json` | 路由位于 `backend/routers/`；前端 Axios `baseURL` 为 `/api/v1`。 |
| 构建 | `npm run dev`、`npm run build`、`npm run preview`；后端直接运行 `python main.py` | Vite 开发代理 `/api` 和 `/health` 到 `127.0.0.1:8000`。 |
| 部署 | README/维护指南描述为 Nginx/宝塔提供 `frontend/dist`，Uvicorn 单独监听后端端口 | 仓库内没有 Dockerfile、docker-compose、Nginx 配置或进程管理配置；生产部署细节需以实际服务器配置为准。 |
| 测试 | 当前没有 `tests/` 下的自动化测试文件，也没有前端测试框架配置 | 已有验证主要是 `python -m compileall -q .`、`npm run build`、接口冒烟和 Word 验收记录。 |

已确认的当前验证命令：

```powershell
cd backend
python -m compileall -q .

cd ..\frontend
npm run build
```

构建会提示 ECharts 和入口 chunk 超过 500 kB；这是性能风险，不是构建失败。

## 3. Repository Structure

```text
.
├── backend/                    FastAPI 后端运行时代码
│   ├── main.py                 应用入口、CORS、路由挂载、启动初始化
│   ├── config.py               环境变量与连接池/Token 配置
│   ├── database.py             SQLAlchemy Engine、只读/写入 helper、启动表检查
│   ├── routers/                HTTP 路由、参数校验入口和权限入口
│   ├── schemas/                Pydantic 请求/响应模型
│   └── services/               认证辅助、权限范围、销售与日报业务 SQL
├── frontend/                   Vue 单页应用
│   ├── src/main.js             应用装配
│   ├── src/router/              路由与前端角色守卫
│   ├── src/layout/              工作台壳、导航、用户菜单和改密弹窗
│   ├── src/views/               登录、销售、统计、日报、目标和人员目录页面
│   ├── src/services/            Axios API 封装
│   ├── src/stores/              Pinia 登录身份状态
│   ├── src/components/          可复用 Vue 组件（当前主要是 ECharts 包装器）
│   ├── src/utils/               请求拦截与统一错误处理
│   ├── public/                  构建时直接复制的 logo 等静态资源
│   └── package.json             前端依赖与脚本
├── specs/                      经确认的功能/接口/数据/安全规格
├── tasks/                      单次 AI 开发任务记录、验收标准和结果
├── docs/                       API、部署、数据字典、ADR 和运维说明
├── tests/                      后端单元/集成、API 和前端端到端测试
├── .ai/                        AI 执行流程、规则和上下文入口
├── sales-bi-refactor-prd/      早期静态设计/重构 PRD 展示稿，不是运行时代码
├── README.md                   项目基线、启动方式、风险与发布门槛
├── DEVELOPMENT_STATUS.md       任务进度和历史验证摘要
├── CURRENT_PRD.md              2026-09-10 历史现状审计，不自动视为最新规格
├── 产品需求文档-PRD.docx       2026-09-17 评审中的日报需求稿
├── 开发TO DO验收清单*.docx      开发/核验记录；最新核验版优先参考
└── 运营日报收集表-进度原型.html 早期日报交互原型
```

目录之间的关系是：`frontend/src/views` 负责把用户操作转换为 API 请求；`frontend/src/services` 不应包含 SQL 或权限判断；`backend/routers` 把 HTTP 请求转换为已校验的 service 调用；`backend/services` 负责组织范围、业务规则和查询组合；`backend/database.py` 是数据库连接与事务边界；MySQL 表结构属于外部业务数据库，不由前端直接访问。

### 目录修改边界

| 目录/文件 | 负责内容 | 可以修改的情况 | 禁止或需先确认的情况 |
| --- | --- | --- | --- |
| `frontend/src/views/` | 页面布局、交互、展示和页面级状态 | 需求已有 Spec 且 API 契约不变或同步更新 | 不得用前端隐藏替代后端授权；不得静默改变字段口径 |
| `frontend/src/services/` | API 请求封装 | 新接口或接口字段变更并同步 API 文档 | 不得在这里拼 SQL、复制权限逻辑或创建重复请求封装 |
| `frontend/src/router/`、`stores/`、`utils/` | 路由守卫、登录状态和请求错误处理 | 认证/导航 Spec 明确要求时 | 不得只改菜单而不补后端鉴权 |
| `backend/routers/` | HTTP 路由、依赖注入、输入参数和 HTTP 状态码 | API Spec 明确修改并更新 OpenAPI/文档 | 不应把复杂 SQL 或跨模块业务逻辑塞进路由 |
| `backend/services/` | 业务规则、可见范围和数据库查询 | 业务规则已有确认且有回归测试 | 不得未经确认重写范围算法或为了格式统一大规模重构 |
| `backend/schemas/` | Pydantic 输入约束和契约模型 | API/字段 Spec 变更时 | 不得放数据库写入或权限副作用 |
| `backend/database.py`、`config.py` | 数据库连接、事务、环境配置、启动表检查 | 数据库/部署 Spec 明确要求时 | 不得把真实凭据写入仓库；DDL 变更必须有记录和回滚说明 |
| `specs/` | 批准后的可执行规格 | 新需求、业务口径、权限、API 或数据结构确认后 | 未确认信息不得写成已实现事实 |
| `tasks/` | 每次 AI 任务的范围、验收和 handoff | 每项开发/修复任务 | 不应存放永久规格；永久规则应进入 `specs/` |
| `docs/` | 面向开发/运维的说明和 API 文档 | 行为、部署、数据字典发生变化时 | API 或数据库变更不能只改代码不改文档 |
| `tests/` | 测试实现与固定夹具 | 新功能、Bug 回归和契约变更时 | 禁止依赖真实生产凭据或污染远程业务数据 |
| `sales-bi-refactor-prd/`、根目录原型/图片 | 设计参考和历史资产 | 设计评审或原型更新任务 | 不得把原型中“目标能力”误当作当前运行能力 |
| `.idea/`、`.workbuddy/` | 本地 IDE/工作记忆和交接辅助文件 | 用户明确要求维护时 | AI 不应覆盖或清理用户未提交内容 |
| `frontend/dist/`、`frontend/node_modules/`、`backend/.env` | 构建/依赖/本地机密 | 按本地工具生成 | 已被忽略，不应提交或写入文档 |

## 4. Architecture

### 主请求链路

```text
用户浏览器
  ↓
Vue 3 页面 / Vue Router / Pinia / Ant Design Vue / ECharts
  ↓ Axios（/api/v1，自动带 Bearer JWT）
FastAPI main.py
  ↓ 路由依赖 get_current_user（JWT 解码、首登改密限制）
routers/auth.py | routers/sales.py | routers/reports.py
  ↓
services/sales_service.py | services/report_service.py
  ↓ SQLAlchemy text() + Engine 连接池
MySQL 业务表
```

### 前端数据流

- `/login` 调用 `/api/v1/auth/login`，将 token、账号、姓名、角色、部门和 `mustChangePassword` 写入 Pinia/localStorage。
- Axios 请求拦截器为 API 请求注入 Bearer Token；401 清理身份并回到登录，403 显示无权限或触发首次改密流程。
- `MainLayout.vue` 根据当前角色过滤导航，但这只是体验层过滤，不能作为安全边界。
- 日销售和人员销售页面分别维护按筛选条件隔离的页缓存，并预取相邻页面；缓存不能扩大后端返回范围。

### 认证与权限数据流

```text
denglu.username/password_hash
  ↓ bcrypt 校验
denglu.operator_id → operator.id
  ↓ 补齐 real_name / role / department
JWT(sub, userId, realName, role, department, mustChangePassword, exp)
  ↓
每个受保护路由的 get_current_user
  ↓
operator + org_hierarchy + dp_ry 计算可见运营/店铺范围
```

当前 `admin`、`manager`、`leader`、`operator` 的范围算法分别在 `report_service.visible_operator_ids` 和 `sales_service._scope_clause` 中实现。两处必须保持一致；任何范围变更都要有权限矩阵和四角色回归测试。

### 销售查询数据流

- `dny_data` 提供日期、店铺、订单量、销售额和仓库等日销售事实。
- `dp_ry` 把店铺映射到运营、组别、部门、区域和仓库，并被用于范围过滤与人员销售聚合。
- `/sales/daily` 先按日期、可见店铺和可选店铺过滤，再返回分页行、总数、汇总和可选店铺。
- `/sales/personnel` 按所选基准日当天及之前 6 天（共 7 天）聚合运营人员的店铺表现，后端分页，前端缓存页。
- `/sales/stats/*`、`/sales/distribution/*` 和 `/sales/management` 当前 service 查询没有统一接收可见范围参数；非 admin 后端限制是发布前必须确认/补齐的风险。

### 日报数据流

- `GET /report/daily/mine` 查询当前 JWT `userId` 的某日日报，同时返回该月 `target_month` 目标。
- `POST /report/daily` 只允许非 admin 的当前用户提交当天数据；路由校验日期、周二字段和上涨/下滑店铺数量与名称数量一致。
- `report_service.save_report` 将前端字段映射到 `daily_report`，以 `operator_id + report_date` upsert，并把上涨/下滑店铺名以 JSON 文本兼容存储。
- `GET /report/daily` 查询可见范围内已有日报；当前前端补齐未提交人员的实现仍是验收中的能力，后端接口本身返回的是已提交记录列表。
- `GET /report/compliance` 由 `leader`、`manager`、`admin` 使用，按可见范围汇总 7 类指标；`operator` 返回 403。

### API surface

所有业务接口挂载在 `/api/v1` 下：

| 路由 | 方法 | 当前用途 | 权限/注意事项 |
| --- | --- | --- | --- |
| `/auth/login` | POST | 用户名密码登录并签发 JWT | 公开入口；失败返回 401 |
| `/auth/change-password` | POST | 当前用户修改密码并换发 Token | 需要当前 Token；首次改密例外放行 |
| `/auth/me` | GET | 返回 JWT 身份 | 需要 Bearer Token |
| `/sales/daily` | GET | 昨日/指定日期店铺日销售分页 | 后端按角色和东南亚店铺范围过滤 |
| `/sales/personnel` | GET | 前 7 天人员/店铺销售分页 | 后端按角色过滤，支持部门/组/运营筛选 |
| `/sales/stats/regional`、`/sales/stats/platform` | GET | 近 7 日区域/平台趋势 | **已挂 `require_roles("admin")`**（2026-10-06），leader 实测 403；service 仍未接收用户范围，全量口径仅对 admin 开放 |
| `/sales/distribution/region`、`/sales/distribution/warehouse` | GET | 昨日区域/仓库分布 | 当前缺少后端角色限制和用户范围参数 |
| `/sales/management` | GET | 人员目录 `name_roles_apt` | 当前缺少后端角色限制 |
| `/report/daily` | GET/POST | 日报列表、当前用户当天提交/覆盖 | GET 目前主要返回已提交记录；POST 只允许非 admin 提交当天 |
| `/report/daily/mine` | GET | 当前用户某日回填和月目标 | userId 来自 JWT，不接受前端指定提交主体 |
| `/report/target` | GET/POST | 读取/保存运营月度目标 | POST 仅 admin；GET 检查目标运营在可见范围 |
| `/report/people` | GET | 返回当前权限范围的有效运营 | 用于日报列表补齐和目标选择 |
| `/report/compliance` | GET | 管理范围内合规指标和人员 | `operator` 返回 403；其他角色按组织范围聚合 |
| `/health` | GET | 服务健康检查 | 不在 `/api/v1`；Vite/Nginx 应代理到 FastAPI |
| `/openapi.json` | GET | FastAPI 自动生成契约 | 可用于接口审阅，不替代手写 API 文档 |

注意：`GET /report/daily` 路由声明了 `status` 参数，但当前调用 `list_reports` 时没有传递它；**部门、店铺、状态筛选仍未完成**。前端 `DailyReportList.vue` 已在客户端拼装未提交人员行（`row_key: missing-*`），但后端只返回已提交记录，大范围下跨页补行会不全。

### Database dependency map

| 表 | 作用 | 访问位置 |
| --- | --- | --- |
| `denglu` | 登录账号、`operator_id`、`password_hash`、首次改密标记 | `sales_service`、`auth` |
| `operator` | 人员主档、姓名、角色、部门、启用状态 | `sales_service`、`report_service` |
| `dp_ry` | 店铺-运营映射、区域、组、部门、仓库 | 销售范围、人员销售、部门补齐 |
| `org_hierarchy` | 主管/组长与运营的组织关系及部门备用值 | 日报/销售范围 |
| `dny_data` | 东南亚店铺每日订单量、销售额、仓库和日期 | 销售与统计 service |
| `daily_report` | 运营日报字段、方向化店铺波动和提交时间 | `report_service` |
| `target_monthly` | 运营按月份的销售/上架目标 | `report_service` |
| `name_roles_apt` | 人员目录展示字段 `name`、`roles`、`apt` | `get_personnel_management` |
| `operation_security_audit` | 安全审计表 | **已投入使用**：`services/audit_service.py` 写入 `deny_role_required`、`login_failed`、`login_blocked_account`、`login_blocked_ip` 等事件，写入失败不影响业务 |

应用当前没有 ORM 模型或版本化迁移目录，表结构由既有 MySQL 业务库提供，启动函数只做少量幂等检查/新增字段。

### 启动时数据库副作用

FastAPI startup 会调用 `init_business_tables()`：检查并可能向 `denglu`、`daily_report` 添加字段，并创建 `operation_security_audit` 表。这不是完整迁移系统；任何新增/修改 DDL 必须先记录到 `docs/` 或专门迁移 Spec，并说明幂等性、锁表风险、回滚和生产执行人。

## 5. Important Business Rules

以下只记录能由当前代码、README、交接文档或验收清单交叉确认的规则。所有未完成或口径冲突均显式标记。

### 身份和可见范围

1. 角色值当前为 `admin`、`manager`、`leader`、`operator`。
2. `admin` 可见启用的全部 `operator`；`manager` 通过 `org_hierarchy.manager_id` 看名下人员并包含自己；`leader` 通过 `org_hierarchy.leader_id` 看组内人员并包含自己；`operator` 只看自己。
3. 销售范围还必须通过 `dp_ry` 的东南亚区域和运营姓名/店铺映射过滤；新增人员或组织关系后要同时核对 `operator.status`、`org_hierarchy`、`dp_ry.yy`。
4. 前端角色菜单和路由守卫不是授权边界，后端必须返回 401/403 并做数据范围过滤。

### 认证和密码

1. 登录按 `denglu.username` 查询，使用 `password_hash` 做 bcrypt 校验；登录身份必须能关联启用的 `operator`。
2. JWT 算法为 HS256，默认有效期配置为 30 天；首次改密标记会阻止访问除改密和 `/auth/me` 外的受保护接口。
3. 新密码至少 8 位，必须含 ASCII 字母和数字，bcrypt 输入不超过 72 字节；成功改密后清空旧 `password` 字段并写入 `password_hash`。
4. 当前 Token 在改密后不会立即失效；是否需要立即撤销由安全 Spec 确认。生产不得使用 `config.py` 中的默认 DB 密码或默认 JWT 密钥回退。

### 销售查询

1. 经营总览默认查询昨天；每页由后端限制在 10–100 行，返回 `items`、`total`、分页信息、汇总和店铺选项。
2. 人员销售默认以昨天为查询基准日，统计该日及之前 6 天；`dd7/xs7` 是基准日，`dd1/xs1` 是最早一天。其他趋势统计接口是否包含当天仍需单独确认。
3. 前端页面展示 USD，但应用层不读取汇率。销售源数据的币种、退款/取消/测试订单是否计入必须由业务确认。

### 日报

1. `operator`、`leader`、`manager` 可以提交本人当天日报；`admin` 不能提交日报。
2. 只能提交或修改 `date.today()` 对应日期；同一运营同一天使用 upsert，重复提交覆盖更新。
3. 周度字段（周延迟/取消、周商责差评链接、周错发/破损链接）只允许周二填写；非周二由接口拒绝非空输入。
4. 备货审核及时率代码只在周一和周三采集，其他日期保留已存在值，首次提交按 100% 记录。该采集日安排需业务再次确认。
5. 上涨/下滑店铺数量必须分别等于对应名称数量；数据库旧的总浮动数量字段继续兼容，未分类历史数据不得伪造方向。
6. 日报销售额由服务端从 `dny_data.xse` 按运营全部 `dp_ry` 店铺自动汇总，日期列为 `dny_data.rq`；统计从当月 1 日到日报日，且 `dny_data` 全表最新日期必须达到日报日，否则不展示金额并阻止提交。不得回退到 `fbs_data`。页面完成率使用此金额与当月目标计算；提交后保存到 `daily_report.monthly_sales` 快照。
7. 月度目标按运营和月份 upsert，保存仅限 `admin`；目标缺失时前端不计算有效完成率并提示联系管理端。

### 明确未确认的业务口径

- [NEEDS_CONFIRMATION] `dny_data.xse` 的上游会计定义、退款/取消/测试订单是否计入。币种按用户确认为 USD，但源表没有币种列，仍需与上游对账。
- [NEEDS_CONFIRMATION] 管理员/主管/组长在历史账号别名、禁用 operator 和组织变更时的完整范围规则。
- [NEEDS_CONFIRMATION] 统计接口是否允许非 admin 使用，以及区域/仓库分布是否必须按角色隔离。
- [NEEDS_CONFIRMATION] 应用、数据库和运营日报的时区；代码使用 Python/MySQL 的本机当前日期。
- [NEEDS_CONFIRMATION] `/sales/stats/*` 趋势接口的“近 7 天”是否应包含今天；其 SQL 使用 `CURDATE()-7` 到 `CURDATE()` 的闭区间。
- [NEEDS_CONFIRMATION] `operation_security_audit` 的写入事件、保留期、访问者和告警流程。
- [NEEDS_CONFIRMATION] 人员目录是只读目录还是未来可编辑的人事管理模块。

## 6. Development Rules

AI 开始任何实现前必须：

1. 阅读本 `AGENTS.md`、`README.md`、相关 `specs/`、任务记录和受影响代码。
2. 明确需求、Acceptance Criteria、接口字段、权限范围、数据库影响和测试策略。
3. 若业务规则无法从代码或批准的 Spec 确认，停止猜测并写出 `[NEEDS_CONFIRMATION]`，等待确认或把任务保持为未完成。
4. 修改代码前不得先做无关重构；不得删除已有能力、改名接口或改变数据口径来“顺手清理”。
5. API 修改必须同步更新 API 文档、前端封装（如适用）、对应 Spec 和回归测试。
6. 数据库结构或查询口径修改必须记录表、字段、索引、迁移/回滚、影响范围和部署顺序。
7. 新功能必须增加测试；Bug 修复必须增加能复现原问题的回归测试。
8. 后端接口和数据库查询变更至少运行 `python -m compileall -q .`；前端变更至少运行 `npm run build`。
9. 权限、认证和数据查询变更必须覆盖未登录、越权、四角色可见范围和错误响应；不能只验证前端页面。
10. 不得把真实 DB 地址、密码、JWT 密钥、Token 或生产数据写入代码、日志、Spec、任务、提交信息或示例。
11. 完成后更新文档、任务状态和 handoff，说明实际验证、未验证项目和剩余风险。

## 7. File Ownership

```text
frontend/src/views/       只负责页面 UI、交互和页面级展示逻辑
frontend/src/services/    只负责前端 API 调用封装
frontend/src/router/      只负责前端导航、路由元数据和体验层守卫
frontend/src/stores/      只负责前端身份/会话状态
frontend/src/utils/       只负责通用请求拦截和错误呈现
backend/routers/          只负责 HTTP 路由、依赖注入、参数和状态码
backend/schemas/          只负责请求/响应数据模型与输入约束
backend/services/         负责业务规则、可见范围和 SQL 查询/写入
backend/database.py       负责连接池、SQL 执行 helper、事务和启动表检查
backend/config.py         负责环境配置，不存业务规则和真实凭据
specs/                     负责批准后的功能、API、权限和数据契约
tasks/                     负责一次性开发任务和验收记录
docs/                      负责 API、部署、数据字典、迁移和运维说明
tests/                     负责单元、集成、API 契约和端到端测试
.ai/                       负责 AI 工作流和工程规则，不放业务实现
```

跨边界修改必须在任务记录中说明原因。特别是：路由不能复制 service 的权限算法；前端不能自行推断或扩大后端数据范围；数据库表不能通过未记录的启动副作用随意变更。

## 8. Testing

### 当前可运行验证

```powershell
# 后端语法/导入级检查
cd backend
python -m compileall -q .

# 前端生产构建
cd ..\frontend
npm ci
npm run build
```

本项目当前没有已提交的自动化测试文件或测试框架配置；`tests/` 是为后续建立测试边界而创建的目录。不要把“构建通过”写成“业务测试通过”。

### 目标测试分层

- `tests/unit/`：service 的范围计算、字段映射、日报校验和纯函数；使用 fixture/mock，不连接生产库。
- `tests/api/`：FastAPI TestClient/HTTP 契约，覆盖 `/health`、OpenAPI、401/403、请求校验、upsert 和响应结构。
- `tests/integration/`：使用隔离 MySQL schema 或受控测试数据库验证 SQL、索引和事务；禁止写入真实业务库。
- `frontend`：当前未配置 Vitest/Playwright；在引入测试框架前先建立前端测试 Spec。至少覆盖登录守卫、401/403 拦截、日报表单和分页筛选。
- 浏览器验收：四角色登录、日报提交/覆盖、目标配置、跨组访问、统计页限制和生产 SPA 刷新；真实凭据和脏数据不能进入仓库。

### API 冒烟基线

至少验证：`GET /health`、`GET /openapi.json`、未登录受保护接口返回 401、角色越权返回 403、日报同日覆盖、目标权限和销售分页范围。数据库不可用时应明确区分配置/连接错误和空结果；当前行为需进一步固化为测试。

## 9. Definition of Done

任务只有同时满足下列条件才能标记完成：

- 代码实现与批准的 Spec 一致。
- Acceptance Criteria 全部满足，未满足项有明确阻塞记录。
- 新功能有测试，Bug 修复有回归测试；测试和构建命令实际通过。
- API、数据库、部署或数据口径变化已同步文档和规格索引。
- 权限、异常处理、空态、加载态和兼容历史数据已检查。
- 没有明显回归问题，没有修改无关文件，没有泄露凭据或生产数据。
- `tasks/` 中有任务结果，`.ai/` 流程要求的 handoff 已生成。

如果只能完成部分工作，必须明确标记 `partial` 或 `blocked`，列出剩余项和下一步，不得用“已完成”掩盖验收缺口。
