from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileRead(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    timezone: str


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=500)
    timezone: str = Field(default="America/Los_Angeles", max_length=80)


class PoopLogCreate(BaseModel):
    occurred_at: datetime
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    stool_type: int | None = Field(default=None, ge=1, le=7)
    urgency: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=1000)


class PoopLogUpdate(PoopLogCreate):
    pass


class PoopLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    occurred_at: datetime
    duration_seconds: int | None
    stool_type: int | None
    urgency: int | None
    notes: str | None
    created_at: datetime


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class InviteCodeRead(BaseModel):
    code: str


class GroupRead(BaseModel):
    id: str
    name: str
    role: str
    member_count: int


class JoinGroupRequest(BaseModel):
    code: str = Field(min_length=4, max_length=24)


class ActivityRead(BaseModel):
    id: str
    display_name: str
    occurred_at: datetime
    activity_type: str


class MetricPoint(BaseModel):
    label: str
    value: int | float


class LeaderboardRow(BaseModel):
    user_id: str
    display_name: str
    value: int | float


class PersonalReport(BaseModel):
    total_count: int
    current_streak_days: int
    average_per_week: float
    daily_counts: list[MetricPoint]
    hourly_distribution: list[MetricPoint]


class GroupDashboard(BaseModel):
    group_id: str
    group_name: str
    member_count: int
    total_count: int
    leaderboards: dict[str, list[LeaderboardRow]]
    hourly_distribution: list[MetricPoint]
    recent_activity: list[ActivityRead]

