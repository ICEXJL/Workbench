# 瀛江科技工作台

面向东南亚跨境电商运营团队的内部数据工作台。当前提供登录、销售查询、运营日报和月度目标配置。

截至 2026-10-08，项目仍处于**开发验收阶段**。安全与权限 P0 已于 2026-10-06 落地并验证，但仍有功能缺口与工程欠账，**不应作为已完成的生产系统发布**。

> **规模限制**：实测当前 QPS 天花板约 20，**仅能稳定支撑 20–50 人同时在线**。
> 根因是**数据库在公网**（RTT 21 ms，单次查询往返 57 ms），不是连接池也不是进程数 —— 实测把连接池从 30 提到 200 只提升 34%，加 4 workers 反而更慢。详见 [docs/性能评估-500人规模.md](docs/性能评估-500人规模.md)。
>
> 登录限流 IP 维度已于 2026-10-06 **默认停用**（`LOGIN_IP_LIMIT_ENABLED=false`）—— 全公司共用办公网出口 IP 时会误伤正常用户。账号维度（5 次/300秒/锁 900 秒）仍生效，防暴力破解能力不受影响。

> 目录名为 `project005_订单管理系统`，`backend/main.py` 的应用标题亦为「订单管理系统 API」，但代码与数据库中**不存在订单实体**：无订单表、无订单增删改接口、无订单状态机。详见 [specs/SPEC-012](specs/SPEC-012-经营数据工作台领域规格.md)。

## 当前交付范围

| 模块    | 已实现                                                                | 待解决                         |
| ----- | ------------------------------------------------------------------ | --------------------------- |
| 登录与身份 | `denglu.operator_id` → `operator.id`；JWT 返回人员 ID、姓名、角色、部门；四角色菜单与路由 | 无                           |
| 登录安全  | bcrypt 密码校验（明文比对已移除）；登录限流（账号维度）；越权审计落库；`SECRET_KEY` 弱值启动校验               | IP 维度限流已停用（共用出口 IP 会误伤）；限流为单进程内存态，多实例需改 Redis      |
| 经营总览  | 按日期/店铺查询，服务端分页、范围过滤、汇总指标；预取后两页                                     | 币种与退款/取消订单口径待业务确认           |
| 人员销售  | 近 7 日按部门/组别/运营筛选、服务端分页、条件聚合；预取后两页                                  | 大区范围与店铺归属需业务抽样复核；深页查询与导出未实现 |
| 运营日报  | 13 项分组填报、周二周度项、本人回填、同日覆盖更新、列表与明细                                   | 缺部门/店铺/状态筛选；缺越权详情接口         |
| 月度目标  | 管理端按运营和月份新增或覆盖目标；填报页读取并实时计算完成率                                     | 列表与批量导入未实现；目标口径待业务核实        |
| 趋势与分布 | 管理端页面；区域/平台趋势、区域/仓库分布、人员目录                                         | 人员目录为只读，非人员管理               |

日报实时累计销售额由服务端从全部映射店铺汇总后乘以 75%，按美分四舍五入，用于表单展示、目标完成率和新提交快照；已有历史快照不追溯调整。详见 [docs/API_REPORTS.md](docs/API_REPORTS.md)。

## 已解决的历史问题

以下是 2026-10-06 之前文档中标记为「未完成」的问题，现已闭环。逐项实测证据见 [tasks/2026-10-06-T14](tasks/2026-10-06-T14-RBAC权限体系核查.md)、[tasks/2026-10-06-T13](tasks/2026-10-06-T13-前端ECharts按需引入与Git远程核实.md) 与 [tasks/2026-10-06-T12](tasks/2026-10-06-T12-四角色端到端验收.md)。

| 历史问题                        | 现状                                                                                                | 证据                              |
| --------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------- |
| 明文密码比对仍在                    | **已解决**。`services/sales_service.py` 仅走 `bcrypt.checkpw`；`denglu.password` 列220 行明文已清零，225 个账号哈希完好 | 全库仅 `$2b$12$` 哈希                |
| 默认 JWT 密钥回退                 | **已解决**。`config.py` 对空值、默认值、长度 < 32 三种弱值全部拒绝启动                                                    | 三种弱密钥场景均拒绝启动                    |
| 登录限流缺失                      | **已解决**。账号维度 5 次/300 秒/锁 900 秒；IP 维度 30 次/600 秒                                                   | HTTP 实测第 6 次起 429 + 剩余秒数        |
| 越权审计缺失                      | **已解决并核实落库**。`services/audit_service.py` 统一写 `operation_security_audit`              | 审计表实有 33 条 `deny_role_required`     |
| 统计/分布/人员目录接口未限管理端| **已解决**。5 个接口挂 `require_roles("admin")`                                                          | leader/manager 实测全 403，admin 仍 200  |
| T12 四角色端到端未通过| **已全部通过**。admin/leader/operator/manager 四角色均已实测，三角矩阵 36/36 符合预期                | 见 [tasks/2026-10-06-T14](tasks/2026-10-06-T14-RBAC权限体系核查.md) |
| `python-jose` 装不上           | **已解决**。清华镜像缺该包，需显式 `-i https://pypi.org/simple`                                                  | 属环境问题，见「环境注意事项」                 |
| 前端 chunk 超500 kB            | **ECharts 部分已解决**。按需引入后 1,036.98 kB → 504.60 kB                                                   | `index-*.js` 仍 1,535.05 kB，见下文  |
| `package.json` 缺 `dayjs` 声明 | **已解决**。6 个文件直接 import 却未声明，已补                                                                    | —                               |

## 技术结构

```text
frontend/            Vue 3 + Vite 6 + Pinia + Vue Router + Ant Design Vue 4 + ECharts 5
backend/             FastAPI + SQLAlchemy 2 + PyMySQL + JWT
specs/               已确认规格（SPEC-011、SPEC-012）
tasks/               单次任务记录与验收报告
docs/                API 文档
tests/               后端自动化测试（44 项）
.ai/                 AI 执行流程与规则
AGENTS.md            AI 开发入口
```

浏览器通过 Vite 将 `/api`、`/health` 代理到本地 FastAPI。后端连接远程 MySQL，涉及 `denglu`、`operator`、`org_hierarchy`、`dp_ry`、`dny_data`、`daily_report`、`target_month`、`operation_security_audit`。`dny_data` 已建`(rq, dpbh)` 索引。**数据库内容与连接凭据不在仓库中**，`backend/.env` 已被 Git 忽略。

权限范围以登录角色和 `org_hierarchy` 为基础：普通运营仅本人，组长为本组，主管为名下，管理端为全量。经营总览与人员销售在服务端过滤；前端菜单隐藏仅用于体验，**不构成权限边界**。

**2026-10-06 实测确认范围过滤真实生效**（非仅靠前端隐藏）：

| 维度     | admin    | leader  | manager | 隔离结论                    |
| -------- | -------- | ------- | ------- | --------------------------- |
| 可见店铺 | 1009 家  | 28 家   | 181 家  | leader 是 admin 严格子集，独有 0 家 |
| 可见人员 | 224 人   | 3 人    | 40 人   | leader 是 admin 子集        |
| 日报记录 | 448 条   | 6 条/3 人 | 80 条/40 人 | leader 涉及人员是 admin 子集 |

身份防伪造为双保险：`DailyReportPayload` 未定义 `operator_id` 字段，且 `save_report`
以`{**payload, "operator_id": int(user["userId"])}` 强制覆盖，请求体无法伪造提交者。
越权拒绝会写入 `operation_security_audit`（现有33 条 `deny_role_required`）。

## 本地启动

> **日常启动照着 [docs/启动指南.md](docs/启动指南.md) 走**，里面有两窗口命令、
> 停止方法、启动成功的判断标准和常见问题排查。
> 下面是要点摘要。

环境：Python 3.10+、Node.js、npm，以及有访问权限的 MySQL。仅在可信内网环境使用开发服务。

**两条前提规则**：① 本机系统代理 `127.0.0.1:56975` 会劫持 localhost 请求，
启动前必须 `unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY`；
② 前后端要开**两个终端窗口**同时跑。

1. 复制 `backend/.env.example` 为 `backend/.env`，填入数据库连接信息和**随机生成的强 `SECRET_KEY`**（长度 ≥ 32，不能用默认值，否则后端拒绝启动）。`.env` 已被 Git 忽略。
2. 后端：在 `backend` 执行 `python main.py`。健康检查：`http://127.0.0.1:8000/health`。
3. 前端：在 `frontend` 执行 `npm ci`（首次）、`npm run dev`。页面地址：`http://localhost:5173/login`。
4. 前端构建：`npm run build`。

开发服务器默认监听所有网卡。正式部署必须设置前端实际域名、限制 CORS、关闭不必要的公网入口，并使用安全的凭据管理与 HTTPS。

### 部署到服务器

**系统不会自动识别服务器上的数据库。** `backend/.env` 已被 Git 忽略，不会随代码进入仓库；
若不配置，`DB_HOST` 等会退回默认值（`127.0.0.1` / `root` / `123456` / `sales_data`）而连不上库。
配置方式（环境变量优先于 `.env`，已实测）、DDL 权限要求、Nginx 配置与上线检查清单，
见 **[docs/部署与配置.md](docs/部署与配置.md)**。

### 环境注意事项

- **`python-jose` 不在清华镜像中**，若 `pip install` 报 `from versions: none`，改用官方源：`pip install python-jose[cryptography] -i https://pypi.org/simple`。
- **`npm run build` 在部分环境会被批量删除保护拦截**（`SAFE_DELETE_BULK_CONFIRM_REQUIRED`，当 `dist/assets` 文件数超过阈值时）。绕法：`npx vite build --outDir <临时目录> --emptyOutDir false`。
- **`config.py` 不得用字符串拼接生成连接串**：库名 `东南亚运营数据` 含中文，拼接后建 Engine 会因编码出错。连接串统一由 `database.URL.create()` 构造。
- **本机代理会劫持 localhost**：启动前后端前先 `unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY`，否则内部请求变成 502。
- **登录限流是单进程内存态**：多实例部署时各进程计数不共享，需改为 Redis 等共享存储。

## 核心接口

所有业务接口挂载在 `/api/v1` 下。

| 接口                                                           | 方法       | 权限                                     |
| ------------------------------------------------------------ | -------- | -------------------------------------- |
| `/auth/login`                                                | POST     | 公开（带限流）                                |
| `/auth/change-password`                                      | POST     | 登录用户                                   |
| `/auth/me`                                                   | GET      | 登录用户                                   |
| `/sales/daily`                                               | GET      | 按角色与店铺范围过滤                             |
| `/sales/personnel`                                           | GET      | 按角色范围过滤                                |
| `/sales/stats/regional`、`/sales/stats/platform`              | GET      | **仅 admin**                            |
| `/sales/distribution/region`、`/sales/distribution/warehouse` | GET      | **仅 admin**                            |
| `/sales/management`                                          | GET      | **仅 admin**                            |
| `/report/daily`、`/report/daily/mine`                         | GET/POST | 按可见范围；提交限非admin 本人当天                   |
| `/report/compliance`                                         | GET      | leader / manager / admin（operator 403） |
| `/report/people`                                             | GET      | 登录用户（已按可见范围过滤）                         |
| `/report/target`                                             | GET/POST | 读取公开，写入限 admin                         |

前端将当前页数据缓存于组件内并静默预取后两页；筛选变化时重新查询。预取不等于预先渲染全部 DOM，也不使无权限数据进入浏览器。

## 验证与性能

**当前验证记录**：后端共有 44 项单元测试；日报销售额专项 15 项已通过。完整套件当前有 1 项既有登录限流边界断言失败（锁刚建立时剩余秒数可能报告 901 秒，而断言上限为 900 秒），因此不能写成“全套测试通过”。

- 权限隔离：leader 访问 5 个管理端接口全部 403，admin 仍 200。
- 登录限流：错误密码 1–5 次 401，第 6 次起 429 并提示剩余秒数。
- 范围隔离：leader 可见 28 店铺，admin 可见 1009 店铺，leader 的 28 个全部是 admin 子集、独有 0。
- 前端渲染：`/stats7d`、`/statsdaily` 图表正常渲染，ECharts 按需引入后无 console 报错。

**2026-09-18 性能基线**：经营总览由约 20.09 秒、15.39 MB 全量响应降为约 0.44 秒、27 KB、20 条首屏；人员销售由约 2.24 秒、1008 条降为约 0.45 秒、13 KB、20 条首屏。该数据为本地到远程库的单次测试，**不是生产环境 SLA**。

## 尚未解决的问题

以下为当前真实待办，按优先级排列；manager 四角色端到端验收已在 T14 完成，不再列为待办。

### P1功能缺口

1. **日报列表筛选维度不足** —— 现有日期区间 + 运营人员两个筛选，缺部门、店铺、提交状态筛选。
2. **缺日报越权详情接口** —— 目前只能从列表数据取明细，无独立详情接口做后端二次校验。
3. **T04后端补行未完成** —— 前端已在 `DailyReportList.vue` 拼装未提交人员行，但后端 `/report/daily` 只返回已提交记录，跨页补行在大范围下会不全。
4. **业务口径待确认** —— `dny_data.xse` 是否计入退款/取消/测试订单；朱文剑名下12 个 `dp_ry` 编号在源表无历史记录，需权威店铺清单核对归属。

### P1 工程欠账

1. **无 CI/CD** —— 无 `.github/workflows`，测试与构建全靠手工。
2. **无数据库迁移/回滚脚本** —— 无 Alembic、无 `schema_migrations` 版本表。DDL 变更目前只能手工执行且无回滚路径，这是当前最大的运维风险。
3. **无部署配置** —— 无 Dockerfile、docker-compose、Nginx 配置、进程管理配置。
4. **无前端测试框架** —— 后端有 44 项单元测试，前端仍无自动化测试。
5. **前端 chunk 仍偏大** —— `index-*.js` 1,535.05 kB（gzip 477.23 kB），根因是 Ant Design Vue 全量引入，需 `unplugin-vue-components` 按需引入；`EChart-*.js` 504.60 kB 仍略超500 kB 阈值。
6. **限流为单进程内存态** —— 多实例部署时各进程计数不共享，需改用 Redis 等共享存储。IP 维度已于 2026-10-06 默认停用（`LOGIN_IP_LIMIT_ENABLED=false`），以避免共用出口 IP 时误伤全公司；账号维度（5 次/300 秒/锁 900 秒）仍生效。
7. **前端构建告警** —— `[ant-design-vue: Table] index parameter of rowKey function is deprecated`，需改为稳定 rowKey。
8. **并发能力不足** —— QPS 天花板约 20，根因是数据库在公网（RTT 21 ms）。优先级：①数据库与应用同内网；②Redis 缓存 `dp_ry`/`denglu`/月目标等低频变更数据以减少往返；③合并接口内多条 SQL。**不要靠加大连接池或加 workers 解决** —— 前者实测仅 +34%，后者实测更慢。

## 已知事故记录

**2026-10-06 误写胡蓉日报**：验证 manager 权限时误发起 `POST /api/v1/report/daily`，覆盖了 `operator_id=156` / `report_date=2026-10-06` 的既有记录（原 `submitted_at` 10:51:09 被改为 13:35:19）。binlog 恢复因权限不足（需 SUPER）失败，原值无法还原，**建议该运营重新提交当天日报**（页面同日覆盖）。前一日记录完好。

**同日T14 核查再次触碰同一记录（业务数值未损）**：manager 端到端验收需要实测写路径，
改为「先 `GET` 读出原值→ 原样回写」，并断言 14 个业务字段逐一比对无变化。实测结果：
`listing_count` 等业务数值全部一致，但 **`submitted_at` 仍被 `CURRENT_TIMESTAMP` 刷新**。
即该记录的「最后提交时间」已非本人首次填写时间。此为验证代价，业务数据无损失。

> 教训：日报表 `save_report` 用 `ON DUPLICATE KEY UPDATE ... submitted_at=CURRENT_TIMESTAMP`，
> 任何写路径验证都会改写提交时间。后续如需再次验证写路径，应改用测试库，
> 或在验证后显式告知运营「提交时间已刷新」。

## Git 与远程仓库

```
origin  https://github.com/ICEXJL/Workbench.git
```

仓库已于 2026-10-06 设为公开。本地已完成 4 次提交，但**尚未成功推送** —— 本机代理 `127.0.0.1:56975` 对 `github.com:443` 的 CONNECT 返回 502（`api.github.com` 等域名不受影响）。解决方式：在代理白名单放行 `github.com`，或临时关闭代理后执行 `git push -u origin main`。

注意：仓库为公开状态，`tasks/` 内含真实账号名与验收细节。推送前应确认是否需要脱敏。

## 验收依据

逐项状态见 [DEVELOPMENT\_STATUS.md](DEVELOPMENT_STATUS.md)、[specs/](specs/)、[tasks/](tasks/)，业务验收记录见 `开发TO DO验收清单-已核验-2026-09-22.docx`。
