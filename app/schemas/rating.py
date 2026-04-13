from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.movie import MovieResponse


class RatingCreate(BaseModel):
    rating: int

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class RatingResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationItem(BaseModel):
    """A recommended movie paired with its similarity score (0–1)."""

    movie: MovieResponse
    similarity_score: float
