from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    userId: str
    realName: str
    role: str
    department: str | None = None


class DailyReportPayload(BaseModel):
    report_date: date
    cumulative_sales: Decimal = Field(ge=0)
    listing_count: int = Field(ge=0)
    optimization_count: int = Field(ge=0)
    weekly_delay_exceeded: bool | None = None
    violation_triggered: bool
    infringement_triggered: bool
    weekly_bad_review_links: int | None = Field(default=None, ge=0)
    weekly_wrong_damage_links: int | None = Field(default=None, ge=0)
    stocking_audit_rate: Decimal = Field(ge=0, le=100)
    reverse_product_count: int = Field(ge=0)
    volatile_store_count: int = Field(ge=0)
    all_issues_resolved: bool


class MonthlyTargetPayload(BaseModel):
    operator_id: int
    department: str | None = None
    target_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    sales_target: Decimal = Field(ge=0)
    listing_target: int = Field(default=0, ge=0)
