from datetime import datetime

from pydantic import BaseModel, field_validator

# Canonical genre list — must match the order in services/recommendation.py
VALID_GENRES = {
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Horror", "Mystery",
    "Romance", "Sci-Fi", "Thriller", "Western",
}


class MovieCreate(BaseModel):
    title: str
    year: int | None = None
    description: str | None = None
    genres: list[str]

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_GENRES
        if invalid:
            raise ValueError(f"Invalid genre(s): {invalid}. Valid genres: {sorted(VALID_GENRES)}")
        if not v:
            raise ValueError("At least one genre is required")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int | None) -> int | None:
        if v is not None and not (1888 <= v <= 2100):
            raise ValueError("Year must be between 1888 and 2100")
        return v


class MovieResponse(BaseModel):
    id: int
    title: str
    year: int | None
    description: str | None
    genres: list[str]
    average_rating: float
    rating_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
