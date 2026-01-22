"""
游戏超时处理服务
定期检查游戏状态，当投票/任务阶段超时时自动随机执行
"""
import random
from datetime import UTC, datetime

from src.models.sql_models import Room
from src.repositories.room_repository import room_repo
from src.services.game_service import game_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TimeoutService:
    """
    游戏超时检测和处理服务
    """
    
    def __init__(self):
        self.check_interval = 10  # 每 10 秒检查一次
        
    def check_and_process_timeouts(self):
        """
        检查并处理所有超时的游戏
        """
        try:
            # 查询所有正在进行的游戏
            active_rooms = Room.query.filter_by(status='PLAYING').all()
            
            processed_count = 0
            
            for room in active_rooms:
                if self._check_room_timeout(room):
                    processed_count += 1
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} timed out rooms")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error checking timeouts: {e}", exc_info=True)
            return 0
    
    def _check_room_timeout(self, room: Room) -> bool:
        """
        检查单个房间是否超时
        """
        try:
            gs = room.game_state
            if not gs or not gs.phase_start_time:
                return False
            
            # 计算是否超时
            timeout_seconds = gs.timeout_seconds or 60
            elapsed = (datetime.now(UTC).replace(tzinfo=None) - gs.phase_start_time).total_seconds()
            
            if elapsed < timeout_seconds:
                return False
            
            # 超时处理
            logger.warning(
                f"Room {room.room_number} timeout in phase {gs.phase} "
                f"(elapsed: {elapsed:.1f}s, timeout: {timeout_seconds}s)"
            )
            
            if gs.phase == 'TEAM_VOTE':
                return self._handle_vote_timeout(room)
            elif gs.phase == 'QUEST_PERFORM':
                return self._handle_quest_timeout(room)
            else:
                logger.debug(f"Phase {gs.phase} doesn't require timeout handling")
                return False
                
        except Exception as e:
            logger.error(f"Error checking timeout for room {room.room_number}: {e}")
            return False
    
    def _handle_vote_timeout(self, room: Room) -> bool:
        """
        处理投票超时：自动为未投票的玩家随机投票
        """
        try:
            gs = room.game_state
            players = gs.players
            votes = dict(gs.votes or {})

            # 找出未投票的玩家
            not_voted = [p for p in players if p not in votes]

            if not not_voted:
                # 所有人都已投票，正常处理
                return False

            # 为未投票的玩家随机投票
            for player in not_voted:
                # 好人倾向同意（70% yes），坏人倾向反对（60% no）
                role = gs.roles_config.get(player)
                if role in ['MERLIN', 'PERCIVAL', 'LOYAL']:
                    vote = 'yes' if random.random() < 0.7 else 'no'
                else:
                    vote = 'no' if random.random() < 0.6 else 'yes'

                votes[player] = vote
                # 使用列表的 index 方法，而不是可能返回 Mock 的对象方法
                try:
                    player_num = players.index(player) + 1
                except (ValueError, AttributeError):
                    player_num = 1
                logger.info(
                    f"Auto-vote for player {player_num} "
                    f"({role}): {vote} (timeout)"
                )

            gs.votes = votes
            gs.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 重置时间

            # 保存并处理投票结果
            room_repo.update_game_state(gs)

            # 触发投票结果处理
            game_service._process_vote_result(room)

            return True

        except Exception as e:
            logger.error(f"Error handling vote timeout for room {room.room_number}: {e}")
            return False
    
    def _handle_quest_timeout(self, room: Room) -> bool:
        """
        处理任务超时：自动为未执行的玩家随机执行
        """
        try:
            gs = room.game_state
            current_team = gs.current_team
            
            if not current_team:
                return False
            
            quest_votes = dict(gs.quest_votes or {}) if isinstance(gs.quest_votes, dict) else {}
            
            # 找出未执行的玩家
            not_voted = [p for p in current_team if p not in quest_votes]
            
            if not not_voted:
                # 所有人都已执行，正常处理
                return False
            
            # 为未执行的玩家随机执行
            for player in not_voted:
                role = gs.roles_config.get(player)

                # 好人必须成功，坏人可以失败（40% 概率失败）
                if role in ['MERLIN', 'PERCIVAL', 'LOYAL']:
                    vote = 'success'
                else:
                    vote = 'fail' if random.random() < 0.4 else 'success'

                quest_votes[player] = vote
                players = gs.players
                # 使用列表的 index 方法，而不是可能返回 Mock 的对象方法
                try:
                    player_num = players.index(player) + 1
                except (ValueError, AttributeError):
                    player_num = 1
                logger.info(
                    f"Auto-quest for player {player_num} "
                    f"({role}): {vote} (timeout)"
                )

            gs.quest_votes = quest_votes
            gs.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 重置时间

            # 保存并处理任务结果
            room_repo.update_game_state(gs)

            # 触发任务结果处理
            game_service._process_quest_result(room)

            return True
            
        except Exception as e:
            logger.error(f"Error handling quest timeout for room {room.room_number}: {e}")
            return False
    
    def update_phase_start_time(self, room_number: str):
        """
        更新房间阶段开始时间
        在阶段切换时调用
        """
        try:
            room = room_repo.get_by_number(room_number)
            if room and room.game_state:
                room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)
                room_repo.update_game_state(room.game_state)
                logger.debug(f"Updated phase start time for room {room_number}")
        except Exception as e:
            logger.error(f"Error updating phase start time: {e}")


# 单例
timeout_service = TimeoutService()
