from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from src.app_factory import db
from src.extensions.redis_ext import redis_manager
from src.models.sql_models import GameState, Room
from src.utils.json_utils import json_dumps, json_loads
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RoomRepository:
    """
    Handles persistence for Room and GameState.
    Uses MySQL as Source of Truth and Redis as a Cache.
    Implements Cache-Aside strategy.
    """

    CACHE_TTL = 3600  # 1 hour
    CACHE_PREFIX = "cache:room:"

    def get_by_number(self, room_number: str) -> Room | None:
        cache_key = f"{self.CACHE_PREFIX}{room_number}"
        
        # 1. Try Redis Cache
        try:
            cached_data = redis_manager.client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache HIT for room {room_number}")
                cached_room = self._deserialize_room(cached_data)
                if cached_room:
                    return cached_room
        except Exception as e:
            logger.warning(f"Redis cache read failed for room {room_number}: {e}, falling back to DB")

        # 2. Try MySQL
        room = Room.query.filter_by(room_number=room_number).first()
        if room:
            # 3. Fill Cache if found (async, don't block)
            try:
                self._set_cache(room)
            except Exception as e:
                logger.warning(f"Failed to set cache for room {room_number}: {e}")
            return room
        
        return None

    def save(self, room: Room) -> None:
        """
        Saves room with optimistic locking (handled by version field).
        Then invalidates cache.
        """
        try:
            # Incremental version handled manually or via SQLAlchemy events
            if room.version is None:
                room.version = 1
            else:
                room.version += 1
            db.session.add(room)
            db.session.commit()
            
            # Invalidate Redis Cache
            try:
                redis_manager.client.delete(f"{self.CACHE_PREFIX}{room.room_number}")
                logger.debug(f"Saved room {room.room_number} (v{room.version}) and invalidated cache")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for room {room.room_number}: {e}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save room {room.room_number}: {str(e)}")
            raise

    def delete(self, room: Room) -> None:
        room_number = room.room_number
        db.session.delete(room)
        db.session.commit()
        try:
            redis_manager.client.delete(f"{self.CACHE_PREFIX}{room_number}")
            logger.debug(f"Deleted room {room_number} and invalidated cache")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for room {room_number}: {e}")

    def update_game_state(self, game_state: GameState) -> None:
        """
        Special helper for JSON fields in GameState.
        SQLAlchemy doesn't always detect internal JSON changes.
        """
        flag_modified(game_state, "current_team")
        flag_modified(game_state, "quest_results")
        flag_modified(game_state, "roles_config")
        flag_modified(game_state, "players")
        flag_modified(game_state, "votes")
        flag_modified(game_state, "quest_votes")
        db.session.commit()
        
        # Invalidate associated room cache
        if game_state.room:
            try:
                redis_manager.client.delete(f"{self.CACHE_PREFIX}{game_state.room.room_number}")
                logger.debug(f"Invalidated cache for room {game_state.room.room_number}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")

    def _serialize_room(self, room: Room) -> dict[str, Any]:
        """Serialize Room object to dict for Redis storage."""
        room_data = {
            "id": room.id,
            "room_number": room.room_number,
            "owner_id": room.owner_id,
            "status": room.status,
            "created_at": room.created_at.isoformat() if room.created_at else None,
            "updated_at": room.updated_at.isoformat() if room.updated_at else None,
            "version": room.version,
        }
        
        # Serialize GameState if exists
        if room.game_state:
            room_data["game_state"] = {
                "id": room.game_state.id,
                "room_id": room.game_state.room_id,
                "phase": room.game_state.phase,
                "round_num": room.game_state.round_num,
                "vote_track": room.game_state.vote_track,
                "leader_idx": room.game_state.leader_idx,
                "current_team": room.game_state.current_team,
                "quest_results": room.game_state.quest_results,
                "roles_config": room.game_state.roles_config,
                "players": room.game_state.players,
                "votes": room.game_state.votes,
                "quest_votes": room.game_state.quest_votes,
            }
        
        return room_data

    def _deserialize_room(self, cached_data: str) -> Room | None:
        """Deserialize cached JSON dict back to Room object."""
        try:
            from datetime import datetime
            
            data = json_loads(cached_data)
            if not data:
                return None
            
            # Create Room object without SQLAlchemy session
            room = Room(
                id=data.get("id"),
                room_number=data.get("room_number"),
                owner_id=data.get("owner_id"),
                status=data.get("status"),
                version=data.get("version", 1),
            )
            
            # Parse datetime fields
            if data.get("created_at"):
                room.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                room.updated_at = datetime.fromisoformat(data["updated_at"])
            
            # Create GameState if exists
            game_state_data = data.get("game_state")
            if game_state_data:
                game_state = GameState(
                    id=game_state_data.get("id"),
                    room_id=game_state_data.get("room_id"),
                    phase=game_state_data.get("phase"),
                    round_num=game_state_data.get("round_num", 1),
                    vote_track=game_state_data.get("vote_track", 0),
                    leader_idx=game_state_data.get("leader_idx", 0),
                    current_team=game_state_data.get("current_team", []),
                    quest_results=game_state_data.get("quest_results", []),
                    roles_config=game_state_data.get("roles_config", {}),
                    players=game_state_data.get("players", []),
                    votes=game_state_data.get("votes", {}),
                    quest_votes=game_state_data.get("quest_votes", []),
                )
                room.game_state = game_state
            
            return room
        except Exception as e:
            logger.error(f"Failed to deserialize room from cache: {e}")
            return None

    def _set_cache(self, room: Room) -> None:
        """Set room in Redis cache."""
        cache_key = f"{self.CACHE_PREFIX}{room.room_number}"
        room_data = self._serialize_room(room)
        redis_manager.client.setex(
            cache_key,
            self.CACHE_TTL,
            json_dumps(room_data)
        )
        logger.debug(f"Cache SET for room {room.room_number}")

# Singleton
room_repo = RoomRepository()
