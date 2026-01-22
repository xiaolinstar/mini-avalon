import random
import string
from datetime import UTC

from src.app_factory import db
from src.exceptions.room import RoomFullError, RoomNotFoundError, RoomStateError
from src.models.sql_models import GameState, Room, User
from src.repositories.room_repository import room_repo
from src.repositories.user_repository import user_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RoomService:
    def create_room(self, owner_openid: str) -> Room:
        # 1. Generate unique 4-digit room number
        room_number = self._generate_room_number()
        
        # 2. Create Room object
        room = Room(
            room_number=room_number,
            owner_id=owner_openid,
            status='WAITING'
        )
        
        # 3. Initialize GameState
        game_state = GameState(
            phase='WAITING',
            players=[owner_openid], # Owner is first player
            quest_results=[],
            current_team=[]
        )
        room.game_state = game_state
        
        # 4. Set user's current room
        owner = user_repo.get_by_openid(owner_openid)
        if owner:
            owner.current_room_id = room.id
        
        room_repo.save(room)
        logger.info(f"Room {room_number} created by {owner_openid}")
        return room

    def join_room(self, room_number: str, user_openid: str) -> Room:
        room = room_repo.get_by_number(room_number)
        if not room:
            raise RoomNotFoundError(room_number)
        
        if room.status != 'WAITING':
            raise RoomStateError("游戏已经开始，无法加入")
            
        # Check if user already in room
        players = list(room.game_state.players or [])
        if user_openid in players:
            return room # Already in
            
        if len(players) >= 10:
            raise RoomFullError(room_number)
            
        # Update players list
        players.append(user_openid)
        room.game_state.players = players
        
        # Update user's current room
        user = user_repo.get_by_openid(user_openid)
        if user:
            user.current_room_id = room.id
            
        room_repo.update_game_state(room.game_state)
        
        logger.info(f"User {user_openid} joined room {room_number}")
        return room

    def _generate_room_number(self) -> str:
        # Simple random 4-char digit string
        for _ in range(10): # Try 10 times to find unique
            num = ''.join(random.choices(string.digits, k=4))
            if not room_repo.get_by_number(num):
                return num
        return str(random.randint(1000, 9999)) # Fallback

    def cleanup_stale_rooms(self, hours: int = 2):
        from datetime import datetime, timedelta
        threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
        
        stale_rooms = Room.query.filter(Room.updated_at < threshold).all()
        count = len(stale_rooms)
        for room in stale_rooms:
            # Clear user current_room_id
            User.query.filter_by(current_room_id=room.id).update({"current_room_id": None})
            room_repo.delete(room)
            
        db.session.commit()
        logger.info(f"Cleaned up {count} stale rooms inactive since {threshold}")
        return count

room_service = RoomService()
