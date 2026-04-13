from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.movie import Movie
from app.models.rating import Rating
from app.models.user import User
from app.schemas.rating import RatingCreate, RatingResponse
from app.services.movie_service import refresh_movie_stats
from app.services.recommendation import recompute_user_preference

router = APIRouter(tags=["Ratings"])


@router.post(
    "/movies/{movie_id}/rate",
    response_model=RatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a movie (1–5).  Re-rating updates the existing score.",
)
async def rate_movie(
    movie_id: int,
    body: RatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Rating:
    # Verify movie exists
    movie = (await db.execute(select(Movie).where(Movie.id == movie_id))).scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    # Upsert: update existing rating rather than reject duplicates
    existing = (
        await db.execute(
            select(Rating).where(
                Rating.user_id == current_user.id,
                Rating.movie_id == movie_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.rating = body.rating
        rating = existing
    else:
        rating = Rating(user_id=current_user.id, movie_id=movie_id, rating=body.rating)
        db.add(rating)

    await db.commit()
    await db.refresh(rating)

    # Keep denormalized stats and preference vector in sync.
    # These are quick updates on small sets, so awaiting them inline is fine.
    await refresh_movie_stats(movie_id, db)
    await recompute_user_preference(current_user.id, db)

    return rating


@router.get(
    "/movies/{movie_id}/ratings",
    response_model=list[RatingResponse],
    summary="Get all ratings for a movie",
)
async def get_movie_ratings(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[Rating]:
    # Confirm movie exists to give a meaningful 404 rather than an empty list
    movie = (await db.execute(select(Movie).where(Movie.id == movie_id))).scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return (await db.execute(select(Rating).where(Rating.movie_id == movie_id))).scalars().all()


@router.get(
    "/users/me/ratings",
    response_model=list[RatingResponse],
    summary="Get all ratings submitted by the current user",
)
async def get_my_ratings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Rating]:
    return (
        await db.execute(select(Rating).where(Rating.user_id == current_user.id))
    ).scalars().all()
