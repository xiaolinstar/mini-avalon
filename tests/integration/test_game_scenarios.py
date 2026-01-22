from src.fsm.avalon_fsm import GamePhase
from src.repositories.user_repository import user_repo
from src.services.game_service import game_service
from src.services.room_service import room_service


def setup_users(n):
    users = [f"user_{i}" for i in range(1, n + 1)]
    for u in users:
        user_repo.create_or_update(u, nickname=f"Player_{u[-1]}")
    return users

def test_evil_wins_by_3_fails(app):
    with app.app_context():
        users = setup_users(5)
        room = room_service.create_room(users[0])
        room_number = room.room_number
        for u in users[1:]:
            room_service.join_room(room_number, u)
        
        game_service.start_game(room_number, users[0])
        
        # Round 1, 2, 3 - All failed by evil
        for r in range(1, 4):
            leader_openid = room.game_state.players[room.game_state.leader_idx]
            # Pick 2 people (Quest 1, 3 for 5p is 2; Quest 2 is 3)
            size = game_service.fsm.get_quest_size(5, r)
            game_service.pick_team(room_number, leader_openid, list(range(1, size + 1)))
            
            for u in users:
                game_service.cast_vote(room_number, u, 'yes')
            
            team = room.game_state.current_team
            # One fail is enough
            game_service.perform_quest(room_number, team[0], 'fail')
            for member in team[1:]:
                game_service.perform_quest(room_number, member, 'success')
        
        assert room.game_state.phase == GamePhase.GAME_OVER.value
        assert sum(1 for res in room.game_state.quest_results if res is False) == 3
        assert room.status == 'ENDED'

def test_evil_wins_by_assassination(app):
    with app.app_context():
        users = setup_users(5)
        room = room_service.create_room(users[0])
        room_number = room.room_number
        for u in users[1:]:
            room_service.join_room(room_number, u)
        
        game_service.start_game(room_number, users[0])
        roles = room.game_state.roles_config
        merlin_openid = next(p for p, r in roles.items() if r == 'MERLIN')
        assassin_openid = next(p for p, r in roles.items() if r == 'ASSASSIN')
        merlin_idx = room.game_state.players.index(merlin_openid) + 1
        
        # Good wins 3 quests
        for r in range(1, 4):
            leader_openid = room.game_state.players[room.game_state.leader_idx]
            size = game_service.fsm.get_quest_size(5, r)
            game_service.pick_team(room_number, leader_openid, list(range(1, size + 1)))
            for u in users:
                game_service.cast_vote(room_number, u, 'yes')
            for member in room.game_state.current_team:
                game_service.perform_quest(room_number, member, 'success')
        
        assert room.game_state.phase == GamePhase.ASSASSINATION.value
        
        # Assassin shoots Merlin
        msg = game_service.shoot_player(room_number, assassin_openid, merlin_idx)
        assert "刺杀成功" in msg
        assert room.game_state.phase == GamePhase.GAME_OVER.value
        assert room.status == 'ENDED'

def test_vote_track_reaches_5(app):
    with app.app_context():
        users = setup_users(5)
        room = room_service.create_room(users[0])
        room_number = room.room_number
        for u in users[1:]:
            room_service.join_room(room_number, u)
        game_service.start_game(room_number, users[0])
        
        # Vote track 0 -> 5
        for _ in range(5):
            leader_openid = room.game_state.players[room.game_state.leader_idx]
            game_service.pick_team(room_number, leader_openid, [1, 2])
            for u in users:
                game_service.cast_vote(room_number, u, 'no')
        
        assert room.game_state.phase == GamePhase.GAME_OVER.value
        assert room.status == 'ENDED'
        assert room.game_state.vote_track == 5

def test_quest_4_double_fail_rule(app):
    with app.app_context():
        # 7 players
        users = setup_users(7)
        room = room_service.create_room(users[0])
        room_number = room.room_number
        for u in users[1:]:
            room_service.join_room(room_number, u)
        game_service.start_game(room_number, users[0])
        
        # Force round 4
        room.game_state.round_num = 4
        leader_openid = room.game_state.players[room.game_state.leader_idx]
        game_service.pick_team(room_number, leader_openid, [1, 2, 3, 4]) # 7p Q4 is 4
        for u in users:
            game_service.cast_vote(room_number, u, 'yes')
            
        team = room.game_state.current_team
        # 1 fail in Q4 for 7p -> Success because 2 needed
        game_service.perform_quest(room_number, team[0], 'fail')
        for m in team[1:]:
            game_service.perform_quest(room_number, m, 'success')
            
        assert room.game_state.quest_results[-1] is True

def test_good_wins_by_assassination_fail(app):
    with app.app_context():
        users = setup_users(5)
        room = room_service.create_room(users[0])
        room_number = room.room_number
        for u in users[1:]:
            room_service.join_room(room_number, u)
        
        game_service.start_game(room_number, users[0])
        roles = room.game_state.roles_config
        # Find someone NOT Merlin
        target_openid = next(p for p, r in roles.items() if r == 'LOYAL')
        assassin_openid = next(p for p, r in roles.items() if r == 'ASSASSIN')
        target_idx = room.game_state.players.index(target_openid) + 1
        
        # Good wins 3 quests
        room.game_state.quest_results = [True, True, True]
        room.game_state.phase = GamePhase.ASSASSINATION.value
        
        # Assassin shoots LOYAL
        msg = game_service.shoot_player(room_number, assassin_openid, target_idx)
        assert "刺杀失败" in msg
        assert room.game_state.phase == GamePhase.GAME_OVER.value
        assert room.status == 'ENDED'
