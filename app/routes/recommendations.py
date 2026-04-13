from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.movie import MovieResponse
from app.schemas.rating import RecommendationItem
from app.services.recommendation import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "",
    response_model=list[RecommendationItem],
    summary="Personalised movie recommendations for the authenticated user",
)
async def recommend(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecommendationItem]:
    """
    Returns movies ranked by cosine similarity between the user's genre
    preference vector and each movie's genre vector.

    **Cold start**: if the user has no rating history yet, falls back to the
    globally top-rated movies.
    """
    results = await get_recommendations(user_id=current_user.id, db=db, limit=limit)
    return [
        {
            "movie": MovieResponse.model_validate(movie),
            "similarity_score": round(score, 4),
        }
        for movie, score in results
    ]
