"""
Integration tests covering the full request/response cycle via the ASGI client.

Tests are grouped by feature area and designed to be run in any order
(each fixture provides an isolated session).
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, username: str = "testuser") -> str:
    """Register a user and return their Bearer token."""
    await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "securepass1"},
    )
    resp = await client.post(
        "/auth/login",
        json={"username": username, "password": "securepass1"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ────────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "hashed_password" not in body


async def test_register_duplicate_username(client: AsyncClient):
    payload = {"username": "bob", "email": "bob@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


async def test_login_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"username": "carol", "password": "password123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"username": "dave", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


# ── Movie tests ───────────────────────────────────────────────────────────────

async def test_add_movie_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/movies",
        json={"title": "Test Film", "year": 2020, "genres": ["Drama"]},
    )
    assert resp.status_code == 403  # No Bearer token


async def test_add_and_get_movie(client: AsyncClient):
    token = await register_and_login(client, "movieuser")
    resp = await client.post(
        "/movies",
        json={
            "title": "The Test Movie",
            "year": 2023,
            "description": "A test film.",
            "genres": ["Action", "Drama"],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    movie_id = resp.json()["id"]

    get_resp = await client.get(f"/movies/{movie_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "The Test Movie"


async def test_get_movie_not_found(client: AsyncClient):
    resp = await client.get("/movies/999999")
    assert resp.status_code == 404


async def test_invalid_genre_rejected(client: AsyncClient):
    token = await register_and_login(client, "genreuser")
    resp = await client.post(
        "/movies",
        json={"title": "Bad Genre Film", "year": 2020, "genres": ["NotAGenre"]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


async def test_search_by_title(client: AsyncClient):
    token = await register_and_login(client, "searchuser")
    await client.post(
        "/movies",
        json={"title": "Searchable Film", "year": 2021, "genres": ["Comedy"]},
        headers=auth_headers(token),
    )
    resp = await client.get("/movies/search", params={"q": "searchable"})
    assert resp.status_code == 200
    titles = [m["title"] for m in resp.json()]
    assert any("Searchable" in t for t in titles)


async def test_search_by_genre(client: AsyncClient):
    token = await register_and_login(client, "genresearch")
    await client.post(
        "/movies",
        json={"title": "Horror Film", "year": 2022, "genres": ["Horror"]},
        headers=auth_headers(token),
    )
    resp = await client.get("/movies/search", params={"genre": "Horror"})
    assert resp.status_code == 200
    assert all("Horror" in m["genres"] for m in resp.json())


# ── Rating tests ──────────────────────────────────────────────────────────────

async def test_rate_movie(client: AsyncClient):
    token = await register_and_login(client, "ratinguser")
    add = await client.post(
        "/movies",
        json={"title": "Rateable Film", "year": 2020, "genres": ["Drama"]},
        headers=auth_headers(token),
    )
    movie_id = add.json()["id"]

    resp = await client.post(
        f"/movies/{movie_id}/rate",
        json={"rating": 5},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 5


async def test_re_rating_updates_score(client: AsyncClient):
    token = await register_and_login(client, "rerateuser")
    add = await client.post(
        "/movies",
        json={"title": "Re-Rate Film", "year": 2020, "genres": ["Drama"]},
        headers=auth_headers(token),
    )
    movie_id = add.json()["id"]

    await client.post(f"/movies/{movie_id}/rate", json={"rating": 3}, headers=auth_headers(token))
    resp = await client.post(
        f"/movies/{movie_id}/rate",
        json={"rating": 5},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 5


async def test_rating_out_of_range_rejected(client: AsyncClient):
    token = await register_and_login(client, "badrating")
    add = await client.post(
        "/movies",
        json={"title": "Range Test Film", "year": 2020, "genres": ["Drama"]},
        headers=auth_headers(token),
    )
    movie_id = add.json()["id"]
    resp = await client.post(
        f"/movies/{movie_id}/rate",
        json={"rating": 6},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


async def test_my_ratings(client: AsyncClient):
    token = await register_and_login(client, "myratingsuser")
    add = await client.post(
        "/movies",
        json={"title": "My Ratings Film", "year": 2020, "genres": ["Drama"]},
        headers=auth_headers(token),
    )
    movie_id = add.json()["id"]
    await client.post(f"/movies/{movie_id}/rate", json={"rating": 4}, headers=auth_headers(token))

    resp = await client.get("/users/me/ratings", headers=auth_headers(token))
    assert resp.status_code == 200
    assert any(r["movie_id"] == movie_id for r in resp.json())


# ── Recommendation tests ──────────────────────────────────────────────────────

async def test_cold_start_recommendations(client: AsyncClient):
    """A user with no ratings should get the global top-rated movies."""
    token = await register_and_login(client, "colduser")
    resp = await client.get("/recommendations", headers=auth_headers(token))
    assert resp.status_code == 200
    # May be empty if no rated movies exist yet — just assert shape
    for item in resp.json():
        assert "movie" in item
        assert "similarity_score" in item


async def test_recommendations_after_rating(client: AsyncClient):
    """After rating an Action film, Action films should score highly."""
    token = await register_and_login(client, "recuser")
    # Add two films with distinct genres
    action = (
        await client.post(
            "/movies",
            json={"title": "Rec Action Film", "year": 2020, "genres": ["Action"]},
            headers=auth_headers(token),
        )
    ).json()
    drama = (
        await client.post(
            "/movies",
            json={"title": "Rec Drama Film", "year": 2020, "genres": ["Drama"]},
            headers=auth_headers(token),
        )
    ).json()

    # Rate the Action film 5 stars
    await client.post(
        f"/movies/{action['id']}/rate",
        json={"rating": 5},
        headers=auth_headers(token),
    )

    resp = await client.get("/recommendations", headers=auth_headers(token))
    assert resp.status_code == 200
    recs = resp.json()

    # The rated movie must not appear in recommendations
    rec_ids = [r["movie"]["id"] for r in recs]
    assert action["id"] not in rec_ids


# ── User preference tests ─────────────────────────────────────────────────────

async def test_preferences_empty_before_ratings(client: AsyncClient):
    token = await register_and_login(client, "prefuser1")
    resp = await client.get("/users/me/preferences", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["preferences"] == {}


async def test_preferences_populated_after_rating(client: AsyncClient):
    token = await register_and_login(client, "prefuser2")
    add = await client.post(
        "/movies",
        json={"title": "Pref Test Film", "year": 2020, "genres": ["Action", "Thriller"]},
        headers=auth_headers(token),
    )
    movie_id = add.json()["id"]
    await client.post(f"/movies/{movie_id}/rate", json={"rating": 5}, headers=auth_headers(token))

    resp = await client.get("/users/me/preferences", headers=auth_headers(token))
    assert resp.status_code == 200
    prefs = resp.json()["preferences"]
    assert "Action" in prefs
    assert "Thriller" in prefs


# ── Health check ──────────────────────────────────────────────────────────────

async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
