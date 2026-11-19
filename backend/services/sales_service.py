"""业务查询层：把原 Streamlit 脚本里的全部 SQL 原样迁移到这里。

前端只调 /backend/backend 的接口，不接触任何 SQL。
"""
import bcrypt

from database import run_execute, run_query
from services.permission_scope import (
    MANAGER_ALIAS_IDS_SQL,
    MANAGER_ALIAS_NAMES_SQL,
    MANAGER_IDENTITY_IDS_SQL,
)

ADMIN_USERS = {"boss", "boos", "xiangjinglv", "lichuxiong"}


def resolve_identity(username: str) -> dict | None:
    rows = run_query(
        """SELECT d.username, o.id AS operator_id, o.real_name, o.role, o.status,
                  d.must_change_password,
                  COALESCE(o.department, MAX(p.bm), MAX(p.fgs)) AS resolved_department
           FROM denglu d
           JOIN operator o ON o.id=d.operator_id
           LEFT JOIN dp_ry p ON p.yy COLLATE utf8mb4_0900_ai_ci=o.real_name
           WHERE d.username=:username
           GROUP BY d.username,o.id,o.real_name,o.department,o.role,o.status
           LIMIT 1""",
        {"username": username},
    )
    if not rows or not rows[0].get("operator_id") or not rows[0].get("status"):
        return None
    row = rows[0]
    return {
        "username": username,
        "userId": str(row["operator_id"]),
        "realName": row["real_name"],
        "role": row["role"],
        "department": row.get("resolved_department"),
        "mustChangePassword": bool(row.get("must_change_password")),
    }


# ==================== 登录 ====================
def find_user(username: str, password: str) -> dict | None:
    """查询账号并使用 bcrypt 哈希验证密码。"""
    rows = run_query(
        "SELECT * FROM denglu WHERE username = :username LIMIT 1",
        {"username": username},
    )
    return rows[0] if rows and _password_matches(rows[0], password) else None


def _password_matches(user: dict, password: str) -> bool:
    password_hash = user.get("password_hash")
    if not password_hash:
        return False
    try:
        hash_bytes = (
            password_hash
            if isinstance(password_hash, bytes)
            else str(password_hash).encode("utf-8")
        )
        return bcrypt.checkpw(password.encode("utf-8"), hash_bytes)
    except (ValueError, TypeError):
        return False


def change_password(username: str, current_password: str, new_password: str) -> bool:
    rows = run_query(
        "SELECT username,password,password_hash "
        "FROM denglu WHERE username=:username LIMIT 1",
        {"username": username},
    )
    if not rows or not _password_matches(rows[0], current_password):
        return False

    password_hash = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    return run_execute(
        "UPDATE denglu SET password_hash=:password_hash, password='', must_change_password=0 "
        "WHERE username=:username",
        {"username": username, "password_hash": password_hash},
    ) > 0


def _scope_clause(user: dict, alias: str = "p") -> tuple[str, dict]:
    role, operator_id = user["role"], int(user["userId"])
    normalized_owner = f"REPLACE(TRIM({alias}.yy), '代维护', '')"
    own_names = """SELECT canonical.real_name
        FROM operator canonical
        WHERE canonical.id=:scope_id
        UNION
        SELECT legacy.real_name
        FROM operator legacy
        JOIN operator canonical ON canonical.id=:scope_id
        WHERE legacy.status=0
          AND legacy.real_name LIKE CONCAT(canonical.real_name, '\\_%')"""
    if role == "admin":
        return "", {}
    if role == "manager":
        own_names = f"""{own_names}
            UNION
            {MANAGER_ALIAS_NAMES_SQL}"""
        return f""" AND {normalized_owner} IN (
            SELECT o.real_name
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE (h.manager_id IN ({MANAGER_IDENTITY_IDS_SQL})
                   OR h.leader_id IN ({MANAGER_ALIAS_IDS_SQL}))
              AND h.operator_id NOT IN ({MANAGER_ALIAS_IDS_SQL})
              AND o.status=1
            UNION
            {own_names}
        )""", {"scope_id": operator_id}
    if role == "leader":
        return f""" AND {normalized_owner} IN (
            SELECT o.real_name
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE h.leader_id=:scope_id AND o.status=1
            UNION
            {own_names}
        )""", {"scope_id": operator_id}
    return f" AND {normalized_owner} IN ({own_names})", {"scope_id": operator_id}


# ==================== 每日销售 ====================
# 注意：2026-10-16 起不再按 dp_ry.qy 过滤区域。
# dp_ry 实际有 5 个区域（东南亚1058/ TH 230 / MY 189 / BR 6 / 墨西哥4 店铺），
# 原先硬编码 qy='东南亚' 会导致 MY/TH 等区的组员（如罗莉娅的覃美娟、马欢）查不到数据。
# 现改为不限区域，可见范围完全由 _scope_clause 的权限逻辑决定。
def daily_sales_sort_clause(sort_by: str, sort_order: str) -> str:
    columns = {
        "xse": "CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4))",
        "dds": "CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4))",
    }
    metric = sort_by if sort_by in columns else "xse"
    primary = columns[metric]
    secondary = columns["dds"] if metric == "xse" else columns["xse"]
    direction = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    return f"{primary} {direction}, {secondary} DESC, d.dpbh ASC"


def daily_sales_range_sort_clause(sort_by: str, sort_order: str) -> str:
    columns = {"xse": "xse", "dds": "dds"}
    metric = sort_by if sort_by in columns else "xse"
    secondary = "dds" if metric == "xse" else "xse"
    direction = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    return f"{metric} {direction}, {secondary} DESC, dpbh ASC"


def get_daily_sales(
    user: dict,
    target_date: str,
    store: str | None,
    page: int,
    page_size: int,
    sort_by: str = "xse",
    sort_order: str = "desc",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    scope_sql, scope_params = _scope_clause(user)
    store_sql = " AND d.dpbh=:store" if store else ""
    visibility = f"EXISTS (SELECT 1 FROM dp_ry p WHERE p.dpbh=d.dpbh{scope_sql})"
    range_start = start_date or target_date
    range_end = end_date or target_date
    range_sql = "d.rq BETWEEN :start_date AND :end_date"
    params = {
        **scope_params,
        "target_date": target_date,
        "start_date": range_start,
        "end_date": range_end,
        "store": store,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    is_range = range_start != range_end
    # 运营（dp_ry.yy）与运营上级（dp_ry.zm）：visibility 已保证 dpbh 在 dp_ry 中存在，
    # 用标量子查询取一条，避免 JOIN 一对多放大行数。同一店铺多归属时取字典序最小的一条。
    owner_cols = ("(SELECT MIN(p.yy) FROM dp_ry p WHERE p.dpbh=d.dpbh) yy,"
                  "(SELECT MIN(p.zm) FROM dp_ry p WHERE p.dpbh=d.dpbh) zm")
    if is_range:
        order_clause = daily_sales_range_sort_clause(sort_by, sort_order)
        items_sql = f"""
            SELECT d.dpbh,
                   {owner_cols},
                   COALESCE(SUM(CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4))), 0) dds,
                   ROUND(COALESCE(SUM(CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4))), 0), 2) xse,
                   GROUP_CONCAT(DISTINCT NULLIF(TRIM(d.ckh), '') ORDER BY d.ckh SEPARATOR '、') ckh,
                   :start_date period_start,
                   :end_date period_end
            FROM dny_data d
            WHERE {range_sql} AND {visibility}{store_sql}
            GROUP BY d.dpbh
            ORDER BY {order_clause}
            LIMIT :limit OFFSET :offset
        """
        count_sql = f"SELECT COUNT(DISTINCT d.dpbh) total FROM dny_data d WHERE {range_sql} AND {visibility}{store_sql}"
    else:
        order_clause = daily_sales_sort_clause(sort_by, sort_order)
        items_sql = f"SELECT d.dpbh,{owner_cols},d.dds,d.xse,d.ckh,d.rq FROM dny_data d WHERE {range_sql} AND {visibility}{store_sql} ORDER BY {order_clause} LIMIT :limit OFFSET :offset"
        count_sql = f"SELECT COUNT(*) total FROM dny_data d WHERE {range_sql} AND {visibility}{store_sql}"
    items = run_query(items_sql, params)
    total = run_query(count_sql, params)[0]["total"]
    summary = run_query(
        f"SELECT COALESCE(SUM(CAST(NULLIF(TRIM(d.dds), '') AS DECIMAL(20,4))),0) orders,ROUND(COALESCE(SUM(CAST(NULLIF(TRIM(d.xse), '') AS DECIMAL(20,4))),0),2) sales,COUNT(DISTINCT d.dpbh) stores FROM dny_data d WHERE {range_sql} AND {visibility}{store_sql}",
        params,
    )[0]
    stores = run_query(
        f"SELECT DISTINCT d.dpbh FROM dny_data d WHERE {range_sql} AND {visibility} ORDER BY d.dpbh",
        params,
    )
    summary["aov"] = round(float(summary["sales"] or 0) / float(summary["orders"] or 1), 2) if summary["orders"] else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": summary,
        "stores": [row["dpbh"] for row in stores],
        "period_start": range_start,
        "period_end": range_end,
    }


# ==================== 店铺人员销售情况表 ====================
def get_personnel_sales(user: dict, cxrq_str: str, department: str | None, group: str | None, operator: str | None, page: int, page_size: int) -> dict:
    scope_sql, scope_params = _scope_clause(user, "p")
    filters = scope_sql
    params = {**scope_params, "cxrq": cxrq_str, "limit": page_size, "offset": (page - 1) * page_size}
    for key, column, value in (("department", "p.jc", department), ("group_name", "p.zm", group), ("operator_name", "p.yy", operator)):
        if value:
            filters += f" AND {column}=:{key}"
            params[key] = value

    day_fields = []
    for index, days_ago in enumerate(range(6, -1, -1), start=1):
        day_fields.extend([
            f"SUM(CASE WHEN d.rq=DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL {days_ago} DAY,'%Y-%m-%d') THEN d.dds ELSE 0 END) dd{index}",
            f"ROUND(SUM(CASE WHEN d.rq=DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL {days_ago} DAY,'%Y-%m-%d') THEN d.xse ELSE 0 END),2) xs{index}",
        ])

    platform_expression = """CASE WHEN p.dpbh LIKE 'shopee-ph%' THEN 'shopee-ph' WHEN p.dpbh LIKE 'shopee-3pf%' THEN 'shopee-3pf'
      WHEN p.dpbh LIKE 'lazada-ph%' THEN 'lazada-ph' WHEN p.dpbh LIKE 'lazada-3pf%' THEN 'lazada-3pf'
      WHEN p.dpbh LIKE 'tiktok-ph%' THEN 'tiktok-ph' WHEN p.dpbh LIKE 'tiktok-3pf%' THEN 'tiktok-3pf' END"""
    from_sql = """FROM dp_ry p JOIN dny_data d
      ON d.dpbh=p.dpbh
      AND d.rq BETWEEN DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 6 DAY,'%Y-%m-%d')
      AND DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 0 DAY,'%Y-%m-%d')"""
    where_sql = f"WHERE p.yy IS NOT NULL AND TRIM(p.yy)<>''{filters}"
    select_sql = f"""SELECT
      GROUP_CONCAT(DISTINCT p.jc ORDER BY p.jc SEPARATOR '、') jc,
      GROUP_CONCAT(DISTINCT p.zm ORDER BY p.zm SEPARATOR '、') zm,
      p.yy,MIN(p.rzsj) rzsj,
      GROUP_CONCAT(DISTINCT p.dpbh ORDER BY p.dpbh SEPARATOR '、') dpbh,
      GROUP_CONCAT(DISTINCT {platform_expression} ORDER BY {platform_expression} SEPARATOR '、') fl,
      ROUND(COALESCE(SUM(d.xse),0) / 7, 2) avg_sales,
      {','.join(day_fields)},
      COALESCE(SUM(d.dds),0) total_orders,ROUND(COALESCE(SUM(d.xse),0),2) total_sales
      {from_sql} {where_sql} GROUP BY p.yy"""
    total = run_query(f"SELECT COUNT(DISTINCT p.yy) total {from_sql} {where_sql}", params)[0]["total"]
    items = run_query(f"{select_sql} ORDER BY total_sales DESC,yy LIMIT :limit OFFSET :offset", params)
    summary_sql = f"""SELECT COALESCE(SUM(operator_orders),0) total_orders,
      ROUND(COALESCE(SUM(operator_sales),0),2) total_sales
      FROM (SELECT p.yy,SUM(d.dds) operator_orders,SUM(d.xse) operator_sales
      {from_sql} {where_sql} GROUP BY p.yy) operator_totals"""
    summary_params = {key: value for key, value in params.items() if key not in ("limit", "offset")}
    summary_rows = run_query(summary_sql, summary_params)
    options = run_query(f"SELECT DISTINCT p.jc,p.zm,p.yy FROM dp_ry p WHERE p.yy IS NOT NULL AND TRIM(p.yy)<>''{scope_sql} ORDER BY p.jc,p.zm,p.yy", scope_params)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": summary_rows[0] if summary_rows else {"total_orders": 0, "total_sales": 0},
        "options": options,
    }


def get_personnel_store_sales(user: dict, operator_name: str, target_date: str) -> dict:
    """Return all stores owned by an operator for one day, including zero-sales stores."""
    scope_sql, scope_params = _scope_clause(user, "p")
    params = {**scope_params, "operator_name": operator_name, "target_date": target_date}
    sql = f"""
      SELECT p.dpbh,
             COALESCE(SUM(d.dds), 0) AS total_orders,
             ROUND(COALESCE(SUM(d.xse), 0), 2) AS total_sales
      FROM dp_ry p
      LEFT JOIN dny_data d ON d.dpbh=p.dpbh AND d.rq=:target_date
      WHERE p.yy=:operator_name AND p.yy IS NOT NULL AND TRIM(p.yy)<>''{scope_sql}
      GROUP BY p.dpbh
      ORDER BY total_sales DESC, total_orders DESC, p.dpbh ASC
    """
    return {"operator": operator_name, "date": target_date, "items": run_query(sql, params)}


# ==================== 7天数据统计：地区 ====================
def get_regional_stats() -> list[dict]:
    sql_query = """
    SELECT
        d.rq,
        SUM(CASE WHEN t.fgs = '南昌部' THEN d.dds ELSE 0 END) AS 南昌部_订单量,
        ROUND(SUM(CASE WHEN t.fgs = '南昌部' THEN d.xse ELSE 0 END), 2) AS 南昌部_销售额,
        SUM(CASE WHEN t.fgs = '武汉部' THEN d.dds ELSE 0 END) AS 武汉部_订单量,
        ROUND(SUM(CASE WHEN t.fgs = '武汉部' THEN d.xse ELSE 0 END), 2) AS 武汉部_销售额,
        SUM(CASE WHEN t.fgs = '深圳部' THEN d.dds ELSE 0 END) AS 深圳部_订单量,
        ROUND(SUM(CASE WHEN t.fgs = '深圳部' THEN d.xse ELSE 0 END), 2) AS 深圳部_销售额
    FROM dny_data d
    INNER JOIN (
        SELECT DISTINCT dpbh, fgs
        FROM dp_ry
        WHERE fgs IN ('武汉部', '南昌部', '深圳部')
    ) t ON d.dpbh = t.dpbh
    WHERE d.rq >= CURDATE() - INTERVAL 7 DAY
      AND d.rq <= CURDATE()
    GROUP BY d.rq
    ORDER BY d.rq;
    """
    return run_query(sql_query)


# ==================== 7天数据统计：平台 ====================
def get_platform_stats() -> list[dict]:
    sql_query = """
    SELECT
        rq,
        SUM(CASE WHEN LOWER(prefix) = 'lazada' THEN dds ELSE 0 END) AS Lazada_订单量,
        ROUND(SUM(CASE WHEN LOWER(prefix) = 'lazada' THEN xse ELSE 0 END), 2) AS Lazada_销售额,
        SUM(CASE WHEN LOWER(prefix) = 'shopee' THEN dds ELSE 0 END) AS Shopee_订单量,
        ROUND(SUM(CASE WHEN LOWER(prefix) = 'shopee' THEN xse ELSE 0 END), 2) AS Shopee_销售额,
        SUM(CASE WHEN LOWER(prefix) = 'tiktok' THEN dds ELSE 0 END) AS TK_订单量,
        ROUND(SUM(CASE WHEN LOWER(prefix) = 'tiktok' THEN xse ELSE 0 END), 2) AS TK_销售额
    FROM (
        SELECT
            rq,
            SUBSTRING_INDEX(dpbh, '-', 1) AS prefix,
            SUM(dds) AS dds,
            SUM(xse) AS xse
        FROM dny_data
        WHERE rq >= CURDATE() - INTERVAL 7 DAY
          AND rq <= CURDATE()
        GROUP BY rq, SUBSTRING_INDEX(dpbh, '-', 1)
    ) t
    GROUP BY rq
    ORDER BY rq;
    """
    return run_query(sql_query)


# ==================== 每日分布：区域 ====================
def get_t1_region_distribution(target_date: str) -> list[dict]:
    sql_query = """
    SELECT
        IFNULL(t2.fgs, '总计') AS 区域,
        SUM(t1.dds) AS 订单量,
        ROUND(SUM(t1.xse), 2) AS 销售额
    FROM dny_data t1
    JOIN dp_ry t2 ON t1.dpbh = t2.dpbh
    WHERE t1.rq = :target_dt
    GROUP BY t2.fgs WITH ROLLUP;
    """
    return run_query(sql_query, {"target_dt": target_date})


# ==================== 每日分布：仓库 ====================
def get_t1_warehouse_distribution(target_date: str) -> list[dict]:
    sql_query = """
    SELECT
        IFNULL(t2.fhck, '总计') AS 仓库,
        SUM(t1.dds) AS 订单量,
        ROUND(SUM(t1.xse), 2) AS 销售额
    FROM dny_data t1
    JOIN dp_ry t2 ON t1.dpbh = t2.dpbh
    WHERE t1.rq = :target_dt
    GROUP BY t2.fhck WITH ROLLUP;
    """
    return run_query(sql_query, {"target_dt": target_date})


# ==================== 人员管理 ====================
def get_personnel_management() -> list[dict]:
    return run_query("SELECT name, roles, apt FROM name_roles_apt")

