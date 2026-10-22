from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import GroupActivity, GroupMembership, PoopLog, User
from app.schemas import PoopLogCreate, PoopLogRead, PoopLogUpdate

router = APIRouter(prefix="/poop-logs", tags=["poop logs"])


@router.get("", response_model=list[PoopLogRead])
def list_logs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[PoopLog]:
    return list(
        db.scalars(
            select(PoopLog)
            .where(PoopLog.user_id == current_user.id)
            .order_by(PoopLog.occurred_at.desc())
            .limit(100)
        )
    )


@router.post("", response_model=PoopLogRead, status_code=status.HTTP_201_CREATED)
def create_log(
    payload: PoopLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PoopLog:
    log = PoopLog(user_id=current_user.id, **payload.model_dump())
    db.add(log)
    db.flush()

    memberships = db.scalars(
        select(GroupMembership).where(GroupMembership.user_id == current_user.id)
    ).all()
    for membership in memberships:
        db.add(
            GroupActivity(
                group_id=membership.group_id,
                user_id=current_user.id,
                poop_log_id=log.id,
            )
        )

    db.commit()
    db.refresh(log)
    return log


@router.patch("/{log_id}", response_model=PoopLogRead)
def update_log(
    log_id: str,
    payload: PoopLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PoopLog:
    log = db.scalar(select(PoopLog).where(PoopLog.id == log_id, PoopLog.user_id == current_user.id))
    if not log:
        raise HTTPException(status_code=404, detail="Poop log not found")

    for key, value in payload.model_dump().items():
        setattr(log, key, value)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    log = db.scalar(select(PoopLog).where(PoopLog.id == log_id, PoopLog.user_id == current_user.id))
    if not log:
        raise HTTPException(status_code=404, detail="Poop log not found")
    db.delete(log)
    db.commit()

