from redis import Redis


class RedisExtension:
    def __init__(self, app=None):
        self._client = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        redis_url = app.config.get("REDIS_URL")
        # 初始化连接池
        self._client = Redis.from_url(redis_url, decode_responses=True)
        
        # 快速失败自检：确认 Redis 是否可用
        try:
            self._client.ping()
        except Exception as e:
            app.logger.error(f"❌ 无法连接到 Redis: {e}")
            if app.config.get('APP_ENV') == 'dev':
                print("\n" + "="*50)
                print("💡 提示: 检测到 Redis 连接失败。")
                print("请确保你已经启动了本地开发环境的基础设施：")
                print("👉 运行命令: docker compose up -d")
                print("="*50 + "\n")
            import sys
            sys.exit(1)
        
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['redis_manager'] = self

    @property
    def client(self) -> Redis:
        return self._client

# 创建单例对象，供外部模块导入
redis_manager = RedisExtension()
