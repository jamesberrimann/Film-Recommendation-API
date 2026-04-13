from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships (lazy="selectin" avoids N+1 queries in async context)
    ratings: Mapped[list["Rating"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Rating", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    preference: Mapped["UserPreference"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
