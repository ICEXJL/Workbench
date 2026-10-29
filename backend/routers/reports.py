from datetime import date
from decimal import Decimal
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from routers.auth import get_current_user
from schemas import schemas
from services import report_service

router = APIRouter(prefix="/report", tags=["运营日报"])
logger = logging.getLogger(__name__)


def _cumulative_sales_summary(operator_id: int, report_date: date) -> dict:
    try:
        return report_service.get_cumulative_sales(operator_id, report_date)
    except (report_service.CumulativeSalesDataError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="累计销售数据暂时无法读取，请联系管理员") from exc


def _refresh_sales_snapshot(operator_id: int, report_date: date) -> None:
    try:
        summary = report_service.get_cumulative_sales(operator_id, report_date)
        if summary.get("status") == "available" and summary.get("amount") is not None:
            report_service.update_sales_snapshot(operator_id, report_date, summary["amount"])
    except (report_service.CumulativeSalesDataError, SQLAlchemyError):
        logger.exception(
            "Daily report sales snapshot refresh failed for operator_id=%s report_date=%s",
            operator_id,
            report_date,
        )


@router.get("/daily")
def daily_reports(
    start_date: date | None = None,
    end_date: date | None = None,
    operator_id: int | None = None,
    status: str | None = None,
    department: str | None = None,
    group: str | None = None,
    user: dict = Depends(get_current_user),
):
    """日报列表。

    department / group 用于按部门、组别收窄范围，过滤在服务端完成，
    不受前端当前页影响；两者都只在用户权限范围内生效。
    """
    end_date = end_date or date.today()
    start_date = start_date or end_date.replace(day=1)
    return report_service.list_reports(
        user,
        str(start_date),
        str(end_date),
        operator_id,
        department=department,
        group=group,
    )


@router.get("/daily/mine")
def my_daily_report(
    report_date: date = Query(default_factory=date.today),
    user: dict = Depends(get_current_user),
    include_sales_summary: bool = True,
):
    report = report_service.get_report(int(user["userId"]), str(report_date))
    target = report_service.get_target(int(user["userId"]), report_date.strftime("%Y-%m"))
    if not include_sales_summary:
        return {
            "report": report,
            "target": target,
            "identity": user,
            "sales_summary": {
                "amount": report.get("cumulative_sales") if report else None,
                "currency": "USD",
                "period_start": str(report_date.replace(day=1)),
                "period_end": str(report_date),
                "data_as_of": None,
                "source": "daily_report" if report else "dny_data",
                "status": "snapshot" if report else "pending",
            },
        }
    sales_summary = _get_sales_summary(int(user["userId"]), report_date, report)
    return {"report": report, "target": target, "identity": user, "sales_summary": sales_summary}


def _get_sales_summary(operator_id: int, report_date: date, report: dict | None) -> dict:
    if report and report_date < date.today():
        return {
            "amount": report["cumulative_sales"],
            "currency": "USD",
            "period_start": str(report_date.replace(day=1)),
            "period_end": str(report_date),
            "data_as_of": None,
            "source": "daily_report",
            "status": "snapshot",
        }
    try:
        return _cumulative_sales_summary(operator_id, report_date)
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        return {
            "amount": report.get("cumulative_sales") if report else None,
            "currency": "USD",
            "period_start": str(report_date.replace(day=1)),
            "period_end": str(report_date),
            "data_as_of": None,
            "source": "daily_report" if report else "dny_data",
            "status": "source_error",
        }


@router.get("/daily/mine/sales-summary")
def my_daily_sales_summary(
    report_date: date = Query(default_factory=date.today),
    user: dict = Depends(get_current_user),
):
    operator_id = int(user["userId"])
    report = report_service.get_report(operator_id, str(report_date))
    return _get_sales_summary(operator_id, report_date, report)


@router.post("/daily")
def submit_daily_report(
    payload: schemas.DailyReportPayload,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
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
    operator_id = int(user["userId"])
    existing_report = report_service.get_report(operator_id, str(payload.report_date))
    saved_sales = existing_report.get("cumulative_sales") if existing_report else None
    payload_data["cumulative_sales"] = saved_sales if saved_sales is not None else Decimal("0.00")
    # 备货审核及时率只在周一、周三采集；其他日期保留当天已有值，首次提交按 100% 记录。
    if payload.report_date.weekday() not in (0, 2):
        payload_data["stocking_audit_rate"] = existing_report["stocking_audit_rate"] if existing_report else 100
    report = report_service.save_report(user, payload_data)
    background_tasks.add_task(_refresh_sales_snapshot, operator_id, payload.report_date)
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
def compliance(
    start_date: date | None = None,
    end_date: date | None = None,
    department: str | None = None,
    group: str | None = None,
    user: dict = Depends(get_current_user),
):
    if user["role"] == "operator":
        raise HTTPException(status_code=403, detail="运营角色无权查看合规汇总")
    end_date = end_date or date.today()
    start_date = start_date or end_date.replace(day=1)
    return report_service.compliance_overview(
        user,
        str(start_date),
        str(end_date),
        department=department,
        group=group,
    )
