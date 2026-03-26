from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.signal import Signal, TenantSignal
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/digest", tags=["digest"])

CLUSTER_NAMES = {
    "ai_drug_discovery": "AI в разработке лекарств",
    "oncology": "Онкология нового поколения",
    "biosimilars": "Биоаналоги и биосимиляры",
    "regulatory": "Регуляторика и GMP",
    "competitors_ru": "Конкуренты РФ",
    "export_markets": "Китай и экспортные рынки",
}


@router.get("/weekly", response_model=dict[str, Any])
async def get_weekly_digest(
    top_n: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a weekly digest of top signals for the current tenant."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    stmt = (
        select(TenantSignal)
        .options(selectinload(TenantSignal.signal))
        .join(Signal)
        .where(
            and_(
                TenantSignal.tenant_id == current_user.tenant_id,
                TenantSignal.is_dismissed == False,  # noqa: E712
            )
        )
        .order_by(TenantSignal.relevance_score.desc())
        .limit(top_n)
    )
    result = await db.execute(stmt)
    tenant_signals = result.scalars().all()

    top_signals = []
    new_signals = []
    trending_signals = []
    cluster_breakdown = {}

    for ts in tenant_signals:
        signal = ts.signal
        cluster = signal.cluster or "other"
        cluster_name = CLUSTER_NAMES.get(cluster, cluster)

        brief = {
            "id": str(signal.id),
            "title": signal.title,
            "description": signal.description,
            "cluster": cluster,
            "cluster_name": cluster_name,
            "signal_type": signal.signal_type.value,
            "composite_score": signal.composite_score,
            "novelty_score": signal.novelty_score,
            "momentum_score": signal.momentum_score,
            "confidence_level": signal.confidence_level,
            "status": signal.status.value,
            "first_detected": signal.first_detected.isoformat() if signal.first_detected else None,
            "relevance_score": ts.relevance_score,
            "industry_relevance": ts.industry_relevance,
            "competitor_activity": ts.competitor_activity,
            "opportunity_score": ts.opportunity_score,
        }
        top_signals.append(brief)

        if signal.first_detected and signal.first_detected >= week_ago:
            new_signals.append(brief)
        if signal.momentum_score >= 0.6:
            trending_signals.append(brief)

        if cluster_name not in cluster_breakdown:
            cluster_breakdown[cluster_name] = 0
        cluster_breakdown[cluster_name] += 1

    # Count totals
    all_stmt = (
        select(TenantSignal)
        .join(Signal)
        .where(
            and_(
                TenantSignal.tenant_id == current_user.tenant_id,
                TenantSignal.is_dismissed == False,  # noqa: E712
            )
        )
    )
    all_result = await db.execute(all_stmt)
    total_active = len(all_result.scalars().all())

    # Generate AI summary if Gemini is configured
    ai_summary = None
    if settings.GEMINI_API_KEY and top_signals:
        try:
            from app.services.nlp.gemini_analyzer import GeminiAnalyzer
            analyzer = GeminiAnalyzer(api_key=settings.GEMINI_API_KEY)
            ai_summary = await analyzer.generate_weekly_digest(
                top_signals,
                period_start=week_ago.strftime("%Y-%m-%d"),
                period_end=now.strftime("%Y-%m-%d"),
            )
            await analyzer.close()
        except Exception:
            pass

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
        "cluster_breakdown": cluster_breakdown,
        "top_signals": top_signals,
        "new_signals": new_signals,
        "trending_signals": trending_signals,
        "ai_summary": ai_summary,
        "watchlist": tenant.technology_watchlist or [],
    }
