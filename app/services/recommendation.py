"""
Content-based recommendation engine.

Algorithm
---------
1. Each movie is encoded as a multi-hot genre vector of length |GENRES|.
   e.g. ["Action", "Sci-Fi"] → [1,0,0,0,0,0,0,0,0,0,0,1,0,0]

2. The user's *preference vector* is computed as the rating-weighted average
   of the genre vectors of every movie they have rated.  A 5-star rating
   pulls the vector strongly toward that movie's genres; a 1-star pulls it
   away (by contributing low weight).

3. At query time we compute cosine similarity between the user preference
   vector and every unrated movie, then return the top-N.

4. Cold-start (no ratings yet): fall back to top-rated movies by global score.

The preference vector is persisted in the `user_preferences` table and
refreshed after every rating change, so recommendation queries are O(M)
where M = number of movies in the catalogue — no fan-out over ratings.
"""

from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.rating import Rating, UserPreference

# ── Canonical genre list ──────────────────────────────────────────────────────
# Order is fixed: position i in any genre vector corresponds to GENRES[i].
# Adding a new genre requires a data migration to recompute all stored vectors.
GENRES: list[str] = [
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Horror",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "Western",
]
GENRE_INDEX: dict[str, int] = {g: i for i, g in enumerate(GENRES)}
VECTOR_SIZE = len(GENRES)


def compute_genre_vector(genres: list[str]) -> list[float]:
    """Build a multi-hot encoded vector for the given list of genre strings."""
    vec = [0.0] * VECTOR_SIZE
    for g in genres:
        if g in GENRE_INDEX:
            vec[GENRE_INDEX[g]] = 1.0
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Cosine similarity in [0, 1].  Returns 0 if either vector is all-zero
    (avoids division by zero for movies with no genres or blank user vectors).
    """
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


async def recompute_user_preference(user_id: int, db: AsyncSession) -> None:
    """
    Recalculate the user's genre preference vector from their full rating
    history and persist it.  Called after every rating upsert.
    """
    rows = (
        await db.execute(
            select(Rating, Movie)
            .join(Movie, Rating.movie_id == Movie.id)
            .where(Rating.user_id == user_id)
        )
    ).all()

    if not rows:
        return

    # Weighted sum: higher-rated movies contribute more
    preference = np.zeros(VECTOR_SIZE, dtype=np.float64)
    total_weight = 0.0
    for rating_obj, movie in rows:
        w = float(rating_obj.rating)
        preference += w * np.array(movie.genre_vector, dtype=np.float64)
        total_weight += w

    if total_weight > 0:
        preference /= total_weight

    # Upsert preference row
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if pref:
        pref.genre_vector = preference.tolist()
    else:
        db.add(UserPreference(user_id=user_id, genre_vector=preference.tolist()))

    await db.commit()


async def get_recommendations(
    user_id: int,
    db: AsyncSession,
    limit: int = 10,
) -> list[tuple[Movie, float]]:
    """
    Return up to *limit* movies not yet rated by the user, ranked by cosine
    similarity to their preference vector.

    Returns list of (Movie, similarity_score) tuples.
    """
    # Fetch user preference vector
    pref_row = (
        await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
    ).scalar_one_or_none()

    # ── Cold-start fallback ───────────────────────────────────────────────
    if pref_row is None or not pref_row.genre_vector:
        top = (
            await db.execute(
                select(Movie)
                .where(Movie.rating_count > 0)
                .order_by(Movie.average_rating.desc(), Movie.rating_count.desc())
                .limit(limit)
            )
        ).scalars().all()
        # Normalise to [0,1] for a consistent similarity_score interface
        return [(m, round(m.average_rating / 5.0, 4)) for m in top]

    # IDs of movies the user has already rated (exclude from candidates)
    rated_ids: set[int] = set(
        (await db.execute(select(Rating.movie_id).where(Rating.user_id == user_id)))
        .scalars()
        .all()
    )

    # Fetch all candidate movies
    stmt = select(Movie)
    if rated_ids:
        stmt = stmt.where(Movie.id.not_in(rated_ids))
    candidates: list[Movie] = (await db.execute(stmt)).scalars().all()

    # Score and sort
    scored = [
        (movie, cosine_similarity(pref_row.genre_vector, movie.genre_vector))
        for movie in candidates
    ]
    # Primary sort: similarity desc; secondary: average_rating desc (tiebreak)
    scored.sort(key=lambda x: (x[1], x[0].average_rating), reverse=True)

    return scored[:limit]
