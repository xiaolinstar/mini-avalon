#!/usr/bin/env python3
"""
房间清理脚本
可以由cron或K8s CronJob定期执行

用法:
    python scripts/cleanup_rooms.py              # 执行清理
    python scripts/cleanup_rooms.py --stats     # 只查看统计
    python scripts/cleanup_rooms.py --dry-run    # 模拟运行（不删除）
"""
import argparse
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app_factory import create_app
from src.services.cleanup_service import cleanup_service


def main():
    parser = argparse.ArgumentParser(description='清理过期房间')
    parser.add_argument('--stats', action='store_true', help='只显示统计信息，不执行清理')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际删除')

    args = parser.parse_args()

    # 创建应用上下文
    app = create_app()

    with app.app_context():
        if args.stats:
            # 只显示统计
            print("=" * 60)
            print("当前房间统计")
            print("=" * 60)
            stats = cleanup_service.get_room_statistics()
            for key, value in stats.items():
                print(f"  {key:20s}: {value}")
            print("=" * 60)
            return 0

        if args.dry_run:
            # 模拟运行
            print("=" * 60)
            print("模拟运行 - 不会实际删除房间")
            print("=" * 60)
            stats = cleanup_service.get_room_statistics()
            print("\n当前状态:")
            for key, value in stats.items():
                print(f"  {key:20s}: {value}")
            print("\n[模拟] 将根据策略清理过期房间...")
            print("=" * 60)
            return 0

        # 执行清理
        print("=" * 60)
        print("开始清理过期房间")
        print("=" * 60)

        # 显示清理前统计
        print("\n清理前统计:")
        stats_before = cleanup_service.get_room_statistics()
        for key, value in stats_before.items():
            print(f"  {key:20s}: {value}")

        # 执行清理
        print("\n执行清理...")
        cleanup_result = cleanup_service.cleanup_expired_rooms()

        # 显示清理结果
        print("\n清理结果:")
        for key, value in cleanup_result.items():
            if key != 'total' and value > 0:
                print(f"  {key:20s}: {value}")

        print(f"\n总计清理: {cleanup_result['total']} 个房间")

        # 显示清理后统计
        print("\n清理后统计:")
        stats_after = cleanup_service.get_room_statistics()
        for key, value in stats_after.items():
            print(f"  {key:20s}: {value}")

        print("=" * 60)
        print("清理完成!")
        print("=" * 60)

        return 0


if __name__ == '__main__':
    sys.exit(main())
