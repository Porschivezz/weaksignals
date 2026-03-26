"""Pipeline management API — trigger ingestion, analysis, etc."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/trigger-ingestion")
async def trigger_ingestion(
    current_user: User = Depends(get_current_user),
):
    """Trigger a full ingestion + analysis pipeline run."""
    if current_user.role not in (UserRole.ceo, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO or admin can trigger pipeline",
        )

    from app.workers.tasks import ingest_all_sources_task, analyze_and_score_task, compute_tenant_relevance_task

    # Queue tasks in sequence
    chain = ingest_all_sources_task.apply_async()

    return {
        "status": "triggered",
        "task_id": str(chain.id),
        "message": "Ingestion pipeline started. Signals will appear within ~10 minutes.",
    }


@router.post("/trigger-analysis")
async def trigger_analysis(
    current_user: User = Depends(get_current_user),
):
    """Trigger signal analysis on unprocessed documents."""
    if current_user.role not in (UserRole.ceo, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO or admin can trigger analysis",
        )

    from app.workers.tasks import analyze_and_score_task
    task = analyze_and_score_task.apply_async()

    return {
        "status": "triggered",
        "task_id": str(task.id),
        "message": "Analysis pipeline started.",
    }
