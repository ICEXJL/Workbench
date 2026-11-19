# Specification Index

本索引记录项目规格的入口和状态。`draft` 表示规格尚待业务评审，不表示已经批准，也不表示对应能力已经实现。

| ID | Spec | 状态 | 相关模块 |
| --- | --- | --- | --- |
| SPEC-001 | 角色、组织层级与数据可见范围 | draft | `backend/services/sales_service.py`、`report_service.py`、`org_hierarchy`、`dp_ry` |
| SPEC-002 | 认证、首次改密与 Token 生命周期 | draft | `backend/routers/auth.py`、`denglu`、`frontend/src/stores/auth.js` |
| SPEC-003 | 东南亚销售查询、分页与统计口径 | draft | `/api/v1/sales/*`、`dny_data`、`dp_ry`、销售页面；人员销售取基准日当天及前 6 天，按运营汇总账号数据并降序排名，底部整体汇总当前权限和筛选范围 |
| SPEC-004 | 运营日报字段、周度规则与同日覆盖 | draft | `/api/v1/report/daily*`、`daily_report`、日报页面 |
| SPEC-005 | 月度目标与完成率 | draft | `/api/v1/report/target`、`target_monthly`、日报/目标页面 |
| SPEC-006 | 合规概览与异常指标 | draft | `/api/v1/report/compliance`、日报列表页面 |
| SPEC-007 | API 错误、越权和审计契约 | draft | `routers/`、`operation_security_audit`、请求拦截器 |
| SPEC-008 | 数据库结构、启动检查与迁移/回滚 | draft | `backend/database.py`、业务 MySQL 表 |
| SPEC-009 | 运行、部署、健康检查与发布验收 | draft | Vite、Uvicorn、Nginx/宝塔、README |
| SPEC-010 | 测试分层与四角色端到端验收 | draft | `tests/`、API 冒烟、浏览器验收 |
| SPEC-011 | 日报销售额自动取数（dny_data，源数据必须覆盖日报日） | implemented | `/api/v1/report/daily*`、`dny_data`、`dp_ry`、`daily_report`、日报页面、月度目标完成率 |
| SPEC-012 | 经营数据工作台领域规格（销售查询与运营日报） | implemented | 全部 16 个业务接口、`daily_report`、`operator`、`org_hierarchy`、`dp_ry`、`target_monthly`、`operation_security_audit` |

## 状态约定

- `draft`：已识别范围，但尚未获得完整业务/技术批准。
- `approved`：业务口径、接口、权限和验收标准已确认，可作为实现依据。
- `implemented`：已按批准 Spec 实现并通过对应测试；不能只因代码存在就标记。
- `deprecated`：已被新 Spec 替代，保留替代关系和迁移说明。

所有正式 Spec 应包含：目标与非目标、角色矩阵、数据口径、接口/字段、异常、数据库影响、Acceptance Criteria、测试和未确认项。历史 PRD、原型和验收清单应在 Spec 中作为来源引用，而不是自动成为实现契约。

- SPEC-013：运营日报注意事项（implemented），见 [规格](SPEC-013-report-attention-notes.md)，覆盖字段、权限、条件展示及迁移回滚。
