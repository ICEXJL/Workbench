from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
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
        "department": user.get("department"), "exp": expire,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_current_user(
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


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {key: user.get(key) for key in ("sub", "userId", "realName", "role", "department")}
