"""
Movie business logic — creation, search, and denormalized stat updates.

Denormalized averages
---------------------
We store `average_rating` and `rating_count` directly on the Movie row so
that listing / searching movies by rating doesn't require an aggregation join
on every request.  The trade-off is a small write overhead on every rating
change; for a read-heavy workload this is the right choice.
"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.rating import Rating
from app.services.recommendation import compute_genre_vector


async def create_movie(db: AsyncSession, **kwargs) -> Movie:
    """
    Persist a new movie.  The genre_vector is computed here so callers
    only need to supply the human-readable genres list.
    """
    genre_vector = compute_genre_vector(kwargs["genres"])
    movie = Movie(**kwargs, genre_vector=genre_vector)
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie


async def get_movie_or_404(movie_id: int, db: AsyncSession) -> Movie:
    """Return the movie or raise a 404-style ValueError."""
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        raise ValueError(f"Movie {movie_id} not found")
    return movie


async def search_movies(
    db: AsyncSession,
    *,
    query: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    min_rating: Optional[float] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Movie]:
    """
    Flexible movie search.  All filters are optional and composable.

    - query   : case-insensitive substring match on title
    - genre   : exact match for one genre in the genres array
    - year    : exact release year
    - min_rating : minimum average_rating (inclusive)
    """
    stmt = select(Movie)

    if query:
        stmt = stmt.where(Movie.title.ilike(f"%{query}%"))
    if genre:
        # PostgreSQL: genre = ANY(genres) — checks if the value is in the array
        stmt = stmt.where(Movie.genres.any(genre))
    if year is not None:
        stmt = stmt.where(Movie.year == year)
    if min_rating is not None:
        stmt = stmt.where(Movie.average_rating >= min_rating)

    stmt = stmt.order_by(Movie.average_rating.desc(), Movie.id.asc()).limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


async def refresh_movie_stats(movie_id: int, db: AsyncSession) -> None:
    """
    Recompute average_rating and rating_count from the ratings table and
    write them back to the movie row.  Must be called after any rating change.
    """
    agg = (
        await db.execute(
            select(
                func.avg(Rating.rating).label("avg"),
                func.count(Rating.id).label("cnt"),
            ).where(Rating.movie_id == movie_id)
        )
    ).one()

    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one()
    movie.average_rating = round(float(agg.avg or 0.0), 2)
    movie.rating_count = agg.cnt
    await db.commit()
