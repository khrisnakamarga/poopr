from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileRead)
def read_profile(current_user: User = Depends(get_current_user)) -> ProfileRead:
    return ProfileRead(
        id=current_user.profile.id,
        email=current_user.email,
        display_name=current_user.profile.display_name,
        avatar_url=current_user.profile.avatar_url,
        timezone=current_user.profile.timezone,
    )


@router.put("/me", response_model=ProfileRead)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileRead:
    current_user.profile.display_name = payload.display_name
    current_user.profile.avatar_url = payload.avatar_url
    current_user.profile.timezone = payload.timezone
    db.commit()
    db.refresh(current_user)
    return read_profile(current_user)

