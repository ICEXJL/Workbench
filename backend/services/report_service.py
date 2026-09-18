from database import run_execute, run_query


def visible_operator_ids(user: dict) -> list[int]:
    operator_id, role = int(user["userId"]), user["role"]
    if role == "admin":
        rows = run_query("SELECT id FROM operator WHERE status=1")
    elif role == "manager":
        rows = run_query("SELECT DISTINCT operator_id AS id FROM org_hierarchy WHERE manager_id=:id UNION SELECT :id", {"id": operator_id})
    elif role == "leader":
        rows = run_query("SELECT DISTINCT operator_id AS id FROM org_hierarchy WHERE leader_id=:id UNION SELECT :id", {"id": operator_id})
    else:
        rows = [{"id": operator_id}]
    return sorted({int(row["id"]) for row in rows})


def visible_people(user: dict) -> list[dict]:
    ids = visible_operator_ids(user)
    bind = {f"p{i}": value for i, value in enumerate(ids)}
    placeholders = ",".join(f":p{i}" for i in range(len(ids)))
    return run_query(f"SELECT id,real_name,department,role FROM operator WHERE id IN ({placeholders}) AND status=1 ORDER BY real_name", bind)


def get_target(operator_id: int, target_month: str) -> dict | None:
    rows = run_query("SELECT operator_id,department,month target_month,sales_target,listing_target,status,updated_at FROM target_monthly WHERE operator_id=:id AND month=:month", {"id": operator_id, "month": target_month})
    return rows[0] if rows else None


def save_target(payload: dict) -> None:
    run_execute("""INSERT INTO target_monthly (operator_id,department,month,sales_target,listing_target,status,updated_at)
      VALUES (:operator_id,:department,:target_month,:sales_target,:listing_target,1,NOW())
      ON DUPLICATE KEY UPDATE department=VALUES(department),sales_target=VALUES(sales_target),listing_target=VALUES(listing_target),status=1,updated_at=NOW()""", payload)


def save_report(user: dict, payload: dict) -> dict:
    data = {**payload, "operator_id": int(user["userId"])}
    run_execute("""INSERT INTO daily_report
      (operator_id,report_date,monthly_sales,actual_listings,optimized_products,weekly_late_exceed,
       violation_flag,infringement_flag,weekly_badreview_links,weekly_misship_links,review_ontime_rate,
       reverse_product_cnt,fluctuate_shop_cnt,all_issues_resolved)
      VALUES (:operator_id,:report_date,:cumulative_sales,:listing_count,:optimization_count,:weekly_delay_exceeded,
       :violation_triggered,:infringement_triggered,:weekly_bad_review_links,:weekly_wrong_damage_links,
       :stocking_audit_rate,:reverse_product_count,:volatile_store_count,:all_issues_resolved)
      ON DUPLICATE KEY UPDATE monthly_sales=VALUES(monthly_sales),actual_listings=VALUES(actual_listings),
       optimized_products=VALUES(optimized_products),weekly_late_exceed=VALUES(weekly_late_exceed),
       violation_flag=VALUES(violation_flag),infringement_flag=VALUES(infringement_flag),
       weekly_badreview_links=VALUES(weekly_badreview_links),weekly_misship_links=VALUES(weekly_misship_links),
       review_ontime_rate=VALUES(review_ontime_rate),reverse_product_cnt=VALUES(reverse_product_cnt),
       fluctuate_shop_cnt=VALUES(fluctuate_shop_cnt),all_issues_resolved=VALUES(all_issues_resolved),submitted_at=CURRENT_TIMESTAMP""", data)
    return get_report(int(user["userId"]), str(payload["report_date"]))


def get_report(operator_id: int, report_date: str) -> dict | None:
    rows = run_query("""SELECT id,operator_id,report_date,monthly_sales cumulative_sales,actual_listings listing_count,
      optimized_products optimization_count,weekly_late_exceed weekly_delay_exceeded,violation_flag violation_triggered,
      infringement_flag infringement_triggered,weekly_badreview_links weekly_bad_review_links,
      weekly_misship_links weekly_wrong_damage_links,review_ontime_rate stocking_audit_rate,
      reverse_product_cnt reverse_product_count,fluctuate_shop_cnt volatile_store_count,
      all_issues_resolved,submitted_at FROM daily_report WHERE operator_id=:id AND report_date=:day""", {"id": operator_id, "day": report_date})
    return rows[0] if rows else None


def list_reports(user: dict, start_date: str, end_date: str, operator_id: int | None = None) -> list[dict]:
    ids = visible_operator_ids(user)
    if operator_id is not None:
        ids = [operator_id] if operator_id in ids else []
    if not ids:
        return []
    bind = {f"p{i}": value for i, value in enumerate(ids)}
    placeholders = ",".join(f":p{i}" for i in range(len(ids)))
    return run_query(f"""SELECT r.id,r.operator_id,o.real_name operator_name,COALESCE(o.department,MAX(h.dept)) department,
      r.report_date,r.monthly_sales cumulative_sales,r.actual_listings listing_count,r.optimized_products optimization_count,
      r.weekly_late_exceed weekly_delay_exceeded,r.violation_flag violation_triggered,r.infringement_flag infringement_triggered,
      r.weekly_badreview_links weekly_bad_review_links,r.weekly_misship_links weekly_wrong_damage_links,
      r.review_ontime_rate stocking_audit_rate,r.reverse_product_cnt reverse_product_count,
      r.fluctuate_shop_cnt volatile_store_count,r.all_issues_resolved,r.submitted_at,t.sales_target,
      CASE WHEN t.sales_target IS NULL OR t.sales_target=0 THEN NULL ELSE ROUND(r.monthly_sales/t.sales_target*100,2) END completion_rate
      FROM daily_report r JOIN operator o ON o.id=r.operator_id
      LEFT JOIN org_hierarchy h ON h.operator_id=r.operator_id
      LEFT JOIN target_monthly t ON t.operator_id=r.operator_id AND t.month=DATE_FORMAT(r.report_date,'%Y-%m')
      WHERE r.operator_id IN ({placeholders}) AND r.report_date BETWEEN :start_date AND :end_date
      GROUP BY r.id,o.real_name,o.department,t.sales_target
      ORDER BY r.report_date DESC,o.real_name""", {**bind,"start_date":start_date,"end_date":end_date})
