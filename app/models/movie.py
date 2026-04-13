from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # genres stores human-readable labels, e.g. ["Action", "Sci-Fi"]
    genres: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False)

    # genre_vector is a pre-computed multi-hot encoding over the canonical
    # genre list (see services/recommendation.py).  Storing it denormalized
    # avoids recomputing the vector on every recommendation request.
    genre_vector: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)

    # Denormalized stats updated after each new rating for fast sorting/filtering
    average_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    ratings: Mapped[list["Rating"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Rating", back_populates="movie", cascade="all, delete-orphan"
    )
