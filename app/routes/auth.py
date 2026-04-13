from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    # Check uniqueness before hashing (cheap query first)
    existing = (
        await db.execute(
            select(User).where(
                (User.username == body.username) | (User.email == body.email)
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()

    # Deliberate vague error — don't reveal whether the username exists
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
