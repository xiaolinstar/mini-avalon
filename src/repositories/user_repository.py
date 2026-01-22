from typing import Optional

from src.app_factory import db
from src.models.sql_models import User
from src.utils.logger import get_logger

logger = get_logger(__name__)

class UserRepository:
    """
    Repository for User management.
    Source of Truth: MySQL.
    Cache: Redis.
    """
    CACHE_PREFIX = "cache:user:"
    CACHE_TTL = 86400  # 24 hours

    def get_by_openid(self, openid: str) -> User | None:
        # Implementation of cache-aside for User
        user = User.query.filter_by(openid=openid).first()
        return user

    def get_current_room(self, openid: str) -> Optional['Room']:
        user = self.get_by_openid(openid)
        if user and user.current_room_id:
            from src.models.sql_models import Room
            return Room.query.get(user.current_room_id)
        return None


    def create_or_update(self, openid: str, nickname: str | None = None) -> User:
        user = self.get_by_openid(openid)
        if not user:
            user = User(openid=openid, nickname=nickname)
            db.session.add(user)
        else:
            if nickname:
                user.nickname = nickname
        
        try:
            db.session.commit()
            # Invalidate cache if implemented for users
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving user {openid}: {e}")
            raise

user_repo = UserRepository()
