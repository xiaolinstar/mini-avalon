"""定时清理服务 - 自动清理过期房间"""
from datetime import UTC, datetime, timedelta

from src.models.sql_models import Room, User
from src.repositories.room_repository import room_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CleanupService:
    """房间清理服务，根据不同状态和活跃度清理过期房间"""

    # 清理策略配置（小时）
    CLEANUP_POLICIES = {
        'ENDED': 168,           # 已结束房间：7天后清理 (7 * 24 = 168小时)
        'WAITING_EMPTY': 1,     # 等待中无玩家：1小时后清理
        'WAITING_STALLED': 24,  # 等待中有玩家但长时间未开始：24小时后清理
        'PLAYING_STALLED': 72,  # 游戏中异常长时间：3天后清理 (可能是卡住的房间)
        'ORPHANED': 0,          # 孤儿房间（无玩家）：立即清理
    }

    def cleanup_expired_rooms(self) -> dict[str, int]:
        """
        清理所有过期房间，返回清理统计
        Returns:
            Dict[str, int]: 按状态分类的清理数量
        """
        stats = {
            'total': 0,
            'ENDED': 0,
            'WAITING': 0,
            'PLAYING': 0,
            'ORPHANED': 0,
        }

        try:
            # 1. 清理已结束超过7天的房间
            ended_count = self._cleanup_ended_rooms()
            stats['ENDED'] = ended_count
            stats['total'] += ended_count

            # 2. 清理等待中的房间（无玩家或长时间未开始）
            waiting_count = self._cleanup_waiting_rooms()
            stats['WAITING'] = waiting_count
            stats['total'] += waiting_count

            # 3. 清理异常的游戏中房间（超过3天未更新）
            playing_count = self._cleanup_stalled_playing_rooms()
            stats['PLAYING'] = playing_count
            stats['total'] += playing_count

            # 4. 清理孤儿房间（无玩家关联的房间）
            orphaned_count = self._cleanup_orphaned_rooms()
            stats['ORPHANED'] = orphaned_count
            stats['total'] += orphaned_count

            logger.info(f"Cleanup completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise

    def _cleanup_ended_rooms(self) -> int:
        """清理已结束超过7天的房间"""
        threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=self.CLEANUP_POLICIES['ENDED'])
        rooms = Room.query.filter(
            Room.status == 'ENDED',
            Room.updated_at < threshold
        ).all()

        count = 0
        for room in rooms:
            if self._delete_room_safely(room):
                count += 1

        if count > 0:
            logger.info(f"Cleaned {count} ENDED rooms (updated before {threshold})")

        return count

    def _cleanup_waiting_rooms(self) -> int:
        """清理等待状态的房间（无玩家或长时间未开始）"""
        count = 0
        now = datetime.now(UTC).replace(tzinfo=None)

        # 获取所有等待中的房间
        rooms = Room.query.filter_by(status='WAITING').all()

        for room in rooms:
            # 检查是否有玩家
            players = room.game_state.players if room.game_state else []

            if not players or len(players) == 0:
                # 无玩家房间：1小时后清理
                threshold = now - timedelta(hours=self.CLEANUP_POLICIES['WAITING_EMPTY'])
                if room.updated_at < threshold:
                    if self._delete_room_safely(room):
                        count += 1
                        logger.debug(f"Cleaned empty WAITING room {room.room_number}")
            else:
                # 有玩家但长时间未开始：24小时后清理
                threshold = now - timedelta(hours=self.CLEANUP_POLICIES['WAITING_STALLED'])
                if room.updated_at < threshold:
                    if self._delete_room_safely(room):
                        count += 1
                        logger.debug(f"Cleaned stalled WAITING room {room.room_number} with {len(players)} players")

        if count > 0:
            logger.info(f"Cleaned {count} WAITING rooms")

        return count

    def _cleanup_stalled_playing_rooms(self) -> int:
        """清理异常长时间未更新的游戏中房间"""
        threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=self.CLEANUP_POLICIES['PLAYING_STALLED'])
        rooms = Room.query.filter(
            Room.status == 'PLAYING',
            Room.updated_at < threshold
        ).all()

        count = 0
        for room in rooms:
            # 确保房间没有活动（没有超时正在处理）
            if room.game_state and room.game_state.phase:
                if self._delete_room_safely(room):
                    count += 1
                    logger.warning(
                        f"Cleaned stalled PLAYING room {room.room_number} "
                        f"(phase: {room.game_state.phase}, last_update: {room.updated_at})"
                    )

        if count > 0:
            logger.info(f"Cleaned {count} stalled PLAYING rooms")

        return count

    def _cleanup_orphaned_rooms(self) -> int:
        """清理孤儿房间（没有玩家关联的房间）"""
        # 查找所有房间
        all_rooms = Room.query.all()
        count = 0

        for room in all_rooms:
            # 检查是否有玩家在这个房间
            player_count = User.query.filter_by(current_room_id=room.id).count()

            # 如果没有玩家，且不是刚刚创建的（避免误删）
            if player_count == 0:
                threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
                if room.updated_at < threshold:
                    if self._delete_room_safely(room):
                        count += 1
                        logger.debug(f"Cleaned orphaned room {room.room_number}")

        if count > 0:
            logger.info(f"Cleaned {count} orphaned rooms")

        return count

    def _delete_room_safely(self, room: Room) -> bool:
        """安全删除房间，处理外键关联"""
        try:
            # 1. 清理关联的用户的 current_room_id
            User.query.filter_by(current_room_id=room.id).update({"current_room_id": None})

            # 2. 删除房间（cascade会删除关联的game_state）
            room_repo.delete(room)

            logger.debug(f"Successfully deleted room {room.room_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete room {room.room_number}: {e}")
            return False

    def get_room_statistics(self) -> dict[str, int]:
        """获取当前房间统计信息"""
        try:
            stats = {
                'total': 0,
                'WAITING': 0,
                'PLAYING': 0,
                'ENDED': 0,
                'orphaned': 0,
            }

            # 统计各状态房间数
            stats['total'] = Room.query.count()
            stats['WAITING'] = Room.query.filter_by(status='WAITING').count()
            stats['PLAYING'] = Room.query.filter_by(status='PLAYING').count()
            stats['ENDED'] = Room.query.filter_by(status='ENDED').count()

            # 统计孤儿房间
            orphaned_count = 0
            for room in Room.query.all():
                player_count = User.query.filter_by(current_room_id=room.id).count()
                if player_count == 0:
                    orphaned_count += 1
            stats['orphaned'] = orphaned_count

            logger.info(f"Room statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting room statistics: {e}")
            return {}


# Singleton
cleanup_service = CleanupService()
