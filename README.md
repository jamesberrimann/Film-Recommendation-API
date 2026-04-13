# Film Recommendation API

A REST API that gives you personalised film recommendations based on what you've rated. Built with FastAPI and PostgreSQL, it runs entirely in Docker so there's nothing to install locally beyond Docker itself.

## What it does

You register an account, log in, and start rating films from the catalogue. Every time you rate something, the API updates a taste profile for you — a vector of genre preferences weighted by how highly you rated each film. When you ask for recommendations, it compares that profile against every film you haven't seen yet using cosine similarity and returns the closest matches.

If you haven't rated anything yet it falls back to showing the highest rated films globally, so new users always get something useful.

## How to run it

You'll need Docker installed. Clone the repo, then run:

```
docker compose up --build
```

Once it's up, seed the database with 25 films:

```
docker compose run --rm api python scripts/seed_db.py
```

The app is at http://localhost:8000 and a database browser (Adminer) is at http://localhost:8080.

## The stack

The API is Python with FastAPI and SQLAlchemy talking to a PostgreSQL database over an async connection. Passwords are hashed with bcrypt and authentication uses JWT tokens. The recommendation logic uses numpy for the cosine similarity calculation. Everything is containerised with Docker Compose, including a lightweight web UI for browsing the database.

## Project structure

The code is split into models (database tables), schemas (what the API accepts and returns), routes (the endpoints), and services (the business logic). The recommendation engine lives in `app/services/recommendation.py` and the JWT handling is in `app/auth/`.
