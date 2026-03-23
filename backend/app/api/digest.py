from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.signal import Signal, TenantSignal
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.signal import SignalBrief

router = APIRouter(prefix="/digest", tags=["digest"])


@router.get("/weekly", response_model=dict[str, Any])
async def get_weekly_digest(
    top_n: int = Query(10, ge=1, le=50, description="Number of top signals to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a weekly digest of top signals for the current tenant."""
    # Get tenant info
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Get top signals from the past week, ranked by relevance
    stmt = (
        select(TenantSignal)
        .options(selectinload(TenantSignal.signal))
        .join(Signal)
        .where(
            and_(
                TenantSignal.tenant_id == current_user.tenant_id,
                TenantSignal.is_dismissed == False,  # noqa: E712
                Signal.last_updated >= week_ago,
            )
        )
        .order_by(TenantSignal.relevance_score.desc())
        .limit(top_n)
    )
    result = await db.execute(stmt)
    tenant_signals = result.scalars().all()

    # Build digest sections
    top_signals = []
    new_signals = []
    trending_signals = []

    for ts in tenant_signals:
        signal = ts.signal
        brief = {
            "id": str(signal.id),
            "title": signal.title,
            "signal_type": signal.signal_type.value,
            "composite_score": signal.composite_score,
            "confidence_level": signal.confidence_level,
            "status": signal.status.value,
            "first_detected": signal.first_detected.isoformat() if signal.first_detected else None,
            "relevance_score": ts.relevance_score,
            "industry_relevance": ts.industry_relevance,
            "opportunity_score": ts.opportunity_score,
        }
        top_signals.append(brief)

        if signal.first_detected and signal.first_detected >= week_ago:
            new_signals.append(brief)

        if signal.momentum_score >= 0.6:
            trending_signals.append(brief)

    # Aggregate stats
    all_signals_stmt = (
        select(TenantSignal)
        .join(Signal)
        .where(
            and_(
                TenantSignal.tenant_id == current_user.tenant_id,
                TenantSignal.is_dismissed == False,  # noqa: E712
            )
        )
    )
    all_result = await db.execute(all_signals_stmt)
    total_active = len(all_result.scalars().all())

    return {
        "tenant_name": tenant.name,
        "period": {
            "start": week_ago.isoformat(),
            "end": now.isoformat(),
        },
        "summary": {
            "total_active_signals": total_active,
            "new_this_week": len(new_signals),
            "trending": len(trending_signals),
        },
        "top_signals": top_signals,
        "new_signals": new_signals,
        "trending_signals": trending_signals,
        "watchlist": tenant.technology_watchlist or [],
    }
