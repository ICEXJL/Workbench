from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from routers.auth import get_current_user, require_roles
from services import sales_service

router = APIRouter(prefix="/sales", tags=["销售数据"])

# 管理端接口：service 层未接收可见范围参数，必须在路由层限制为admin。
admin_only = require_roles("admin")


def yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


@router.get("/daily")
def daily_sales(
    target_date: str | None = None,
    store: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    user: dict = Depends(get_current_user),
):
    return sales_service.get_daily_sales(user, target_date or yesterday_str(), store, page, page_size)


@router.get("/personnel")
def personnel_sales(
    cxrq: str | None = None,
    department: str | None = None,
    group: str | None = None,
    operator: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    user: dict = Depends(get_current_user),
):
    return sales_service.get_personnel_sales(user, cxrq or yesterday_str(), department, group, operator, page, page_size)


@router.get("/stats/regional")
def regional_stats(user: dict = Depends(admin_only)):
    """近7天各地区统计。"""
    return sales_service.get_regional_stats()


@router.get("/stats/platform")
def platform_stats(user: dict = Depends(admin_only)):
    """近7天各平台统计。"""
    return sales_service.get_platform_stats()


@router.get("/distribution/region")
def region_distribution(user: dict = Depends(admin_only)):
    """昨日各区域分布。"""
    return sales_service.get_t1_region_distribution(yesterday_str())


@router.get("/distribution/warehouse")
def warehouse_distribution(user: dict = Depends(admin_only)):
    """昨日各仓库分布。"""
    return sales_service.get_t1_warehouse_distribution(yesterday_str())


@router.get("/management")
def personnel_management(user: dict = Depends(admin_only)):
    """人员管理列表。"""
    return sales_service.get_personnel_management()
