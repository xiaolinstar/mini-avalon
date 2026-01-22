from datetime import UTC, datetime, timedelta

from src.app_factory import db
from src.models.sql_models import GameState, Room
from src.services.cleanup_service import cleanup_service


def test_cleanup_ended_rooms(app):
    with app.app_context():
        # Create a room that ended more than 7 days ago
        room = Room(room_number="1111", owner_id="user1", status='ENDED')
        db.session.add(room)
        db.session.commit()
        
        # Manually set updated_at (default is now)
        room.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
        db.session.commit()
        
        count = cleanup_service._cleanup_ended_rooms()
        assert count == 1
        assert Room.query.filter_by(room_number="1111").first() is None

def test_cleanup_waiting_rooms_empty(app):
    with app.app_context():
        # Create a waiting room with no players, updated 2 hours ago
        room = Room(room_number="2222", owner_id="user2", status='WAITING')
        gs = GameState(room=room, players=[])
        db.session.add(room)
        db.session.add(gs)
        db.session.commit()
        
        room.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
        db.session.commit()
        
        count = cleanup_service._cleanup_waiting_rooms()
        assert count == 1
        assert Room.query.filter_by(room_number="2222").first() is None

def test_cleanup_stalled_playing_rooms(app):
    with app.app_context():
        # Create a playing room stalled for 4 days
        room = Room(room_number="3333", owner_id="user3", status='PLAYING')
        gs = GameState(room=room, phase='TEAM_VOTE')
        db.session.add(room)
        db.session.add(gs)
        db.session.commit()
        
        room.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=4)
        db.session.commit()
        
        count = cleanup_service._cleanup_stalled_playing_rooms()
        assert count == 1
        assert Room.query.filter_by(room_number="3333").first() is None

def test_cleanup_orphaned_rooms(app):
    with app.app_context():
        # Create a room with no users associated (orphaned)
        room = Room(room_number="4444", owner_id="user4", status='WAITING')
        db.session.add(room)
        db.session.commit()
        
        # Set updated_at to more than 5 minutes ago
        room.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        db.session.commit()
        
        # Ensure no user has current_room_id = room.id
        count = cleanup_service._cleanup_orphaned_rooms()
        assert count == 1
        assert Room.query.filter_by(room_number="4444").first() is None

def test_cleanup_all(app):
    with app.app_context():
        # Just test the main entry point
        stats = cleanup_service.cleanup_expired_rooms()
        assert isinstance(stats, dict)
        assert 'total' in stats
