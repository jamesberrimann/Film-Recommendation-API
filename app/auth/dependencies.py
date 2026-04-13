from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import decode_token
from app.database import get_db
from app.models.user import User

# HTTPBearer automatically extracts the token from the Authorization header
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates the Bearer token and returns the
    associated User.  Raises 401 for missing/invalid/expired tokens.
    """
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise invalid_credentials

    # The token subject ('sub') is stored as a string to comply with JWT spec
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise invalid_credentials

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise invalid_credentials

    return user
