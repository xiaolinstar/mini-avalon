from abc import ABC, abstractmethod
from typing import Dict, Type, List

from src.wechat.commands import Command, CommandType
from src.repositories.user_repository import user_repo
from src.services.game_service import game_service
from src.services.room_service import room_service

class CommandHandler(ABC):
    @abstractmethod
    def handle(self, cmd: Command) -> str:
        pass

class CreateRoomHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = room_service.create_room(cmd.user_openid)
        return f"房间创建成功！房间号: {room.room_number}\n发送 /join {room.room_number} 让朋友们加入吧。"

class JoinRoomHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room_num = cmd.args[0] if cmd.args else ""
        room_service.join_room(room_num, cmd.user_openid)
        return f"成功加入房间 {room_num}！"

class StartGameHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        room = game_service.start_game(room.room_number, cmd.user_openid)
        role_info = game_service.get_player_info(room, cmd.user_openid)
        return f"游戏开始！房间号: {room.room_number}\n\n{role_info}\n\n当前阶段: {room.game_state.phase}\n当前队长: 玩家{room.game_state.leader_idx + 1}"

class StatusHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        players = room.game_state.players
        players_count = len(players)
        reply_text = f"【房间 {room.room_number} 状态】\n- 状态: {room.status}\n- 阶段: {room.game_state.phase}\n- 玩家人数: {players_count}/10"
        
        if room.status == 'PLAYING':
            leader_name = f"玩家{room.game_state.leader_idx + 1}"
            reply_text += f"\n- 当前轮次: 第 {room.game_state.round_num} 局"
            reply_text += f"\n- 连续失败: {room.game_state.vote_track}/5"
            reply_text += f"\n- 当前队长: {leader_name}"
            
            if room.game_state.phase in ['TEAM_VOTE', 'QUEST_PERFORM']:
                team_indices = [players.index(p)+1 for p in room.game_state.current_team]
                reply_text += f"\n- 当前队伍: {team_indices}"
                
            role_info = game_service.get_player_info(room, cmd.user_openid)
            reply_text += f"\n\n{role_info}"
        return reply_text

class PickTeamHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        indices = [int(i) for i in cmd.args]
        game_service.pick_team(room.room_number, cmd.user_openid, indices)
        return f"组队成功！请全体玩家对队伍 {indices} 进行投票。\n发送 '/vote yes' 或 '/vote no'。"

class VoteHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        vote = cmd.args[0] if cmd.args else ""
        game_service.cast_vote(room.room_number, cmd.user_openid, vote)
        return f"投票成功 ({vote})！请等待其他玩家投票。"

class QuestHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        q_vote = cmd.args[0] if cmd.args else ""
        game_service.perform_quest(room.room_number, cmd.user_openid, q_vote)
        return f"任务投票成功 ({q_vote})！请等待结果发布。"

class ShootHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        room = user_repo.get_current_room(cmd.user_openid)
        if not room:
            return "你当前不在任何房间中。"
        
        target_idx = int(cmd.args[0]) if cmd.args else 0
        result_msg = game_service.shoot_player(room.room_number, cmd.user_openid, target_idx)
        return result_msg

class ProfileHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        return game_service.get_user_stats(cmd.user_openid)

class HelpHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        return ("【阿瓦隆指令帮助】\n"
                "- 建房: 创建房间\n"
                "- 加入 {房号}: 加入房间\n"
                "- /start: 开始游戏\n"
                "- /status: 状态查询\n"
                "- /profile: 个人战绩\n"
                "- /pick 1 2 3: 队长组队\n"
                "- /vote yes/no: 组队投票\n"
                "- /quest success/fail: 任务执行\n"
                "- /shoot {编号}: 刺杀梅林")

class SetNicknameHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        nickname = cmd.args[0] if cmd.args else ""
        if not nickname:
            return "请输入有效的昵称。"
        user_repo.create_or_update(cmd.user_openid, nickname=nickname)
        return f"昵称已成功设置为: {nickname}。"

class UnknownHandler(CommandHandler):
    def handle(self, cmd: Command) -> str:
        return f"收到消息: {cmd.raw_content}。发送 '帮助' 查看可用指令。"

class CommandDispatcher:
    def __init__(self):
        self._handlers: Dict[CommandType, CommandHandler] = {
            CommandType.CREATE_ROOM: CreateRoomHandler(),
            CommandType.JOIN_ROOM: JoinRoomHandler(),
            CommandType.START_GAME: StartGameHandler(),
            CommandType.SET_NICKNAME: SetNicknameHandler(),
            CommandType.STATUS: StatusHandler(),
            CommandType.PICK_TEAM: PickTeamHandler(),
            CommandType.VOTE: VoteHandler(),
            CommandType.QUEST: QuestHandler(),
            CommandType.SHOOT: ShootHandler(),
            CommandType.PROFILE: ProfileHandler(),
            CommandType.HELP: HelpHandler(),
            CommandType.UNKNOWN: UnknownHandler(),
        }

    def dispatch(self, cmd: Command) -> str:
        handler = self._handlers.get(cmd.command_type, self._handlers[CommandType.UNKNOWN])
        try:
            return handler.handle(cmd)
        except Exception as e:
            # We can log the error here if needed, but we let the caller handle it or 
            # return a user-friendly error message if we want.
            # In this refactoring, we mainly focus on the structure.
            raise e

dispatcher = CommandDispatcher()
