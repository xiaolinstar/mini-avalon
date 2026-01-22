from datetime import UTC

import pytest

from src.exceptions.room import RoomFullError, RoomNotFoundError
from src.repositories.user_repository import user_repo
from src.services.room_service import room_service


def test_room_lifecycle(app):
    with app.app_context():
        # Create
        user_repo.create_or_update("owner", nickname="Owner")
        room = room_service.create_room("owner")
        room_number = room.room_number
        assert len(room.game_state.players) == 1
        
        # Join
        user_repo.create_or_update("player2", nickname="P2")
        room_service.join_room(room_number, "player2")
        assert len(room.game_state.players) == 2
        
        # Join already in room (should not fail, but idempotent)
        room_service.join_room(room_number, "player2")
        assert len(room.game_state.players) == 2

def test_join_non_existent_room(app):
    with app.app_context():
        with pytest.raises(RoomNotFoundError):
            room_service.join_room("9999", "user1")

def test_join_full_room(app):
    with app.app_context():
        room = room_service.create_room("owner")
        room_number = room.room_number
        # Mock 10 players
        room.game_state.players = [f"u{i}" for i in range(10)]
        from src.repositories.room_repository import room_repo
        room_repo.update_game_state(room.game_state)
        
        with pytest.raises(RoomFullError):
            room_service.join_room(room_number, "extra")

def test_cleanup_stale_rooms(app):
    with app.app_context():
        from datetime import datetime, timedelta

        from src.app_factory import db
        from src.models.sql_models import Room
        
        # Create a stale room
        user_repo.create_or_update("u1")
        room = room_service.create_room("u1")
        room.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3)
        db.session.commit()
        
        count = room_service.cleanup_stale_rooms(hours=2)
        assert count == 1
        assert Room.query.filter_by(room_number=room.room_number).first() is None
