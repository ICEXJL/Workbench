# 跨境工作台物流查询 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有瀛江科技工作台中新增所有角色可用的跨境物流查询页面和只读后端接口。

**Architecture:** FastAPI 新增物流查询 service/router，按 `sku + warehouse` 对 5 张 `logistics_` 表分表读取并在服务层组装；Vue 新增物流查询页面，复用现有工作台布局、Axios 和路由守卫。物流查询不依赖组织范围，也不修改数据库。

**Tech Stack:** FastAPI、SQLAlchemy text 查询、MySQL、Vue 3、Vue Router、Axios、现有 CSS 工作台风格。

**Spec:** `docs/superpowers/specs/2026-10-13-logistics-workbench-design.md`

## Global Constraints

- 后端 API 使用 `/api/v1` 前缀；前端通过 `frontend/src/services/api.js` 请求。
- 物流查询对 `admin`、`manager`、`leader`、`operator` 全部开放，但只能读取数据。
- 所有物流数据条件必须包含 `sku + warehouse`；不得使用五张业务表的串联 JOIN。
- 不把数据库地址、密码、JWT 密钥、账号密码写入代码、测试、文档或日志。
- 保留工作区现有未提交修改，不使用破坏性 Git 命令。
- 完成前运行后端语法检查和 `frontend` 的 `npm run build`。

### Task 1: 后端物流查询数据服务

**Files:**
- Create: `backend/services/logistics_service.py`
- Test: `tests/test_logistics_service.py`

**Interfaces:**
- Produces `list_query_terms(query: str) -> list[str]`。
- Produces `validate_warehouse(warehouse: str | None, warehouses: list[str]) -> str | None`。
- Produces `get_warehouses() -> dict`。
- Produces `search_logistics(query: str, warehouse: str | None) -> dict`。

- [x] **Step 1: Write the failing tests**

```python
def test_list_query_terms_accepts_backslash_and_caps_at_twenty():
    from services.logistics_service import list_query_terms
    assert list_query_terms(" 1001\\1002\n1003 ") == ["1001", "1002", "1003"]
    assert len(list_query_terms("\\".join(str(i) for i in range(25)))) == 20

def test_validate_warehouse_rejects_unknown_value():
    import pytest
    from services.logistics_service import validate_warehouse
    with pytest.raises(ValueError, match="仓库"):
        validate_warehouse("UNKNOWN", ["PH-A"])

def test_search_logistics_keeps_warehouse_in_each_table_query(monkeypatch):
    from services import logistics_service
    captured = []
    def fake_query(sql, params=None):
        captured.append((sql, params or {}))
        if "FROM logistics_sku" in sql:
            return [{"sku": "1001", "warehouse": "PH-A", "product_name": "测试品"}]
        return []
    monkeypatch.setattr(logistics_service, "run_query", fake_query)
    result = logistics_service.search_logistics("1001", "PH-A")
    assert result["items"][0]["sku"] == "1001"
    logistics_sql = [sql for sql, _ in captured if "logistics_" in sql]
    assert all("warehouse" in sql and "JOIN" not in sql.upper() for sql in logistics_sql)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_logistics_service.py -q`

Expected: FAIL because `services.logistics_service` does not exist.

- [x] **Step 3: Write the minimal implementation**

Implement parameterized `IN` placeholders, warehouse validation, profile-first SKU resolution, and separate queries for the five logistics tables. Group rows in Python by `sku` and then `warehouse`; attach map rows to the matching `badge_no`. For product-name search, resolve at most 20 SKU rows from `logistics_sku` before loading detail tables. Return `{"items": [...], "query": ..., "warehouse": ...}` and never interpolate user input into SQL.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_logistics_service.py -q`

Expected: PASS.

### Task 2: FastAPI logistics routes and application registration

**Files:**
- Create: `backend/routers/logistics.py`
- Modify: `backend/main.py`
- Test: `tests/test_logistics_service.py`

**Interfaces:**
- Adds `GET /api/v1/logistics/warehouses`.
- Adds `GET /api/v1/logistics/search?q=<query>&warehouse=<warehouse>`.

- [x] **Step 1: Write failing route contract tests**

```python
def test_logistics_router_exposes_read_only_paths():
    from routers.logistics import router
    paths = {(route.path, tuple(sorted(route.methods))) for route in router.routes}
    assert ("/warehouses", ("GET",)) in paths
    assert ("/search", ("GET",)) in paths
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_logistics_service.py::test_logistics_router_exposes_read_only_paths -q`

Expected: FAIL because the router file does not exist.

- [x] **Step 3: Implement minimal routes**

Create `APIRouter(prefix="/logistics", tags=["物流查询"])`, protect both endpoints with `Depends(get_current_user)`, pass only query parameters to the service, convert unknown warehouse to HTTP 400, and convert missing/failed logistics tables to HTTP 503 with a safe Chinese message. Include the router under `/api/v1` in `backend/main.py`.

- [x] **Step 4: Run route and backend syntax tests**

Run: `python -m pytest tests/test_logistics_service.py -q` and `python -m compileall -q backend`.

Expected: PASS and exit code 0.

### Task 3: Frontend API, route, navigation section and page

**Files:**
- Create: `frontend/src/views/logistics/LogisticsSearch.vue`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/layout/MainLayout.vue`

**Interfaces:**
- `getLogisticsWarehouses()` calls `/logistics/warehouses`.
- `searchLogistics(params)` calls `/logistics/search`.
- Route name is `logistics-search`, path `/logistics/search`, title `物流查询`, with no role restriction.

- [x] **Step 1: Add the API and route contract before page implementation**

Add the two API functions and the unrestricted route. Add a first navigation section named `跨境工作台` with one item named `物流查询`; keep the existing sections and role filters unchanged.

- [x] **Step 2: Implement the page behavior**

Create a compact search view with:

```js
const state = reactive({ query: '', warehouse: '', warehouses: [], items: [], searched: false, loading: false, error: '' })
async function search() { /* call searchLogistics({ q: state.query, warehouse: state.warehouse || undefined }) */ }
```

Render the search input, warehouse select, result count, SKU result blocks, per-warehouse profile cards, one-column container cards with each container's expandable tracking, a two-month replenishment table, one combined pending/emitted ocean-shipment table, and empty/error/loading states. Escape/format display values through Vue interpolation, never `v-html` for database data. Use the existing CSS variables and responsive grid/table patterns.

- [x] **Step 3: Run frontend build**

Run: `npm run build` from `frontend`.

Expected: Vite exits 0 and creates `frontend/dist`.

### Task 4: Integration verification and documentation

**Files:**
- Modify: `docs/API_LOGISTICS.md`
- Modify: `docs/README` only if an existing index requires a link; otherwise no README change.

- [x] **Step 1: Add endpoint documentation**

Document request parameters, safe response shape, warehouse scope, the five tables used, the no-join rule, and the fact that the page is read-only.

- [x] **Step 2: Run complete verification**

Run:

```powershell
python -m pytest tests/test_logistics_service.py -q
python -m compileall -q backend
Set-Location frontend
npm run build
```

Expected: all logistics tests pass, Python syntax check exits 0, and frontend build exits 0.

- [x] **Step 3: Inspect final diff**

Run `git diff --check` and `git status --short`; verify only the planned logistics files are newly changed by this task and all pre-existing user modifications remain untouched.
