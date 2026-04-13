from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.movie import Movie
from app.models.user import User
from app.schemas.movie import MovieCreate, MovieResponse
from app.services.movie_service import create_movie, search_movies

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", response_model=list[MovieResponse], summary="List all movies")
async def list_movies(
    limit: int = Query(default=20, ge=1, le=100, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> list[Movie]:
    result = await db.execute(
        select(Movie).order_by(Movie.average_rating.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.get("/search", response_model=list[MovieResponse], summary="Search movies")
async def search(
    q: Optional[str] = Query(default=None, description="Title keyword search"),
    genre: Optional[str] = Query(default=None, description="Filter by genre"),
    year: Optional[int] = Query(default=None, description="Filter by release year"),
    min_rating: Optional[float] = Query(default=None, ge=0.0, le=5.0, description="Minimum average rating"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Movie]:
    """
    Search movies using any combination of filters.  All parameters are optional.
    Results are ordered by average rating descending.
    """
    return await search_movies(
        db,
        query=q,
        genre=genre,
        year=year,
        min_rating=min_rating,
        limit=limit,
        offset=offset,
    )


@router.get("/{movie_id}", response_model=MovieResponse, summary="Get a movie by ID")
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> Movie:
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to the catalogue (requires auth)",
)
async def add_movie(
    body: MovieCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),  # wall-off unauthenticated writes
) -> Movie:
    return await create_movie(db, **body.model_dump())
