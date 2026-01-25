"""Models package for the Avalon game server."""

# Import all models to register them with SQLAlchemy
from . import sql_models

# Also expose the models directly
from .sql_models import User, Room, GameState, GameHistory

__all__ = ["User", "Room", "GameState", "GameHistory", "sql_models"]