from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

import config
from schemas import schemas
from services import sales_service

router = APIRouter(prefix="/auth", tags=["认证"])
bearer = HTTPBearer(auto_error=False)


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
def login(req: schemas.LoginRequest):
    user = sales_service.find_user(req.username.strip(), req.password)
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误，请核对后再试！")
    identity = sales_service.resolve_identity(req.username.strip())
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
