from src.services.game_service import game_service


def test_assign_roles(app):
    with app.app_context():
        # Test 5 players
        players = [f"u{i}" for i in range(5)]
        roles = game_service._assign_roles(players)
        assert len(roles) == 5
        role_counts = {}
        for r in roles.values():
            role_counts[r] = role_counts.get(r, 0) + 1
        
        # 5p: 3 Good, 2 Evil. Good: Merlin, Percival, Loyal. Evil: Assassin + (Morgana/Mordred/Oberon/Minion)
        good_roles = ['MERLIN', 'PERCIVAL', 'LOYAL']
        evil_roles = ['ASSASSIN', 'MORGANA', 'MORDRED', 'OBERON', 'MINION']
        
        goods = sum(1 for r in roles.values() if r in good_roles)
        evils = sum(1 for r in roles.values() if r in evil_roles)
        assert goods == 3
        assert evils == 2
        assert 'MERLIN' in roles.values()
        assert 'ASSASSIN' in roles.values()

def test_merlin_vision(app):
    with app.app_context():
        room_mock = type('obj', (object,), {
            'game_state': type('obj', (object,), {
                'players': ['u1', 'u2', 'u3', 'u4', 'u5'],
                'roles_config': {
                    'u1': 'MERLIN',
                    'u2': 'ASSASSIN',
                    'u3': 'MORDRED',
                    'u4': 'LOYAL',
                    'u5': 'MINION'
                }
            })
        })
        info = game_service.get_player_info(room_mock, 'u1')
        assert "你的身份是: MERLIN" in info
        assert "玩家2" in info # Assassin
        assert "玩家5" in info # Minion
        assert "玩家3" not in info # Mordred is hidden

def test_percival_vision(app):
    with app.app_context():
        room_mock = type('obj', (object,), {
            'game_state': type('obj', (object,), {
                'players': ['u1', 'u2', 'u3', 'u4', 'u5'],
                'roles_config': {
                    'u1': 'PERCIVAL',
                    'u2': 'MERLIN',
                    'u3': 'MORGANA',
                    'u4': 'LOYAL',
                    'u5': 'ASSASSIN'
                }
            })
        })
        info = game_service.get_player_info(room_mock, 'u1')
        assert "你的身份是: PERCIVAL" in info
        assert "玩家2" in info # Merlin
        assert "玩家3" in info # Morgana

def test_oberon_vision(app):
    with app.app_context():
        room_mock = type('obj', (object,), {
            'game_state': type('obj', (object,), {
                'players': ['u1', 'u2', 'u3', 'u4', 'u5'],
                'roles_config': {
                    'u1': 'MINION',
                    'u2': 'OBERON',
                    'u3': 'ASSASSIN',
                    'u4': 'MERLIN',
                    'u5': 'LOYAL'
                }
            })
        })
        # Minion vision: sees Assassin, NOT Oberon
        info_minion = game_service.get_player_info(room_mock, 'u1')
        assert "玩家3" in info_minion
        assert "玩家2" not in info_minion
        
        # Oberon vision: sees NO ONE
        info_oberon = game_service.get_player_info(room_mock, 'u2')
        assert "奥伯伦不认识其他坏人" in info_oberon
        assert "你的盟友" not in info_oberon
