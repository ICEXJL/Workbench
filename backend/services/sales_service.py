"""业务查询层：把原 Streamlit 脚本里的全部 SQL 原样迁移到这里。

前端只调 /backend/backend 的接口，不接触任何 SQL。
"""
import bcrypt

from database import run_execute, run_query

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
        return f""" AND {alias}.yy IN (
            SELECT o.real_name
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE h.manager_id=:scope_id AND o.status=1
            UNION
            {own_names}
        )""", {"scope_id": operator_id}
    if role == "leader":
        return f""" AND {alias}.yy IN (
            SELECT o.real_name
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE h.leader_id=:scope_id AND o.status=1
            UNION
            {own_names}
        )""", {"scope_id": operator_id}
    return f" AND {alias}.yy IN ({own_names})", {"scope_id": operator_id}


# ==================== 东南亚每日销售 ====================
def get_daily_sales(user: dict, target_date: str, store: str | None, page: int, page_size: int) -> dict:
    scope_sql, scope_params = _scope_clause(user)
    store_sql = " AND d.dpbh=:store" if store else ""
    visibility = f"EXISTS (SELECT 1 FROM dp_ry p WHERE p.qy='东南亚' AND p.dpbh=d.dpbh{scope_sql})"
    params = {**scope_params, "target_date": target_date, "store": store, "limit": page_size, "offset": (page - 1) * page_size}
    items = run_query(
        f"SELECT d.dpbh,d.dds,d.xse,d.ckh,d.rq FROM dny_data d WHERE d.rq=:target_date AND {visibility}{store_sql} ORDER BY d.xse DESC,d.dpbh LIMIT :limit OFFSET :offset",
        params,
    )
    total = run_query(f"SELECT COUNT(*) total FROM dny_data d WHERE d.rq=:target_date AND {visibility}{store_sql}", params)[0]["total"]
    summary = run_query(
        f"SELECT COALESCE(SUM(d.dds),0) orders,ROUND(COALESCE(SUM(d.xse),0),2) sales,COUNT(DISTINCT d.dpbh) stores FROM dny_data d WHERE d.rq=:target_date AND {visibility}{store_sql}",
        params,
    )[0]
    stores = run_query(
        f"SELECT DISTINCT d.dpbh FROM dny_data d WHERE d.rq=:target_date AND {visibility} ORDER BY d.dpbh",
        params,
    )
    summary["aov"] = round(float(summary["sales"] or 0) / float(summary["orders"] or 1), 2) if summary["orders"] else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size, "summary": summary, "stores": [row["dpbh"] for row in stores]}


# ==================== 东南亚店铺人员销售情况表 ====================
def get_personnel_sales(user: dict, cxrq_str: str, department: str | None, group: str | None, operator: str | None, page: int, page_size: int) -> dict:
    scope_sql, scope_params = _scope_clause(user, "p")
    filters = scope_sql
    params = {**scope_params, "cxrq": cxrq_str, "limit": page_size, "offset": (page - 1) * page_size}
    for key, column, value in (("department", "p.jc", department), ("group_name", "p.zm", group), ("operator_name", "p.yy", operator)):
        if value:
            filters += f" AND {column}=:{key}"
            params[key] = value
    day_fields = []
    for index, days_ago in enumerate(range(7, 0, -1), start=1):
        day_fields.extend([
            f"SUM(CASE WHEN d.rq=DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL {days_ago} DAY,'%Y-%m-%d') THEN d.dds END) dd{index}",
            f"ROUND(SUM(CASE WHEN d.rq=DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL {days_ago} DAY,'%Y-%m-%d') THEN d.xse END),2) xs{index}",
        ])
    select_sql = f"""SELECT p.jc,p.zm,p.yy,p.rzsj,p.dpbh,
      CASE WHEN p.dpbh LIKE 'shopee-ph%' THEN 'shopee-ph' WHEN p.dpbh LIKE 'shopee-3pf%' THEN 'shopee-3pf'
           WHEN p.dpbh LIKE 'lazada-ph%' THEN 'lazada-ph' WHEN p.dpbh LIKE 'lazada-3pf%' THEN 'lazada-3pf'
           WHEN p.dpbh LIKE 'tiktok-ph%' THEN 'tiktok-ph' WHEN p.dpbh LIKE 'tiktok-3pf%' THEN 'tiktok-3pf' END fl,
      {','.join(day_fields)}
      FROM dp_ry p JOIN dny_data d ON d.dpbh=p.dpbh AND d.rq BETWEEN DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 7 DAY,'%Y-%m-%d') AND DATE_FORMAT(STR_TO_DATE(:cxrq,'%Y-%m-%d') - INTERVAL 1 DAY,'%Y-%m-%d')
      WHERE p.qy='东南亚'{filters} GROUP BY p.jc,p.zm,p.yy,p.rzsj,p.dpbh"""
    total = run_query(f"SELECT COUNT(*) total FROM ({select_sql}) rows_count", params)[0]["total"]
    items = run_query(f"{select_sql} ORDER BY zm,yy,fl,xs7 DESC LIMIT :limit OFFSET :offset", params)
    options = run_query(f"SELECT DISTINCT p.jc,p.zm,p.yy FROM dp_ry p WHERE p.qy='东南亚'{scope_sql} ORDER BY p.jc,p.zm,p.yy", scope_params)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "options": options}


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
