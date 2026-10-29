# T15 · 夏伊标准账号合并后缀身份可见范围（2026-10-08）

## 目标

让标准登录账号 `xiayi` 继承其 `_N` 主管身份与 `_W` 组长身份对应的可见运营范围，同时不改变陈丽莎的主管权限。

## 设计决定

- 不创建重复登录账号，不改密码，不写数据库。
- 不需要修改 `org_hierarchy`：该表已有成员关系，武汉 8 位有效运营通过 `_W` 身份（`leader_id=50`）关联；成员的主管关系仍为陈丽莎（`manager_id=187`）。
- 后端以标准 `operator` 记录为主体，通过同名下划线后缀身份解析别名；汇总后缀身份对应的主管关系与组长关系，并排除后缀身份自身，避免重复展示。
- 日报、人员和销售范围继续由后端执行。销售数据页仍限定 `dp_ry.qy='东南亚'`，因此非东南亚店铺不会因为扩大身份范围而显示在东南亚销售页。

## 实现

- `backend/services/permission_scope.py`：统一定义 manager 后缀身份匹配 SQL。
- `backend/services/report_service.py`：日报、合规、可见人员使用合并后的 operator ID 范围。
- `backend/services/sales_service.py`：人员销售与店铺销售复用后缀身份可见范围；对 `dp_ry.yy` 的“代维护”后缀统一归一化后再匹配标准人员名称。
- `tests/test_rbac_permissions.py`：覆盖 manager 的后缀组长关系继承及两类服务的范围一致性。
- `specs/SPEC-012-经营数据工作台领域规格.md`：补充范围业务规则和验收条件。

## 只读数据库核验

- 标准账号映射 `operator.id=48`；同名后缀身份为 `id=49`（manager）和 `id=50`（leader）。
- `_W` 组长关系包含 8 位有效运营，8 人全部包含在 `xiayi` 的 `visible_operator_ids` 和日报人员范围内；后缀身份 `49/50` 不作为重复运营返回。
- `xiayi` 当前合并可见 24 个有效 ID（包括本人以及其原有主管关系成员）。
- 陈丽莎 `operator.id=187` 的当前可见集合为 61 个 ID，与原 `manager_id=187` 关系加本人完全一致。
- 人员销售接口实际返回 21 个东南亚范围选项；8 位 `_W` 运营中 6 位有 `qy='东南亚'` 店铺并出现在该范围，另 2 位只有 MY/TH 映射，因此受既有区域过滤而不显示于东南亚销售页；日报权限不受该区域过滤影响。
- `dp_ry` 中 `Shopee-PH173(五仓)`、`Shopee-PH468(五仓)`、`TikTok-3PF-HY-02(五仓)` 的 `yy` 为“夏伊代维护”，`zm` 为“夏伊_N”；销售范围查询已通过 `REPLACE(TRIM(p.yy),'代维护','')` 兼容，不修改原始店铺归属。
- 权限范围和人员映射核对均为 `SELECT`，没有改动 `operator`、`org_hierarchy` 或 `dp_ry` 的业务数据。重启服务时执行了已有的启动 schema 初始化；初始化前确认所需列和审计表均已存在。

## 验证

- 本地 HTTP 只读验证：`GET /api/v1/report/people` 用标准 `xiayi` 身份返回 200、24 人，武汉 8 人全部在内；用陈丽莎身份返回 200、61 人；`GET /api/v1/sales/personnel` 返回 200、21 人员选项。
- `python -m unittest discover -s tests`：46 项中 45 项通过；唯一失败是既有登录限流倒计时边界测试（实际 901 秒、预期不超过 900 秒），与本任务无关。
- `python -m unittest discover -s tests -p 'test_rbac_permissions.py' -v`：权限专项 20/20 通过。
- `python -m unittest discover -s tests -p 'test_rbac_permissions.py' -v`：代维护兼容后权限专项 21/21 通过；真实 `xiayi` 人员销售查询返回上述店铺归属行，经营总览返回三家店铺。
- 后端 `python -m compileall -q .`：通过。
- 前端 `npm run build`：通过；Vite 提示主包约 1.5 MB、图表包约 505 kB，属于既有体积优化项。
- 本地服务：后端 `http://localhost:8000/health` 返回 `{"status":"ok"}`，前端 `http://localhost:5173/login` 返回 HTTP 200。
