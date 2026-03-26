import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.signal import Signal, SignalStatus, SignalType, TenantSignal
from app.models.user import User, UserRole
from app.schemas.signal import (
    SignalResponse,
    SignalTrajectory,
    SignalTrajectoryPoint,
    TenantSignalResponse,
)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[TenantSignalResponse])
async def list_signals(
    category: SignalType | None = Query(None, description="Filter by signal type"),
    cluster: str | None = Query(None, description="Filter by cluster (ai_drug_discovery, oncology, etc.)"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite score"),
    time_range: str | None = Query(
        None,
        description="Time range filter: 7d, 30d, 90d, 1y",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TenantSignal)
        .options(selectinload(TenantSignal.signal))
        .where(
            and_(
                TenantSignal.tenant_id == current_user.tenant_id,
                TenantSignal.is_dismissed == False,  # noqa: E712
            )
        )
    )

    joined = False
    if category is not None:
        stmt = stmt.join(Signal)
        stmt = stmt.where(Signal.signal_type == category)
        joined = True

    if cluster is not None:
        if not joined:
            stmt = stmt.join(Signal)
            joined = True
        stmt = stmt.where(Signal.cluster == cluster)

    if min_score > 0.0:
        if not joined:
            stmt = stmt.join(Signal)
            joined = True
        stmt = stmt.where(Signal.composite_score >= min_score)

    if time_range is not None:
        now = datetime.now(timezone.utc)
        delta_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = delta_map.get(time_range)
        if days is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range. Use one of: {list(delta_map.keys())}",
            )
        cutoff = now - timedelta(days=days)
        stmt = stmt.where(Signal.first_detected >= cutoff)

    stmt = stmt.order_by(TenantSignal.relevance_score.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    tenant_signals = result.scalars().all()
    return tenant_signals


@router.get("/{signal_id}", response_model=TenantSignalResponse)
async def get_signal(
    signal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TenantSignal)
        .options(selectinload(TenantSignal.signal))
        .where(
            and_(
                TenantSignal.signal_id == signal_id,
                TenantSignal.tenant_id == current_user.tenant_id,
            )
        )
    )
    result = await db.execute(stmt)
    tenant_signal = result.scalar_one_or_none()
    if tenant_signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found for this tenant",
        )
    return tenant_signal


@router.get("/{signal_id}/trajectory", response_model=SignalTrajectory)
async def get_signal_trajectory(
    signal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify signal belongs to tenant
    stmt = select(TenantSignal).where(
        and_(
            TenantSignal.signal_id == signal_id,
            TenantSignal.tenant_id == current_user.tenant_id,
        )
    )
    result = await db.execute(stmt)
    tenant_signal = result.scalar_one_or_none()
    if tenant_signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found for this tenant",
        )

    # Fetch the signal itself
    signal_result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = signal_result.scalar_one()

    # Generate trajectory points from signal data.
    # In a full implementation these would come from a time-series table.
    # For the MVP we synthesize points from the signal's detection window.
    points: list[SignalTrajectoryPoint] = []
    start = signal.first_detected
    end = signal.last_updated
    if start and end and end > start:
        total_seconds = (end - start).total_seconds()
        num_points = min(int(total_seconds / 86400) + 1, 30)  # max 30 daily points
        if num_points < 2:
            num_points = 2
        step = total_seconds / (num_points - 1)
        for i in range(num_points):
            t = start + timedelta(seconds=step * i)
            # Linear interpolation for MVP
            frac = i / (num_points - 1)
            points.append(
                SignalTrajectoryPoint(
                    timestamp=t,
                    metric_name="composite_score",
                    value=round(signal.composite_score * frac, 4),
                )
            )
            points.append(
                SignalTrajectoryPoint(
                    timestamp=t,
                    metric_name="novelty_score",
                    value=round(signal.novelty_score * (1 - 0.3 * frac), 4),
                )
            )
            points.append(
                SignalTrajectoryPoint(
                    timestamp=t,
                    metric_name="momentum_score",
                    value=round(signal.momentum_score * frac, 4),
                )
            )
    else:
        now = datetime.now(timezone.utc)
        for metric, value in [
            ("composite_score", signal.composite_score),
            ("novelty_score", signal.novelty_score),
            ("momentum_score", signal.momentum_score),
        ]:
            points.append(
                SignalTrajectoryPoint(timestamp=now, metric_name=metric, value=value)
            )

    return SignalTrajectory(signal_id=signal.id, title=signal.title, points=points)


@router.post("/{signal_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_signal(
    signal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.ceo, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO or admin can dismiss signals",
        )

    stmt = select(TenantSignal).where(
        and_(
            TenantSignal.signal_id == signal_id,
            TenantSignal.tenant_id == current_user.tenant_id,
        )
    )
    result = await db.execute(stmt)
    tenant_signal = result.scalar_one_or_none()
    if tenant_signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found for this tenant",
        )
    tenant_signal.is_dismissed = True
    await db.flush()
