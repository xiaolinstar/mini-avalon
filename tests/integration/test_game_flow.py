from src.fsm.avalon_fsm import GamePhase
from src.repositories.user_repository import user_repo
from src.services.game_service import game_service
from src.services.room_service import room_service


def test_integration_mini_game_flow(app):
    with app.app_context():
        # 1. Setup 5 users
        users = [f"user_{i}" for i in range(1, 6)]
        for u in users:
            user_repo.create_or_update(u, nickname=f"Player_{u[-1]}")
        
        # 2. Create room
        room = room_service.create_room(users[0])
        room_number = room.room_number
        assert room.status == 'WAITING'
        assert len(room.game_state.players) == 1
        
        # 3. Join others
        for u in users[1:]:
            room_service.join_room(room_number, u)
        
        assert len(room.game_state.players) == 5
        
        # 4. Start game
        game_service.start_game(room_number, users[0])
        assert room.status == 'PLAYING'
        assert room.game_state.phase == GamePhase.TEAM_SELECTION.value
        
        # 5. Pick Team (Quest 1 for 5 players needs 2 people)
        leader_idx = room.game_state.leader_idx
        leader_openid = room.game_state.players[leader_idx]
        game_service.pick_team(room_number, leader_openid, [1, 2])
        assert room.game_state.phase == GamePhase.TEAM_VOTE.value
        
        # 6. Vote for team (Everyone votes yes)
        for u in users:
            game_service.cast_vote(room_number, u, 'yes')
        
        assert room.game_state.phase == GamePhase.QUEST_PERFORM.value
        
        # 7. Perform Quest (Team is players at index 0 and 1)
        team_members = room.game_state.current_team
        for member in team_members:
            game_service.perform_quest(room_number, member, 'success')
            
        assert room.game_state.phase == GamePhase.TEAM_SELECTION.value
        assert room.game_state.round_num == 2
        assert room.game_state.quest_results == [True]
