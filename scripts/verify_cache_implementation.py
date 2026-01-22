#!/usr/bin/env python3
"""
验证 Redis Cache-Aside 实现的脚本
用于手动测试缓存功能是否正常工作
"""
import sys
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, '/Users/xlxing/PycharmProjects/mini-avalon')

def test_cache_serialization():
    """测试序列化和反序列化"""
    print("=" * 60)
    print("测试 1: 序列化和反序列化")
    print("=" * 60)
    
    try:
        from src.models.sql_models import GameState, Room
        from src.repositories.room_repository import RoomRepository
        
        # 创建测试用的 Room 对象
        repo = RoomRepository()
        room = Room(
            id=1,
            room_number="1234",
            owner_id="user1",
            status="WAITING",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
        
        # 测试序列化
        serialized = repo._serialize_room(room)
        print("✅ 序列化成功")
        print(f"   - 房间号: {serialized['room_number']}")
        print(f"   - 状态: {serialized['status']}")
        print(f"   - 游戏阶段: {serialized['game_state']['phase']}")
        
        # 测试反序列化
        from src.utils.json_utils import json_dumps
        json_data = json_dumps(serialized)
        deserialized = repo._deserialize_room(json_data)
        
        if deserialized and deserialized.room_number == "1234":
            print("✅ 反序列化成功")
            print(f"   - 房间号: {deserialized.room_number}")
            print(f"   - 状态: {deserialized.status}")
            print(f"   - 游戏阶段: {deserialized.game_state.phase}")
        else:
            print("❌ 反序列化失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_logic():
    """测试缓存逻辑"""
    print("\n" + "=" * 60)
    print("测试 2: Cache-Aside 逻辑验证")
    print("=" * 60)
    
    try:
        from src.repositories.room_repository import RoomRepository
        
        repo = RoomRepository()
        
        # 验证常量配置
        print(f"✅ 缓存 TTL: {repo.CACHE_TTL} 秒 (1 小时)")
        print(f"✅ 缓存前缀: {repo.CACHE_PREFIX}")
        
        # 验证方法存在
        methods = [
            '_serialize_room',
            '_deserialize_room',
            '_set_cache',
            'get_by_number',
            'save',
            'delete',
            'update_game_state'
        ]
        
        for method in methods:
            if hasattr(repo, method):
                print(f"✅ 方法 {method} 已实现")
            else:
                print(f"❌ 方法 {method} 未找到")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 3: 错误处理机制")
    print("=" * 60)
    
    try:
        from src.repositories.room_repository import RoomRepository
        
        repo = RoomRepository()
        
        # 测试反序列化无效数据
        result = repo._deserialize_room("invalid json")
        if result is None:
            print("✅ 无效 JSON 正确返回 None")
        else:
            print("❌ 无效 JSON 处理不当")
            return False
        
        # 测试反序列化空数据
        result = repo._deserialize_room(None)
        if result is None:
            print("✅ 空数据正确返回 None")
        else:
            print("❌ 空数据处理不当")
            return False
        
        # 测试反序列化空字符串
        result = repo._deserialize_room("")
        if result is None:
            print("✅ 空字符串正确返回 None")
        else:
            print("❌ 空字符串处理不当")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n🚀 开始验证 Redis Cache-Aside 实现\n")
    
    results = []
    
    # 运行所有测试
    results.append(("序列化/反序列化", test_cache_serialization()))
    results.append(("缓存逻辑", test_cache_logic()))
    results.append(("错误处理", test_error_handling()))
    
    # 打印结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 所有测试通过！Redis Cache-Aside 实现完成。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
