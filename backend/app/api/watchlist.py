from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItem(BaseModel):
    technology: str = Field(..., min_length=1, max_length=512)


class WatchlistResponse(BaseModel):
    items: list[str]
    total: int


async def _get_tenant(user: User, db: AsyncSession) -> Tenant:
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


@router.get("", response_model=WatchlistResponse)
async def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(current_user, db)
    items = tenant.technology_watchlist or []
    return WatchlistResponse(items=items, total=len(items))


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistItem,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(current_user, db)
    current_list = list(tenant.technology_watchlist or [])

    normalized = body.technology.strip()
    if normalized.lower() in [item.lower() for item in current_list]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{normalized}' is already on the watchlist",
        )

    current_list.append(normalized)
    tenant.technology_watchlist = current_list
    await db.flush()
    await db.refresh(tenant)

    items = tenant.technology_watchlist or []
    return WatchlistResponse(items=items, total=len(items))


@router.delete("/{item}", status_code=status.HTTP_200_OK, response_model=WatchlistResponse)
async def remove_from_watchlist(
    item: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(current_user, db)
    current_list = list(tenant.technology_watchlist or [])

    # Case-insensitive removal
    lower_item = item.strip().lower()
    new_list = [t for t in current_list if t.lower() != lower_item]

    if len(new_list) == len(current_list):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{item}' not found on the watchlist",
        )

    tenant.technology_watchlist = new_list
    await db.flush()
    await db.refresh(tenant)

    items = tenant.technology_watchlist or []
    return WatchlistResponse(items=items, total=len(items))
