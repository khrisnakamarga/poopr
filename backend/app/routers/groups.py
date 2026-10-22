from __future__ import annotations

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Group, GroupActivity, GroupMembership, InviteCode, PoopLog, Profile, User
from app.schemas import (
    ActivityRead,
    GroupCreate,
    GroupDashboard,
    GroupRead,
    InviteCodeRead,
    JoinGroupRequest,
)
from app.services.stats import count_leaderboard, hourly_distribution

router = APIRouter(prefix="/groups", tags=["groups"])


def generate_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def require_member(db: Session, group_id: str, user_id: str) -> GroupMembership:
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id, GroupMembership.user_id == user_id
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Group not found")
    return membership


@router.get("", response_model=list[GroupRead])
def list_groups(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[GroupRead]:
    memberships = db.scalars(
        select(GroupMembership).where(GroupMembership.user_id == current_user.id)
    ).all()
    return [
        GroupRead(
            id=membership.group.id,
            name=membership.group.name,
            role=membership.role,
            member_count=len(membership.group.memberships),
        )
        for membership in memberships
    ]


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    group = Group(name=payload.name, owner_id=current_user.id)
    membership = GroupMembership(group=group, user_id=current_user.id, role="owner")
    db.add(group)
    db.add(membership)
    db.commit()
    db.refresh(group)
    return GroupRead(id=group.id, name=group.name, role="owner", member_count=1)


@router.post("/{group_id}/invite-codes", response_model=InviteCodeRead, status_code=201)
def create_invite_code(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InviteCodeRead:
    membership = require_member(db, group_id, current_user.id)
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only group admins can create invite codes")

    code = generate_code()
    while db.scalar(select(InviteCode).where(InviteCode.code == code)):
        code = generate_code()

    invite = InviteCode(group_id=group_id, code=code, created_by_id=current_user.id)
    db.add(invite)
    db.commit()
    return InviteCodeRead(code=code)


@router.post("/join", response_model=GroupRead)
def join_group(
    payload: JoinGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    invite = db.scalar(select(InviteCode).where(InviteCode.code == payload.code.upper()))
    if not invite:
        raise HTTPException(status_code=404, detail="Invite code not found")

    existing = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == invite.group_id, GroupMembership.user_id == current_user.id
        )
    )
    if existing:
        return GroupRead(
            id=invite.group.id,
            name=invite.group.name,
            role=existing.role,
            member_count=len(invite.group.memberships),
        )

    membership = GroupMembership(group_id=invite.group_id, user_id=current_user.id, role="member")
    db.add(membership)
    db.commit()
    db.refresh(invite.group)
    return GroupRead(
        id=invite.group.id,
        name=invite.group.name,
        role="member",
        member_count=len(invite.group.memberships),
    )


@router.get("/{group_id}/dashboard", response_model=GroupDashboard)
def group_dashboard(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupDashboard:
    membership = require_member(db, group_id, current_user.id)
    group = membership.group
    member_user_ids = [member.user_id for member in group.memberships]
    logs = list(db.scalars(select(PoopLog).where(PoopLog.user_id.in_(member_user_ids))))
    activity_rows = db.execute(
        select(GroupActivity, Profile.display_name, PoopLog.occurred_at)
        .join(Profile, Profile.user_id == GroupActivity.user_id)
        .join(PoopLog, PoopLog.id == GroupActivity.poop_log_id)
        .where(GroupActivity.group_id == group_id)
        .order_by(GroupActivity.created_at.desc())
        .limit(20)
    ).all()

    return GroupDashboard(
        group_id=group.id,
        group_name=group.name,
        member_count=len(group.memberships),
        total_count=len(logs),
        leaderboards={"most_logs": count_leaderboard(db, member_user_ids)},
        hourly_distribution=hourly_distribution(logs, current_user.profile.timezone),
        recent_activity=[
            ActivityRead(
                id=activity.id,
                display_name=display_name,
                occurred_at=occurred_at,
                activity_type=activity.activity_type,
            )
            for activity, display_name, occurred_at in activity_rows
        ],
    )

