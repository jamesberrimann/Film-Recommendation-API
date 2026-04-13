"""
Database seeding script.

Inserts 25 classic and contemporary films if the movies table is empty.
Run once after starting the stack:

    docker compose run --rm api python scripts/seed_db.py

Or locally (with a .env file present):

    python scripts/seed_db.py
"""

import asyncio
import os
import sys

# Allow running from the project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.models.movie import Movie
from app.services.recommendation import compute_genre_vector

# fmt: off
SEED_MOVIES = [
    {
        "title": "The Dark Knight",
        "year": 2008,
        "description": "Batman raises the stakes in his war on crime with the help of Lt. Jim Gordon and DA Harvey Dent, but the anarchic Joker threatens to derail everything.",
        "genres": ["Action", "Crime", "Drama", "Thriller"],
    },
    {
        "title": "Inception",
        "year": 2010,
        "description": "A thief who steals corporate secrets through dream-sharing technology is given the task of planting an idea into the mind of a CEO.",
        "genres": ["Action", "Adventure", "Sci-Fi", "Thriller"],
    },
    {
        "title": "The Shawshank Redemption",
        "year": 1994,
        "description": "Two imprisoned men bond over several years, finding solace and eventual redemption through acts of common decency.",
        "genres": ["Drama"],
    },
    {
        "title": "The Godfather",
        "year": 1972,
        "description": "The aging patriarch of an organized crime dynasty transfers control to his reluctant son.",
        "genres": ["Crime", "Drama"],
    },
    {
        "title": "Pulp Fiction",
        "year": 1994,
        "description": "The lives of two mob hit men, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.",
        "genres": ["Crime", "Drama", "Thriller"],
    },
    {
        "title": "Forrest Gump",
        "year": 1994,
        "description": "The presidencies of Kennedy and Johnson, Vietnam, Watergate, and other events unfold from the perspective of an Alabama man with an IQ of 75.",
        "genres": ["Comedy", "Drama", "Romance"],
    },
    {
        "title": "The Matrix",
        "year": 1999,
        "description": "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.",
        "genres": ["Action", "Sci-Fi"],
    },
    {
        "title": "Interstellar",
        "year": 2014,
        "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        "genres": ["Adventure", "Drama", "Sci-Fi"],
    },
    {
        "title": "Goodfellas",
        "year": 1990,
        "description": "The story of Henry Hill and his life in the mob, covering his introduction to the life at age 13 through his eventual testimony against his former friends.",
        "genres": ["Crime", "Drama"],
    },
    {
        "title": "Fight Club",
        "year": 1999,
        "description": "An insomniac office worker and a devil-may-care soapmaker form an underground fight club that evolves into something much more dangerous.",
        "genres": ["Drama", "Thriller"],
    },
    {
        "title": "The Silence of the Lambs",
        "year": 1991,
        "description": "A young FBI cadet must receive the help of an imprisoned cannibalistic serial killer to help catch another serial killer.",
        "genres": ["Crime", "Drama", "Horror", "Thriller"],
    },
    {
        "title": "Jurassic Park",
        "year": 1993,
        "description": "A pragmatic paleontologist visiting an almost-complete theme park is tasked with ensuring it is safe, while dinosaurs break free.",
        "genres": ["Action", "Adventure", "Sci-Fi", "Thriller"],
    },
    {
        "title": "Titanic",
        "year": 1997,
        "description": "A seventeen-year-old aristocrat falls in love with a kind but poor artist aboard the luxurious, ill-fated R.M.S. Titanic.",
        "genres": ["Drama", "Romance"],
    },
    {
        "title": "Avengers: Endgame",
        "year": 2019,
        "description": "After the devastating events of Infinity War, the Avengers assemble once more to reverse Thanos's actions and restore balance.",
        "genres": ["Action", "Adventure", "Drama", "Sci-Fi"],
    },
    {
        "title": "The Lion King",
        "year": 1994,
        "description": "Lion prince Simba flees his kingdom after his father is murdered by his uncle, only to return years later to claim his rightful throne.",
        "genres": ["Animation", "Adventure", "Drama"],
    },
    {
        "title": "Toy Story",
        "year": 1995,
        "description": "A cowboy doll is profoundly threatened and jealous when a new spaceman figure supplants him as top toy in a boy's room.",
        "genres": ["Animation", "Adventure", "Comedy"],
    },
    {
        "title": "The Departed",
        "year": 2006,
        "description": "An undercover cop and a mole in the police force try to identify each other while infiltrating an Irish gang in Boston.",
        "genres": ["Crime", "Drama", "Thriller"],
    },
    {
        "title": "No Country for Old Men",
        "year": 2007,
        "description": "Violence and mayhem ensue after a hunter stumbles upon a drug deal gone wrong and more than two million dollars in cash near the Rio Grande.",
        "genres": ["Crime", "Drama", "Thriller", "Western"],
    },
    {
        "title": "Mad Max: Fury Road",
        "year": 2015,
        "description": "In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler in search for her homeland with the aid of a group of female prisoners.",
        "genres": ["Action", "Adventure", "Sci-Fi", "Thriller"],
    },
    {
        "title": "Get Out",
        "year": 2017,
        "description": "A young African-American visits his white girlfriend's parents for the weekend, where his uneasiness about their reception gradually grows.",
        "genres": ["Horror", "Mystery", "Thriller"],
    },
    {
        "title": "Parasite",
        "year": 2019,
        "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
        "genres": ["Comedy", "Drama", "Thriller"],
    },
    {
        "title": "Whiplash",
        "year": 2014,
        "description": "A promising young drummer enrolls at a cut-throat music conservatory where his dreams of greatness are mentored and challenged.",
        "genres": ["Drama", "Mystery"],
    },
    {
        "title": "La La Land",
        "year": 2016,
        "description": "While navigating their careers in Los Angeles, a pianist and an actress fall in love while attempting to reconcile their aspirations.",
        "genres": ["Comedy", "Drama", "Romance"],
    },
    {
        "title": "Blade Runner 2049",
        "year": 2017,
        "description": "A young blade runner's discovery of a long-buried secret leads him to track down former blade runner Rick Deckard.",
        "genres": ["Drama", "Mystery", "Sci-Fi"],
    },
    {
        "title": "Coco",
        "year": 2017,
        "description": "Aspiring musician Miguel enters the Land of the Dead to find his great-great-grandfather, a legendary singer.",
        "genres": ["Adventure", "Animation", "Comedy", "Drama", "Fantasy"],
    },
]
# fmt: on


async def seed(db: AsyncSession) -> None:
    count = (await db.execute(select(Movie))).scalars().first()
    if count is not None:
        print("Database already has movies — skipping seed.")
        return

    for data in SEED_MOVIES:
        movie = Movie(**data, genre_vector=compute_genre_vector(data["genres"]))
        db.add(movie)

    await db.commit()
    print(f"Seeded {len(SEED_MOVIES)} movies successfully.")


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Ensure tables exist before seeding
    from app.database import Base
    import app.models  # noqa: F401 — registers all models with metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
