from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import PoopLog, User
from app.schemas import PersonalReport
from app.services.stats import (
    average_per_week,
    current_streak_days,
    daily_counts,
    hourly_distribution,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/me", response_model=PersonalReport)
def personal_report(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> PersonalReport:
    logs = list(
        db.scalars(
            select(PoopLog)
            .where(PoopLog.user_id == current_user.id)
            .order_by(PoopLog.occurred_at.asc())
        )
    )
    timezone = current_user.profile.timezone
    return PersonalReport(
        total_count=len(logs),
        current_streak_days=current_streak_days(logs, timezone),
        average_per_week=average_per_week(logs, timezone),
        daily_counts=daily_counts(logs, timezone),
        hourly_distribution=hourly_distribution(logs, timezone),
    )

