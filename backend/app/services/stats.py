from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PoopLog
from app.schemas import LeaderboardRow, MetricPoint


def to_local_day(value: datetime, timezone: str) -> date:
    zone = ZoneInfo(timezone)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(zone).date()


def daily_counts(logs: list[PoopLog], timezone: str, days: int = 14) -> list[MetricPoint]:
    today = datetime.now(ZoneInfo(timezone)).date()
    counts = Counter(to_local_day(log.occurred_at, timezone) for log in logs)
    points: list[MetricPoint] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        points.append(MetricPoint(label=day.isoformat(), value=counts.get(day, 0)))
    return points


def hourly_distribution(logs: list[PoopLog], timezone: str) -> list[MetricPoint]:
    zone = ZoneInfo(timezone)
    counts = Counter()
    for log in logs:
        occurred_at = log.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        counts[occurred_at.astimezone(zone).hour] += 1
    return [MetricPoint(label=f"{hour:02d}:00", value=counts.get(hour, 0)) for hour in range(24)]


def current_streak_days(logs: list[PoopLog], timezone: str) -> int:
    days_with_logs = {to_local_day(log.occurred_at, timezone) for log in logs}
    cursor = datetime.now(ZoneInfo(timezone)).date()
    streak = 0
    while cursor in days_with_logs:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def average_per_week(logs: list[PoopLog], timezone: str) -> float:
    if not logs:
        return 0.0
    days = [to_local_day(log.occurred_at, timezone) for log in logs]
    span_days = max((max(days) - min(days)).days + 1, 1)
    return round(len(logs) / span_days * 7, 2)


def count_leaderboard(db: Session, member_user_ids: list[str]) -> list[LeaderboardRow]:
    if not member_user_ids:
        return []

    from app.models import Profile

    rows = db.execute(
        select(PoopLog.user_id, Profile.display_name, func.count(PoopLog.id))
        .join(Profile, Profile.user_id == PoopLog.user_id)
        .where(PoopLog.user_id.in_(member_user_ids))
        .group_by(PoopLog.user_id, Profile.display_name)
        .order_by(func.count(PoopLog.id).desc())
        .limit(10)
    ).all()
    return [
        LeaderboardRow(user_id=user_id, display_name=display_name, value=count)
        for user_id, display_name, count in rows
    ]

