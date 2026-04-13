from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Integer 1–5 enforced at DB level via CheckConstraint above
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="ratings")  # type: ignore[name-defined]  # noqa: F821
    movie: Mapped["Movie"] = relationship("Movie", back_populates="ratings")  # type: ignore[name-defined]  # noqa: F821


class UserPreference(Base):
    """
    Stores the user's aggregated genre preference vector.

    This is recomputed whenever the user submits or updates a rating so that
    recommendation queries are just a vector similarity lookup — no fan-out
    across the ratings table at request time.
    """

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Weighted average of genre vectors for all movies the user has rated
    genre_vector: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="preference")  # type: ignore[name-defined]  # noqa: F821
