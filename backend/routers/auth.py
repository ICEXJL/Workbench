from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

import config
from schemas import schemas
from services import audit_service, login_throttle, sales_service

router = APIRouter(prefix="/auth", tags=["认证"])
bearer = HTTPBearer(auto_error=False)


def require_roles(*roles: str):
    """角色守卫：仅允许指定角色访问，否则记录审计并返回 403。

    用于管理端接口的服务端授权；前端隐藏菜单不构成安全边界。
    """

    def guard(
        request: Request,
        user: dict = Depends(get_current_user),
    ) -> dict:
        if user.get("role") not in roles:
            audit_service.record_event(
                "deny_role_required",
                user.get("sub"),
                f"role={user.get('role')} path={request.url.path}",
            )
            raise HTTPException(status_code=403, detail="无权访问该功能")
        return user

    return guard


def create_access_token(user: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user["username"], "userId": user["userId"],
        "realName": user["realName"], "role": user["role"],
        "department": user.get("department"),
        "mustChangePassword": user.get("mustChangePassword", False),
        "exp": expire,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    try:
        payload = jwt.decode(
            credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM]
        )
        if payload.get("sub") is None:
            raise HTTPException(status_code=401, detail="无效的登录凭证")
        password_change_allowed = request.url.path.endswith("/auth/change-password") or request.url.path.endswith("/auth/me")
        # Tokens issued before the first-login flag existed must not bypass it.
        if payload.get("mustChangePassword", True) and not password_change_allowed:
            raise HTTPException(
                status_code=403,
                detail={"code": "PASSWORD_CHANGE_REQUIRED", "message": "首次登录必须先修改密码"},
            )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")


@router.post("/login", response_model=schemas.TokenResponse)
def login(request: Request, req: schemas.LoginRequest):
    username = req.username.strip()

    # IP 维度限流默认停用：全公司共用办公网出口 IP 时会误伤正常用户。
    # 停用时连request.client 都不读取，也不写入任何 IP 状态。
    if login_throttle.IP_LIMIT_ENABLED:
        client_ip = request.client.host if request.client else ""
        login_throttle.register_ip_attempt(client_ip)
        if login_throttle.is_ip_blocked(client_ip):
            audit_service.record_event("login_blocked_ip", username, f"ip={client_ip}")
            raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    else:
        client_ip = ""

    remaining = login_throttle.is_account_locked(username)
    if remaining:
        audit_service.record_event("login_blocked_account", username, f"ip={client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"账号已锁定，请在 {remaining} 秒后重试",
        )

    user = sales_service.find_user(username, req.password)
    if not user:
        login_throttle.register_failure(username)
        audit_service.record_event("login_failed", username, f"ip={client_ip}")
        raise HTTPException(status_code=401, detail="账号或密码错误，请核对后再试！")

    login_throttle.reset_account(username)
    identity = sales_service.resolve_identity(username)
    if not identity:
        raise HTTPException(status_code=403, detail="账号未关联运营档案，请联系管理端")
    token = create_access_token(identity)
    return schemas.TokenResponse(access_token=token, **identity)


@router.post("/change-password")
def change_password(
    req: schemas.ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=422, detail="两次输入的新密码不一致")
    if req.current_password == req.new_password:
        raise HTTPException(status_code=422, detail="新密码不能与当前密码相同")
    if not sales_service.change_password(
        user["sub"],
        req.current_password,
        req.new_password,
    ):
        raise HTTPException(status_code=400, detail="当前密码错误")
    identity = sales_service.resolve_identity(user["sub"])
    if not identity:
        raise HTTPException(status_code=403, detail="账号未关联运营档案，请联系管理端")
    return {
        "message": "密码修改成功",
        "access_token": create_access_token(identity),
        "token_type": "bearer",
        "mustChangePassword": False,
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {key: user.get(key) for key in ("sub", "userId", "realName", "role", "department", "mustChangePassword")}
