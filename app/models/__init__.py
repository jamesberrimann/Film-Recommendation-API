# Importing all models here ensures SQLAlchemy registers every table
# with the shared metadata, so Base.metadata.create_all() sees them all.
from app.models.user import User  # noqa: F401
from app.models.movie import Movie  # noqa: F401
from app.models.rating import Rating, UserPreference  # noqa: F401
