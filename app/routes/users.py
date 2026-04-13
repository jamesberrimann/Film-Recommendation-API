from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.rating import UserPreference
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.recommendation import GENRES

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get the current user's profile")
async def get_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/preferences", summary="Get the current user's genre preference scores")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns the user's genre affinity scores derived from their rating history.
    Scores are in [0, 1]; genres not yet encountered are omitted.
    """
    pref = (
        await db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not pref or not pref.genre_vector:
        return {
            "message": "No preferences yet — start rating movies!",
            "preferences": {},
        }

    # Pair each genre with its score and sort highest first
    preferences = {
        genre: round(score, 4)
        for genre, score in zip(GENRES, pref.genre_vector)
        if score > 0.0
    }
    return {
        "preferences": dict(sorted(preferences.items(), key=lambda kv: kv[1], reverse=True))
    }
