import json

from database import run_execute, run_query


def _decode_shop_names(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(name).strip() for name in value if str(name).strip()]
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        decoded = str(value).replace("，", ",").replace("、", ",").split(",")
    if not isinstance(decoded, list):
        decoded = [decoded]
    return [str(name).strip() for name in decoded if str(name).strip()]


def _decode_report(row: dict) -> dict:
    row = dict(row)
    row["rising_shop_names"] = _decode_shop_names(row.get("rising_shop_names"))
    row["falling_shop_names"] = _decode_shop_names(row.get("falling_shop_names"))
    return row


def visible_operator_ids(user: dict) -> list[int]:
    operator_id, role = int(user["userId"]), user["role"]
    if role == "admin":
        rows = run_query("SELECT id FROM operator WHERE status=1")
    elif role == "manager":
        rows = run_query("""SELECT DISTINCT h.operator_id AS id
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE h.manager_id=:id AND o.status=1
            UNION SELECT :id""", {"id": operator_id})
    elif role == "leader":
        rows = run_query("""SELECT DISTINCT h.operator_id AS id
            FROM org_hierarchy h JOIN operator o ON o.id=h.operator_id
            WHERE h.leader_id=:id AND o.status=1
            UNION SELECT :id""", {"id": operator_id})
    else:
        rows = [{"id": operator_id}]
    return sorted({int(row["id"]) for row in rows})


def visible_people(user: dict) -> list[dict]:
    ids = visible_operator_ids(user)
    bind = {f"p{i}": value for i, value in enumerate(ids)}
    placeholders = ",".join(f":p{i}" for i in range(len(ids)))
    return run_query(f"""SELECT o.id,o.real_name,
        COALESCE(NULLIF(TRIM(o.department),''),NULLIF(TRIM(p.department),''),MAX(h.dept)) department,
        o.role
      FROM operator o
      LEFT JOIN (
        SELECT yy,GROUP_CONCAT(DISTINCT
          CASE WHEN INSTR(TRIM(bm),'部') > 0
            THEN CONCAT(SUBSTRING_INDEX(TRIM(bm),'部',1),'部')
            ELSE NULLIF(TRIM(bm),'')
          END ORDER BY bm SEPARATOR '、') department
        FROM dp_ry
        WHERE bm IS NOT NULL AND TRIM(bm) <> ''
        GROUP BY yy
      ) p ON p.yy COLLATE utf8mb4_0900_ai_ci=o.real_name
      LEFT JOIN org_hierarchy h ON h.operator_id=o.id
      WHERE o.id IN ({placeholders}) AND o.status=1
      GROUP BY o.id,o.real_name,o.department,p.department,o.role
      ORDER BY o.real_name""", bind)


def get_target(operator_id: int, target_month: str) -> dict | None:
    rows = run_query("SELECT operator_id,department,month target_month,sales_target,listing_target,status,updated_at FROM target_monthly WHERE operator_id=:id AND month=:month", {"id": operator_id, "month": target_month})
    return rows[0] if rows else None


def save_target(payload: dict) -> None:
    run_execute("""INSERT INTO target_monthly (operator_id,department,month,sales_target,listing_target,status,updated_at)
      VALUES (:operator_id,:department,:target_month,:sales_target,:listing_target,1,NOW())
      ON DUPLICATE KEY UPDATE department=VALUES(department),sales_target=VALUES(sales_target),listing_target=VALUES(listing_target),status=1,updated_at=NOW()""", payload)


def save_report(user: dict, payload: dict) -> dict:
    data = {**payload, "operator_id": int(user["userId"])}
    data["volatile_store_count"] = data.get("rising_shop_count", 0) + data.get("falling_shop_count", 0)
    data["rising_shop_names_json"] = json.dumps(data.get("rising_shop_names", []), ensure_ascii=False)
    data["falling_shop_names_json"] = json.dumps(data.get("falling_shop_names", []), ensure_ascii=False)
    run_execute("""INSERT INTO daily_report
      (operator_id,report_date,monthly_sales,actual_listings,optimized_products,weekly_late_exceed,
       violation_flag,infringement_flag,weekly_badreview_links,weekly_misship_links,review_ontime_rate,
       reverse_product_cnt,fluctuate_shop_cnt,rising_shop_count,rising_shop_names,
       falling_shop_count,falling_shop_names,all_issues_resolved)
      VALUES (:operator_id,:report_date,:cumulative_sales,:listing_count,:optimization_count,:weekly_delay_exceeded,
       :violation_triggered,:infringement_triggered,:weekly_bad_review_links,:weekly_wrong_damage_links,
       :stocking_audit_rate,:reverse_product_count,:volatile_store_count,:rising_shop_count,:rising_shop_names_json,
       :falling_shop_count,:falling_shop_names_json,:all_issues_resolved)
      ON DUPLICATE KEY UPDATE monthly_sales=VALUES(monthly_sales),actual_listings=VALUES(actual_listings),
       optimized_products=VALUES(optimized_products),weekly_late_exceed=VALUES(weekly_late_exceed),
       violation_flag=VALUES(violation_flag),infringement_flag=VALUES(infringement_flag),
       weekly_badreview_links=VALUES(weekly_badreview_links),weekly_misship_links=VALUES(weekly_misship_links),
       review_ontime_rate=VALUES(review_ontime_rate),reverse_product_cnt=VALUES(reverse_product_cnt),
       fluctuate_shop_cnt=VALUES(fluctuate_shop_cnt),rising_shop_count=VALUES(rising_shop_count),
       rising_shop_names=VALUES(rising_shop_names),falling_shop_count=VALUES(falling_shop_count),
       falling_shop_names=VALUES(falling_shop_names),all_issues_resolved=VALUES(all_issues_resolved),
       submitted_at=CURRENT_TIMESTAMP""", data)
    return get_report(int(user["userId"]), str(payload["report_date"]))


def get_report(operator_id: int, report_date: str) -> dict | None:
    rows = run_query("""SELECT id,operator_id,report_date,monthly_sales cumulative_sales,actual_listings listing_count,
      optimized_products optimization_count,weekly_late_exceed weekly_delay_exceeded,violation_flag violation_triggered,
      infringement_flag infringement_triggered,weekly_badreview_links weekly_bad_review_links,
      weekly_misship_links weekly_wrong_damage_links,review_ontime_rate stocking_audit_rate,
      reverse_product_cnt reverse_product_count,fluctuate_shop_cnt volatile_store_count,
      rising_shop_count,rising_shop_names,falling_shop_count,falling_shop_names,
      all_issues_resolved,submitted_at FROM daily_report WHERE operator_id=:id AND report_date=:day""", {"id": operator_id, "day": report_date})
    return _decode_report(rows[0]) if rows else None


def list_reports(user: dict, start_date: str, end_date: str, operator_id: int | None = None) -> list[dict]:
    ids = visible_operator_ids(user)
    if operator_id is not None:
        ids = [operator_id] if operator_id in ids else []
    if not ids:
        return []
    bind = {f"p{i}": value for i, value in enumerate(ids)}
    placeholders = ",".join(f":p{i}" for i in range(len(ids)))
    rows = run_query(f"""SELECT r.id,r.operator_id,o.real_name operator_name,
      COALESCE(NULLIF(TRIM(o.department),''),NULLIF(TRIM(p.department),''),MAX(h.dept)) department,
      r.report_date,r.monthly_sales cumulative_sales,r.actual_listings listing_count,r.optimized_products optimization_count,
      r.weekly_late_exceed weekly_delay_exceeded,r.violation_flag violation_triggered,r.infringement_flag infringement_triggered,
      r.weekly_badreview_links weekly_bad_review_links,r.weekly_misship_links weekly_wrong_damage_links,
      r.review_ontime_rate stocking_audit_rate,r.reverse_product_cnt reverse_product_count,
      r.fluctuate_shop_cnt volatile_store_count,r.rising_shop_count,r.rising_shop_names,
      r.falling_shop_count,r.falling_shop_names,r.all_issues_resolved,r.submitted_at,t.sales_target,
      CASE WHEN t.sales_target IS NULL OR t.sales_target=0 THEN NULL ELSE ROUND(r.monthly_sales/t.sales_target*100,2) END completion_rate
      FROM daily_report r JOIN operator o ON o.id=r.operator_id
      LEFT JOIN org_hierarchy h ON h.operator_id=r.operator_id
      LEFT JOIN (
        SELECT yy,GROUP_CONCAT(DISTINCT
          CASE WHEN INSTR(TRIM(bm),'部') > 0
            THEN CONCAT(SUBSTRING_INDEX(TRIM(bm),'部',1),'部')
            ELSE NULLIF(TRIM(bm),'')
          END ORDER BY bm SEPARATOR '、') department
        FROM dp_ry
        WHERE bm IS NOT NULL AND TRIM(bm) <> ''
        GROUP BY yy
      ) p ON p.yy COLLATE utf8mb4_0900_ai_ci=o.real_name
      LEFT JOIN target_monthly t ON t.operator_id=r.operator_id AND t.month=DATE_FORMAT(r.report_date,'%Y-%m')
      WHERE r.operator_id IN ({placeholders}) AND r.report_date BETWEEN :start_date AND :end_date
      GROUP BY r.id,o.real_name,o.department,p.department,t.sales_target
      ORDER BY r.report_date DESC,o.real_name""", {**bind,"start_date":start_date,"end_date":end_date})
    return [_decode_report(row) for row in rows]


def compliance_overview(user: dict, start_date: str, end_date: str) -> dict:
    """Return role-scoped compliance counts and names for management views."""
    ids = visible_operator_ids(user)
    if not ids:
        return {"metrics": [], "start_date": start_date, "end_date": end_date}
    bind = {f"p{i}": value for i, value in enumerate(ids)}
    placeholders = ",".join(f":p{i}" for i in range(len(ids)))
    rows = run_query(f"""SELECT o.real_name,
        MAX(r.violation_flag) violation_flag,
        MAX(r.infringement_flag) infringement_flag,
        MAX(r.weekly_late_exceed) weekly_late_exceed,
        MAX(r.weekly_badreview_links) weekly_badreview_links,
        MAX(r.weekly_misship_links) weekly_misship_links,
        GREATEST(MAX(COALESCE(r.fluctuate_shop_cnt, 0)),
          MAX(COALESCE(r.rising_shop_count, 0) + COALESCE(r.falling_shop_count, 0))) fluctuate_shop_cnt,
        MIN(r.all_issues_resolved) all_issues_resolved
      FROM daily_report r JOIN operator o ON o.id=r.operator_id
      WHERE r.operator_id IN ({placeholders}) AND r.report_date BETWEEN :start_date AND :end_date
      GROUP BY r.operator_id,o.real_name
      ORDER BY o.real_name""", {**bind, "start_date": start_date, "end_date": end_date})
    definitions = [
        ("violation", "触发违规 / 扣分", "violation_flag", "boolean", "是", "否", False),
        ("infringement", "链接侵权 / 禁售", "infringement_flag", "boolean", "是", "否", False),
        ("weekly_delay", "周延迟率 / 取消率超标", "weekly_late_exceed", "boolean", "是", "否", False),
        ("weekly_bad_review", "周商责差评 ≥3 的链接", "weekly_badreview_links", "count", "有异常", "无异常", False),
        ("weekly_wrong_damage", "周错发 / 破损 ≥3 的链接", "weekly_misship_links", "count", "有异常", "无异常", False),
        ("volatile_store", "店铺业绩波动", "fluctuate_shop_cnt", "count", "有异常", "无异常", False),
        ("issues_resolved", "当天问题是否都解决", "all_issues_resolved", "boolean", "是", "否", True),
    ]
    metrics = []
    for key, label, field, value_type, yes_label, no_label, positive in definitions:
        if value_type == "count":
            yes = sorted({row["real_name"] for row in rows if row[field] is not None and row[field] > 0})
            no = sorted({row["real_name"] for row in rows if row[field] == 0})
        else:
            yes = sorted({row["real_name"] for row in rows if row[field] == 1})
            no = sorted({row["real_name"] for row in rows if row[field] == 0})
        metrics.append({"key": key, "label": label, "yes": len(yes), "no": len(no),
                        "yes_people": yes, "no_people": no, "yes_label": yes_label,
                        "no_label": no_label, "positive": positive})
    return {"metrics": metrics, "start_date": start_date, "end_date": end_date}
