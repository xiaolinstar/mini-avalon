"""测试 RoomRepository 的 Redis 缓存功能"""
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.models.sql_models import GameState, Room
from src.repositories.room_repository import RoomRepository


@pytest.fixture
def room_repo_instance():
    """创建 RoomRepository 实例"""
    return RoomRepository()


@pytest.fixture
def mock_room():
    """创建模拟的 Room 对象"""
    room = Room(
        id=1,
        room_number="1234",
        owner_id="user1",
        status="WAITING",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    game_state = GameState(
        id=1,
        room_id=1,
        phase="WAITING",
        round_num=1,
        vote_track=0,
        leader_idx=0,
        current_team=[],
        quest_results=[],
        roles_config={},
        players=["user1"],
        votes={},
        quest_votes=[]
    )
    room.game_state = game_state

    return room


class TestRedisCacheAside:
    """测试 Cache-Aside 策略"""

    @patch('src.repositories.room_repository.redis_manager')
    def test_cache_hit_returns_deserialized_room(self, mock_redis, room_repo_instance):
        """测试缓存命中时从 Redis 返回反序列化的对象"""
        # Mock Redis 缓存命中
        mock_redis.client.get.return_value = '{"id": 1, "room_number": "1234", "owner_id": "user1", "status": "WAITING", "version": 1, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00", "game_state": {"id": 1, "room_id": 1, "phase": "WAITING", "round_num": 1, "vote_track": 0, "leader_idx": 0, "current_team": [], "quest_results": [], "roles_config": {}, "players": ["user1"], "votes": {}, "quest_votes": []}}'

        result = room_repo_instance.get_by_number("1234")

        # 验证 Redis 被查询
        mock_redis.client.get.assert_called_once_with("cache:room:1234")
        # 验证反序列化的结果存在且房间号正确
        assert result is not None
        assert result.room_number == "1234"
        assert result.status == "WAITING"
        assert result.game_state is not None
        assert result.game_state.phase == "WAITING"

    @patch('src.repositories.room_repository.redis_manager')
    @patch('src.repositories.room_repository.Room')
    def test_cache_miss_fetches_from_db_and_sets_cache(self, mock_room_model, mock_redis, room_repo_instance, mock_room):
        """测试缓存未命中时从 DB 读取并回填缓存"""
        # Mock Redis 缓存未命中
        mock_redis.client.get.return_value = None
        # Mock DB 查询返回
        mock_room_model.query.filter_by.return_value.first.return_value = mock_room

        result = room_repo_instance.get_by_number("1234")

        # 验证 Redis 被查询
        mock_redis.client.get.assert_called_once_with("cache:room:1234")
        # 验证 DB 被查询
        mock_room_model.query.filter_by.assert_called_once_with(room_number="1234")
        # 验证缓存被设置
        mock_redis.client.setex.assert_called_once()
        call_args = mock_redis.client.setex.call_args
        assert call_args[0][0] == "cache:room:1234"
        assert call_args[0][1] == 3600  # TTL
        # 验证返回了正确的对象
        assert result == mock_room

    @patch('src.repositories.room_repository.redis_manager')
    @patch('src.repositories.room_repository.Room')
    def test_redis_error_falls_back_to_db(self, mock_room_model, mock_redis, room_repo_instance, mock_room):
        """测试 Redis 不可用时降级到 DB"""
        # Mock Redis 抛出异常
        mock_redis.client.get.side_effect = Exception("Redis connection failed")
        mock_room_model.query.filter_by.return_value.first.return_value = mock_room

        result = room_repo_instance.get_by_number("1234")

        # 验证尽管 Redis 失败，仍从 DB 返回
        assert result == mock_room
        # 验证 DB 被查询
        mock_room_model.query.filter_by.assert_called_once_with(room_number="1234")
        # 缓存设置可能失败，但不影响主流程

    @patch('src.repositories.room_repository.redis_manager')
    def test_save_invalidates_cache(self, mock_redis, room_repo_instance):
        """测试保存房间时失效缓存"""
        mock_room = Mock()
        mock_room.room_number = "1234"
        mock_room.version = 1

        with patch('src.repositories.room_repository.db'):
            room_repo_instance.save(mock_room)

            # 验证缓存被删除
            mock_redis.client.delete.assert_called_once_with("cache:room:1234")

    @patch('src.repositories.room_repository.redis_manager')
    def test_delete_invalidates_cache(self, mock_redis, room_repo_instance):
        """测试删除房间时失效缓存"""
        mock_room = Mock()
        mock_room.room_number = "1234"

        with patch('src.repositories.room_repository.db'):
            room_repo_instance.delete(mock_room)

            # 验证缓存被删除
            mock_redis.client.delete.assert_called_once_with("cache:room:1234")

    @patch('src.repositories.room_repository.redis_manager')
    def test_update_game_state_invalidates_cache(self, mock_redis, room_repo_instance):
        """测试更新游戏状态时失效缓存"""
        mock_game_state = Mock()
        mock_room = Mock()
        mock_room.room_number = "1234"
        mock_game_state.room = mock_room

        with patch('src.repositories.room_repository.db'):
            with patch('src.repositories.room_repository.flag_modified'):
                room_repo_instance.update_game_state(mock_game_state)

                # 验证缓存被删除
                mock_redis.client.delete.assert_called_once_with("cache:room:1234")


class TestSerialization:
    """测试序列化和反序列化"""

    def test_serialize_room_with_game_state(self, room_repo_instance, mock_room):
        """测试序列化包含 GameState 的 Room"""
        serialized = room_repo_instance._serialize_room(mock_room)

        assert serialized["room_number"] == "1234"
        assert serialized["status"] == "WAITING"
        assert serialized["owner_id"] == "user1"
        assert "game_state" in serialized
        assert serialized["game_state"]["phase"] == "WAITING"
        assert serialized["game_state"]["players"] == ["user1"]

    def test_deserialize_room_with_game_state(self, room_repo_instance):
        """测试反序列化包含 GameState 的 Room"""
        cache_data = '{"id": 1, "room_number": "1234", "owner_id": "user1", "status": "WAITING", "version": 1, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00", "game_state": {"id": 1, "room_id": 1, "phase": "WAITING", "round_num": 1, "vote_track": 0, "leader_idx": 0, "current_team": [], "quest_results": [], "roles_config": {}, "players": ["user1"], "votes": {}, "quest_votes": []}}'

        deserialized = room_repo_instance._deserialize_room(cache_data)

        assert deserialized is not None
        assert deserialized.room_number == "1234"
        assert deserialized.status == "WAITING"
        assert deserialized.game_state is not None
        assert deserialized.game_state.phase == "WAITING"
        assert deserialized.game_state.players == ["user1"]

    def test_deserialize_invalid_json(self, room_repo_instance):
        """测试反序列化无效 JSON"""
        result = room_repo_instance._deserialize_room("invalid json")
        assert result is None

    def test_deserialize_none_data(self, room_repo_instance):
        """测试反序列化空数据"""
        result = room_repo_instance._deserialize_room(None)
        assert result is None
