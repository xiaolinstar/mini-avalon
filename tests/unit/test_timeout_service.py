"""测试超时检测服务"""
from unittest.mock import Mock, patch

import pytest

from src.services.timeout_service import TimeoutService


@pytest.fixture
def timeout_service_instance():
    """创建超时服务实例"""
    return TimeoutService()


@pytest.fixture
def mock_room_with_vote_timeout():
    """创建模拟的投票超时房间"""
    from datetime import datetime as dt

    room = Mock()
    room.room_number = "1234"
    room.status = 'PLAYING'

    gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
    gs.phase = 'TEAM_VOTE'
    gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
    gs.timeout_seconds = 60
    gs.players = ['user1', 'user2', 'user3', 'user4', 'user5']
    gs.votes = {'user1': 'yes', 'user2': 'no'}  # 3 人未投票
    gs.roles_config = {
        'user1': 'MERLIN',
        'user2': 'ASSASSIN',
        'user3': 'LOYAL',
        'user4': 'MORGANA',
        'user5': 'PERCIVAL'
    }
    room.game_state = gs

    return room


@pytest.fixture
def mock_room_with_quest_timeout():
    """创建模拟的任务超时房间"""
    from datetime import datetime as dt

    room = Mock()
    room.room_number = "5678"
    room.status = 'PLAYING'

    gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'current_team', 'quest_votes', 'roles_config'])
    gs.phase = 'QUEST_PERFORM'
    gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
    gs.timeout_seconds = 60
    gs.players = ['user1', 'user2', 'user3', 'user4', 'user5']
    gs.current_team = ['user1', 'user2', 'user3']
    gs.quest_votes = {'user1': 'success'}  # 2 人未执行
    gs.roles_config = {
        'user1': 'MERLIN',
        'user2': 'ASSASSIN',
        'user3': 'LOYAL',
        'user4': 'MORGANA',
        'user5': 'PERCIVAL'
    }
    room.game_state = gs

    return room


class TestVoteTimeout:
    """测试投票超时处理"""

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_check_timeout_vote_phase(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance, mock_room_with_vote_timeout):
        """测试检测投票阶段超时"""
        from datetime import datetime as dt

        # Mock datetime.utcnow() 返回一个超时的时间
        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)  # 2 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(mock_room_with_vote_timeout)
        assert is_timeout is True

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_no_timeout_when_all_voted(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance):
        """测试所有人都已投票时不处理超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "1234"
        room.status = 'PLAYING'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
        gs.phase = 'TEAM_VOTE'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.votes = {'user1': 'yes', 'user2': 'no'}  # 所有人都投票了
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 1, 30)  # 1.5 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 所有人都投票了，应该返回 False（不处理超时）
        assert is_timeout is False

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_no_timeout_before_timeout_period(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance):
        """测试未达到超时时间时不处理超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "1234"
        room.status = 'PLAYING'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
        gs.phase = 'TEAM_VOTE'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.votes = {'user1': 'yes'}
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 0, 30)  # 30 秒后，未超时

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 未达到超时时间，应该返回 False
        assert is_timeout is False

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.random')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_auto_vote_for_good_players(self, mock_game_service, mock_room_repo, mock_random, mock_datetime, timeout_service_instance, mock_room_with_vote_timeout):
        """测试好阵营玩家自动投票倾向（70% yes）"""
        from datetime import datetime as dt

        # 模拟 random 随机返回 0.65（小于 0.7，应该投票 yes）
        mock_random.random.return_value = 0.65
        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)

        timeout_service_instance._handle_vote_timeout(mock_room_with_vote_timeout)

        # 检查未投票的好人被设置为 yes
        updated_votes = mock_room_with_vote_timeout.game_state.votes
        assert updated_votes['user3'] == 'yes'  # LOYAL

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.random')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_auto_vote_for_evil_players(self, mock_game_service, mock_room_repo, mock_random, mock_datetime, timeout_service_instance, mock_room_with_vote_timeout):
        """测试坏阵营玩家自动投票倾向（60% no）"""
        from datetime import datetime as dt

        # 模拟 random 随机返回 0.55（小于 0.6，应该投票 no）
        mock_random.random.return_value = 0.55
        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)

        timeout_service_instance._handle_vote_timeout(mock_room_with_vote_timeout)

        # 检查未投票的坏人被设置为 no
        updated_votes = mock_room_with_vote_timeout.game_state.votes
        assert updated_votes['user4'] == 'no'  # MORGANA


class TestQuestTimeout:
    """测试任务超时处理"""

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_check_timeout_quest_phase(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance, mock_room_with_quest_timeout):
        """测试检测任务阶段超时"""
        from datetime import datetime as dt

        # Mock datetime.utcnow() 返回一个超时的时间
        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)  # 2 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(mock_room_with_quest_timeout)
        assert is_timeout is True

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_no_timeout_when_all_completed(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance):
        """测试所有人都已执行任务时不处理超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "5678"
        room.status = 'PLAYING'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'current_team', 'quest_votes', 'roles_config'])
        gs.phase = 'QUEST_PERFORM'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.current_team = ['user1', 'user2']
        gs.quest_votes = {'user1': 'success', 'user2': 'fail'}  # 所有人都执行了
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 1, 30)  # 1.5 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 所有人都执行了，应该返回 False（不处理超时）
        assert is_timeout is False

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_auto_quest_for_good_players(self, mock_game_service, mock_room_repo, mock_datetime, timeout_service_instance, mock_room_with_quest_timeout):
        """测试好阵营玩家必须成功"""
        from datetime import datetime as dt

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)

        timeout_service_instance._handle_quest_timeout(mock_room_with_quest_timeout)

        # 检查未执行的好人被设置为 success
        updated_votes = mock_room_with_quest_timeout.game_state.quest_votes
        assert updated_votes['user3'] == 'success'  # LOYAL

    @patch('src.services.timeout_service.datetime')
    @patch('src.services.timeout_service.random')
    @patch('src.services.timeout_service.room_repo')
    @patch('src.services.timeout_service.game_service')
    def test_auto_quest_for_evil_players(self, mock_game_service, mock_room_repo, mock_random, mock_datetime, timeout_service_instance, mock_room_with_quest_timeout):
        """测试坏阵营玩家可能失败（40% 概率）"""
        from datetime import datetime as dt

        # 模拟 random 随机返回 0.35（小于 0.4，应该失败）
        mock_random.random.return_value = 0.35
        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 2, 0)

        timeout_service_instance._handle_quest_timeout(mock_room_with_quest_timeout)

        # 检查未执行的坏人被设置为 fail
        updated_votes = mock_room_with_quest_timeout.game_state.quest_votes
        assert updated_votes['user2'] == 'fail'  # ASSASSIN


class TestOtherPhases:
    """测试其他阶段不触发超时"""

    @patch('src.services.timeout_service.datetime')
    def test_team_selection_no_timeout(self, mock_datetime, timeout_service_instance):
        """测试组队阶段不触发超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "1234"
        room.status = 'PLAYING'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
        gs.phase = 'TEAM_SELECTION'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.votes = {'user1': 'yes'}
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 3, 0)  # 3 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 不是投票或任务阶段，应该返回 False
        assert is_timeout is False

    @patch('src.services.timeout_service.datetime')
    def test_assassination_no_timeout(self, mock_datetime, timeout_service_instance):
        """测试刺杀阶段不触发超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "1234"
        room.status = 'PLAYING'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
        gs.phase = 'ASSASSINATION'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.votes = {'user1': 'yes'}
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 3, 0)  # 3 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 不是投票或任务阶段，应该返回 False
        assert is_timeout is False

    @patch('src.services.timeout_service.datetime')
    def test_game_over_no_timeout(self, mock_datetime, timeout_service_instance):
        """测试游戏结束不触发超时"""
        from datetime import datetime as dt

        room = Mock()
        room.room_number = "1234"
        room.status = 'ENDED'

        gs = Mock(spec=['phase', 'phase_start_time', 'timeout_seconds', 'players', 'votes', 'roles_config'])
        gs.phase = 'GAME_OVER'
        gs.phase_start_time = dt(2024, 1, 1, 0, 0, 0)
        gs.timeout_seconds = 60
        gs.players = ['user1', 'user2']
        gs.votes = {'user1': 'yes'}
        room.game_state = gs

        mock_datetime.now.return_value = dt(2024, 1, 1, 0, 3, 0)  # 3 分钟后

        is_timeout = timeout_service_instance._check_room_timeout(room)
        # 游戏已结束，应该返回 False
        assert is_timeout is False


class TestPhaseStartTimeUpdate:
    """测试阶段开始时间更新"""

    @patch('src.services.timeout_service.room_repo')
    def test_update_phase_start_time(self, mock_room_repo, timeout_service_instance):
        """测试更新阶段开始时间"""
        mock_room = Mock()
        mock_room.room_number = "1234"
        mock_room.game_state = Mock()

        mock_room_repo.get_by_number.return_value = mock_room

        timeout_service_instance.update_phase_start_time("1234")

        # 验证 phase_start_time 被更新
        assert hasattr(mock_room.game_state, 'phase_start_time')
        mock_room_repo.update_game_state.assert_called_once()
