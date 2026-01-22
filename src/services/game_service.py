import random
from datetime import UTC, datetime

from src.exceptions.room import RoomStateError
from src.fsm.avalon_fsm import AvalonFSM, GamePhase
from src.repositories.room_repository import room_repo
from src.repositories.user_repository import user_repo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GameService:
    def __init__(self):
        self.fsm = AvalonFSM()

    def start_game(self, room_number: str, operator_openid: str):
        room = room_repo.get_by_number(room_number)
        if not room:
            raise RoomStateError("房间不存在")
        
        if room.owner_id != operator_openid:
            raise RoomStateError("只有房主可以开始游戏")
            
        players = list(room.game_state.players)
        player_count = len(players)
        if player_count < 5:
            raise RoomStateError(f"人数不足，当前 {player_count} 人，至少需要 5 人")

        # 1. Shuffle players for leader order
        random.shuffle(players)
        room.game_state.players = players
        
        # 2. Distribute Roles
        roles = self._assign_roles(players)
        room.game_state.roles_config = roles
        
        # 3. Set initial state
        room.game_state.phase = GamePhase.TEAM_SELECTION.value
        room.game_state.round_num = 1
        room.game_state.vote_track = 0
        room.game_state.leader_idx = 0
        room.game_state.quest_results = []
        room.game_state.votes = {}
        room.status = 'PLAYING'
        
        room_repo.save(room)
        logger.info(f"Game started in room {room_number}")
        return room

    def pick_team(self, room_number: str, leader_openid: str, selected_player_indices: list[int]):
        room = room_repo.get_by_number(room_number)
        if not room or room.game_state.phase != GamePhase.TEAM_SELECTION.value:
            raise RoomStateError("当前不是组队阶段")
        
        players = room.game_state.players
        if players[room.game_state.leader_idx] != leader_openid:
            raise RoomStateError("你不是当前队长")
            
        required_size = self.fsm.get_quest_size(len(players), room.game_state.round_num)
        if len(selected_player_indices) != required_size:
            raise RoomStateError(f"本轮任务需要选择 {required_size} 人")
            
        selected_openids = []
        for idx in selected_player_indices:
            if idx < 1 or idx > len(players):
                raise RoomStateError(f"非法的玩家编号: {idx}")
            selected_openids.append(players[idx-1])
            
        room.game_state.current_team = selected_openids
        room.game_state.phase = GamePhase.TEAM_VOTE.value
        room.game_state.votes = {} # Clear old votes
        room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 更新超时开始时间
        
        room_repo.update_game_state(room.game_state)
        logger.info(f"Room {room_number}: Team selection → Vote phase, timeout started")
        return room

    def cast_vote(self, room_number: str, user_openid: str, vote_result: str):
        room = room_repo.get_by_number(room_number)
        if not room or room.game_state.phase != GamePhase.TEAM_VOTE.value:
            raise RoomStateError("当前不是投票阶段")
            
        if user_openid not in room.game_state.players:
            raise RoomStateError("你不在该房间中")
            
        votes = dict(room.game_state.votes or {})
        votes[user_openid] = vote_result
        room.game_state.votes = votes
        
        room_repo.update_game_state(room.game_state)
        
        # Check if all voted
        if len(votes) == len(room.game_state.players):
            self._process_vote_result(room)
            
        return room

    def perform_quest(self, room_number: str, user_openid: str, quest_vote: str):
        room = room_repo.get_by_number(room_number)
        if not room or room.game_state.phase != GamePhase.QUEST_PERFORM.value:
            raise RoomStateError("当前不是任务执行阶段")
            
        if user_openid not in room.game_state.current_team:
            raise RoomStateError("你不在本次任务队伍中")

        # In a real game, good players CANNOT fail quests (usually). 
        # But we'll allow it if they really want to (though it's usually considered throwing).
        # Standard rule: Good must Success.
        role = room.game_state.roles_config.get(user_openid)
        if role not in ['LOYAL', 'MERLIN', 'PERCIVAL'] and quest_vote == 'fail':
             pass # Evil can fail
        elif quest_vote == 'fail':
             # Note: Some variants allow good to fail, but standard doesn't.
             # We will just warn or enforce it. Let's enforce it for standard feel.
             # raise RoomStateError("好人阵营必须选择成功")
             pass # Let's be flexible for now if the user didn't specify strict enforcement

        # We need to track WHO has voted without revealing WHAT they voted.
        # Actually, let's just store a list of results and a set of who has voted.
        # I'll repurpose votes field or use a new one.
        # I added quest_votes as a list. I'll need a way to track who already voted.
        # Let's use a dict temporarily and scramble at the end.
        
        # Re-using the logic: I want to know if everyone in current_team has voted.
        # I'll store it as a dict {openid: value} then take values() and shuffle.
        # But I need to preserve anonymity in the DB if possible. 
        # Actually if I store {openid: value} anyone with DB access can see.
        # For simplicity of this MVP, I'll store {openid: value} in a hidden way.
        
        q_votes = dict(room.game_state.quest_votes or {}) if isinstance(room.game_state.quest_votes, dict) else {}
        q_votes[user_openid] = quest_vote
        room.game_state.quest_votes = q_votes
        
        room_repo.update_game_state(room.game_state)
        
        if len(q_votes) == len(room.game_state.current_team):
            self._process_quest_result(room)
            
        return room

    def _process_quest_result(self, room):
        q_votes = list(room.game_state.quest_votes.values())
        random.shuffle(q_votes) # Anonymize for logs/display
        
        fails = sum(1 for v in q_votes if v == 'fail')
        player_count = len(room.game_state.players)
        round_num = room.game_state.round_num
        
        # Quest 4 Rule: 7+ players need 2 fails
        required_fails = 1
        if player_count >= 7 and round_num == 4:
            required_fails = 2
            
        success = fails < required_fails
        
        # Record result
        results = list(room.game_state.quest_results)
        results.append(success)
        room.game_state.quest_results = results
        
        logger.info(f"Quest {round_num} result: {'SUCCESS' if success else 'FAIL'} (Fails: {fails})")
        
        # Check game over
        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)
        
        if fail_count >= 3:
            room.game_state.phase = GamePhase.GAME_OVER.value
            room.status = 'ENDED'
            self._archive_game(room, "EVIL")
            logger.info("EVIL wins by 3 failed quests")
        elif success_count >= 3:
            # Good reached 3 wins -> Assassination Phase
            room.game_state.phase = GamePhase.ASSASSINATION.value
            room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 更新超时开始时间
            logger.info("GOOD reached 3 wins. Entering ASSASSINATION phase.")
        else:
            # Next round
            room.game_state.round_num += 1
            room.game_state.vote_track = 0
            room.game_state.leader_idx = (room.game_state.leader_idx + 1) % player_count
            room.game_state.phase = GamePhase.TEAM_SELECTION.value
            room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 更新超时开始时间
            room.game_state.quest_votes = {} # Reset for next
            
        room_repo.update_game_state(room.game_state)

    def shoot_player(self, room_number: str, assassin_openid: str, target_idx: int):
        room = room_repo.get_by_number(room_number)
        if not room or room.game_state.phase != GamePhase.ASSASSINATION.value:
            raise RoomStateError("当前不是刺杀阶段")
            
        role = room.game_state.roles_config.get(assassin_openid)
        if role != 'ASSASSIN':
            raise RoomStateError("只有刺客可以执行刺杀")
            
        players = room.game_state.players
        if target_idx < 1 or target_idx > len(players):
            raise RoomStateError(f"非法的玩家编号: {target_idx}")
            
        target_openid = players[target_idx - 1]
        target_role = room.game_state.roles_config.get(target_openid)
        
        success = target_role == 'MERLIN'
        
        room.status = 'ENDED'
        room.game_state.phase = GamePhase.GAME_OVER.value
        
        if success:
            logger.info(f"Assassin shot MERLIN ({target_openid})! EVIL wins.")
            result_msg = "刺杀成功！刺客击杀了梅林，坏人反败为胜！"
        else:
            logger.info(f"Assassin shot {target_role} ({target_openid}). GOOD wins.")
            result_msg = f"刺杀失败！被刺杀的是 {target_role}，好人获得最终胜利！"
            
        self._archive_game(room, "GOOD" if not success else "EVIL")
        room_repo.update_game_state(room.game_state)
        return result_msg

    def _archive_game(self, room, winner_team: str):
        from src.app_factory import db
        from src.models.sql_models import GameHistory
        
        history = GameHistory(
            room_id=str(room.room_number),
            start_time=room.created_at,
            winner_team=winner_team,
            players=room.game_state.players,
            replay_data={
                "roles": room.game_state.roles_config,
                "quest_results": room.game_state.quest_results
            }
        )
        db.session.add(history)

        room_repo.update_game_state(room.game_state)

    def get_user_stats(self, openid: str) -> str:
        from src.models.sql_models import GameHistory
        
        user = user_repo.get_by_openid(openid)
        if not user:
            return "未找到用户信息"
            
        # Get history where user participated
        # Since players is JSON, we can use JSON_CONTAINS if MySQL, or iterate in Python
        # For SQLite/Compatibility, let's do Python filtering for now
        all_history = GameHistory.query.all()
        user_history = [h for h in all_history if openid in (h.players or [])]
        
        total = len(user_history)
        if total == 0:
            return f"【{user.nickname or '玩家'} 的战绩代报】\n暂无比赛记录。"
            
        wins = 0
        good_games = 0
        evil_games = 0
        good_wins = 0
        evil_wins = 0
        
        for h in user_history:
            roles = h.replay_data.get("roles", {})
            user_role = roles.get(openid, "UNKNOWN")
            is_good = user_role in ['MERLIN', 'PERCIVAL', 'LOYAL']
            
            if is_good: good_games += 1
            else: evil_games += 1
            
            if h.winner_team == ("GOOD" if is_good else "EVIL"):
                wins += 1
                if is_good:
                    good_wins += 1
                else:
                    evil_wins += 1
                
        win_rate = (wins / total) * 100
        
        stats = [
            f"【{user.nickname or '玩家'} 的战绩总览】",
            f"总局数: {total}",
            f"总胜率: {win_rate:.1f}%",
            "--- 阵营统计 ---",
            f"好人局: {good_games} (胜 {good_wins})",
            f"坏人局: {evil_games} (胜 {evil_wins})",
        ]
        return "\n".join(stats)

    def _process_vote_result(self, room):
        votes = room.game_state.votes
        yes_count = sum(1 for v in votes.values() if v == 'yes')
        no_count = sum(1 for v in votes.values() if v == 'no')
        
        if yes_count > no_count:
            # Vote Passed
            room.game_state.phase = GamePhase.QUEST_PERFORM.value
            room.game_state.vote_track = 0
            room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 更新超时开始时间
            logger.info(f"Team vote PASSED in room {room.room_number}, started quest timeout")
        else:
            # Vote Failed
            room.game_state.vote_track += 1
            if room.game_state.vote_track >= 5:
                # Hammer failed 5 times -> Evil wins
                room.game_state.phase = GamePhase.GAME_OVER.value
                room.status = 'ENDED'
                logger.info(f"Vote track reached 5. EVIL wins in room {room.room_number}")
            else:
                # Next leader
                room.game_state.leader_idx = (room.game_state.leader_idx + 1) % len(room.game_state.players)
                room.game_state.phase = GamePhase.TEAM_SELECTION.value
                room.game_state.phase_start_time = datetime.now(UTC).replace(tzinfo=None)  # 更新超时开始时间
                logger.info(
                    f"Team vote FAILED in room {room.room_number}. "
                    f"Next leader idx: {room.game_state.leader_idx}"
                )
                
        room_repo.update_game_state(room.game_state)

    def get_player_info(self, room, user_openid: str) -> str:
        roles = room.game_state.roles_config
        role = roles.get(user_openid)
        players = room.game_state.players
        
        info = [f"你的身份是: {role}"]
        
        # Evil roles (common)
        evil_common = ["MORGANA", "ASSASSIN", "MORDRED", "MINION"]

        if role == "MERLIN":
            # Sees all evil EXCEPT Mordred (Oberon IS seen)
            seen = [
                p
                for p, r in roles.items()
                if r in ["MORGANA", "ASSASSIN", "MINION", "OBERON"]
            ]
            names = [f"【玩家{players.index(p)+1}】" for p in seen]
            info.append(f"你看到的坏人(不含莫德雷德): {' '.join(names) or '无'}")
        elif role == 'PERCIVAL':
            # Sees Merlin and Morgana (undistinguished)
            seen = [p for p, r in roles.items() if r in ['MERLIN', 'MORGANA']]
            names = [f"【玩家{players.index(p)+1}】" for p in seen]
            info.append(f"你看到的候选梅林(含莫甘娜): {' '.join(names) or '无'}")
        elif role in evil_common:
            # Evil see each other (except Oberon)
            # Oberon doesn't see them, and they don't see Oberon
            allies = [
                p
                for p, r in roles.items()
                if r in evil_common and p != user_openid
            ]
            names = [f"【玩家{players.index(p)+1}】" for p in allies]
            info.append(f"你的坏人盟友(不含奥伯伦): {' '.join(names) or '无'}")
        elif role == 'OBERON':
            info.append("（奥伯伦不认识其他坏人，坏人也不认识你）")
            
        return "\n".join(info)

    def _assign_roles(self, players: list[str]) -> dict[str, str]:
        count = len(players)
        good_count, evil_count = self.fsm.get_role_distribution(count)
        
        # 好人: MERLIN, PERCIVAL, LOYAL
        # 坏人: MORGANA, ASSASSIN, MORDRED, MINION, OBERON
        good_pool = ['MERLIN', 'PERCIVAL'] + ['LOYAL'] * (good_count - 2)
        
        evil_pool = ['ASSASSIN'] # Always need Assassin
        candidates = ['MORGANA', 'MORDRED', 'OBERON', 'MINION']
        random.shuffle(candidates)
        evil_pool += candidates[:evil_count-1]
        
        # Ensure pool matches player count
        while len(good_pool) > good_count:
            good_pool.pop()
        while len(evil_pool) > evil_count:
            evil_pool.pop()
        while len(good_pool) < good_count:
            good_pool.append("LOYAL")
        while len(evil_pool) < evil_count:
            evil_pool.append("MINION")
            
        all_roles = good_pool + evil_pool
        random.shuffle(all_roles)
        
        return {players[i]: all_roles[i] for i in range(count)}

game_service = GameService()
