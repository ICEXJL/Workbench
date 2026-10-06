from datetime import date, datetime
from decimal import Decimal
import re

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("新密码不能超过 72 个字节")
        if not any(char.isascii() and char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("新密码必须同时包含字母和数字")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    userId: str
    realName: str
    role: str
    department: str | None = None
    mustChangePassword: bool = False


class DailyReportPayload(BaseModel):
    report_date: date
    # Compatibility only: the server recalculates this value from fbs_data.
    cumulative_sales: Decimal | None = None
    listing_count: int = Field(ge=0)
    optimization_count: int = Field(ge=0)
    weekly_delay_exceeded: bool | None = None
    violation_triggered: bool
    infringement_triggered: bool
    weekly_bad_review_links: int | None = Field(default=None, ge=0)
    weekly_wrong_damage_links: int | None = Field(default=None, ge=0)
    stocking_audit_rate: Decimal = Field(ge=0, le=100)
    reverse_product_count: int = Field(ge=0)
    # 该字段已由上涨/下滑数量自动汇总，兼容旧版客户端传 null。
    volatile_store_count: int | None = Field(default=None, ge=0)
    rising_shop_count: int = Field(default=0, ge=0)
    rising_shop_names: list[str] = Field(default_factory=list)
    falling_shop_count: int = Field(default=0, ge=0)
    falling_shop_names: list[str] = Field(default_factory=list)
    all_issues_resolved: bool

    @field_validator("rising_shop_names", "falling_shop_names", mode="before")
    @classmethod
    def normalize_shop_names(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        values = re.split(r"[,，、\n]+", value) if isinstance(value, str) else value
        if not isinstance(values, (list, tuple, set)):
            raise ValueError("店铺名称格式不正确")
        return [str(name).strip() for name in values if str(name).strip()]


class MonthlyTargetPayload(BaseModel):
    operator_id: int
    department: str | None = None
    target_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    sales_target: Decimal = Field(ge=0)
    listing_target: int = Field(default=0, ge=0)
