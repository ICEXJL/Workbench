from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from routers.auth import get_current_user
from schemas import schemas
from services import report_service

router = APIRouter(prefix="/report", tags=["运营日报"])


@router.get("/daily")
def daily_reports(start_date: date | None = None, end_date: date | None = None, operator_id: int | None = None, status: str | None = None, user: dict = Depends(get_current_user)):
    end_date = end_date or date.today()
    start_date = start_date or end_date.replace(day=1)
    return report_service.list_reports(user, str(start_date), str(end_date), operator_id)


@router.get("/daily/mine")
def my_daily_report(report_date: date = Query(default_factory=date.today), user: dict = Depends(get_current_user)):
    report = report_service.get_report(int(user["userId"]), str(report_date))
    target = report_service.get_target(int(user["userId"]), report_date.strftime("%Y-%m"))
    return {"report": report, "target": target, "identity": user}


@router.post("/daily")
def submit_daily_report(payload: schemas.DailyReportPayload, user: dict = Depends(get_current_user)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="管理端不提交运营日报")
    if payload.report_date != date.today():
        raise HTTPException(status_code=403, detail="仅可提交或修改当天日报")
    weekly_values = (payload.weekly_delay_exceeded, payload.weekly_bad_review_links, payload.weekly_wrong_damage_links)
    if payload.report_date.weekday() != 1 and any(value is not None for value in weekly_values):
        raise HTTPException(status_code=422, detail="周度字段仅可在周二填写")
    variation_values = (
        ("上涨", payload.rising_shop_count, payload.rising_shop_names),
        ("下滑", payload.falling_shop_count, payload.falling_shop_names),
    )
    for label, count, names in variation_values:
        if count != len(names):
            raise HTTPException(status_code=422, detail=f"{label}店铺数量与店铺名称数量不一致")

    payload_data = payload.model_dump()
    # 备货审核及时率只在周一、周三采集；其他日期保留当天已有值，首次提交按 100% 记录。
    if payload.report_date.weekday() not in (0, 2):
        existing = report_service.get_report(int(user["userId"]), str(payload.report_date))
        payload_data["stocking_audit_rate"] = existing["stocking_audit_rate"] if existing else 100
    report = report_service.save_report(user, payload_data)
    return {"message": "提交成功", "report": report, "submitted_at": report["submitted_at"]}


@router.get("/target")
def target(operator_id: int, target_month: str, user: dict = Depends(get_current_user)):
    if operator_id not in report_service.visible_operator_ids(user):
        raise HTTPException(status_code=403, detail="无权查看该运营目标")
    return report_service.get_target(operator_id, target_month)


@router.post("/target")
def save_target(payload: schemas.MonthlyTargetPayload, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理端可配置月度目标")
    report_service.save_target(payload.model_dump())
    return {"message": "目标保存成功"}


@router.get("/people")
def people(user: dict = Depends(get_current_user)):
    return report_service.visible_people(user)


@router.get("/compliance")
def compliance(start_date: date | None = None, end_date: date | None = None, user: dict = Depends(get_current_user)):
    if user["role"] == "operator":
        raise HTTPException(status_code=403, detail="运营角色无权查看合规汇总")
    end_date = end_date or date.today()
    start_date = start_date or end_date.replace(day=1)
    return report_service.compliance_overview(user, str(start_date), str(end_date))
