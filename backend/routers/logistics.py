from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from routers.auth import get_current_user
from services import logistics_service


router = APIRouter(prefix="/logistics", tags=["物流查询"])
_DATA_UNAVAILABLE = "物流数据暂时不可用，请联系管理员"


@router.get("/warehouses")
def warehouses(user: dict = Depends(get_current_user)):
    try:
        return logistics_service.get_warehouses()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=_DATA_UNAVAILABLE) from exc


@router.get("/search")
def search(
    q: str,
    warehouse: str | None = None,
    user: dict = Depends(get_current_user),
):
    try:
        return logistics_service.search_logistics(q, warehouse)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=_DATA_UNAVAILABLE) from exc
