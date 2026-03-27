"""Pipeline management API — trigger ingestion, analysis, progress tracking."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/trigger-ingestion")
async def trigger_ingestion(
    current_user: User = Depends(get_current_user),
):
    """Trigger the full pipeline: ingestion → analysis → tenant relevance."""
    if current_user.role not in (UserRole.ceo, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO or admin can trigger pipeline",
        )

    from app.workers.tasks import run_full_pipeline_task

    task = run_full_pipeline_task.apply_async()

    return {
        "status": "triggered",
        "task_id": str(task.id),
        "message": "Полный пайплайн запущен: сбор → анализ → оценка релевантности.",
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


@router.get("/progress/{task_id}")
async def get_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get pipeline progress by task ID."""
    from app.workers.tasks import get_pipeline_progress

    progress = get_pipeline_progress(task_id)
    if progress is None:
        return {
            "task_id": task_id,
            "status": "unknown",
            "error": "Задача не найдена или истекла",
        }
    return progress
