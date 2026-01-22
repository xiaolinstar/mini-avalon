import os
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path，确保可以以 'src.xxx' 方式导入
# 无论是在项目根目录运行 python src/main.py 还是在 src 目录下运行 python main.py
root_dir = str(Path(__file__).resolve().parents[1])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.app_factory import create_app

app = create_app()

@app.cli.command("cleanup-rooms")
def cleanup_rooms_command():
    """清理过期房间（使用新的cleanup_service）"""
    from src.services.cleanup_service import cleanup_service
    stats = cleanup_service.cleanup_expired_rooms()
    print(f"Successfully cleaned up {stats['total']} rooms:")
    for key, value in stats.items():
        if key != 'total':
            print(f"  {key}: {value}")

@app.cli.command("room-stats")
def room_stats_command():
    """查看房间统计信息"""
    from src.services.cleanup_service import cleanup_service
    stats = cleanup_service.get_room_statistics()
    print("Room statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

@app.cli.command("check-timeouts")
def check_timeouts_command():
    """手动检查并处理游戏超时"""
    from src.services.timeout_service import timeout_service
    count = timeout_service.check_and_process_timeouts()
    print(f"Processed {count} timed out games.")

def main():
    """启动应用"""
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
