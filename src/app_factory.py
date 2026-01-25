from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from src.config.settings import settings
from src.utils.logger import get_logger, setup_logging

# Extensions
db = SQLAlchemy()
migrate = Migrate()

logger = get_logger(__name__)


def create_app(config_override=None):
    setup_logging()

    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            environment=settings.APP_ENV,
        )
        logger.info("✅ Sentry initialized.")

    app = Flask(__name__)

    # Configuration
    app.config["APP_ENV"] = settings.APP_ENV
    app.config["SECRET_KEY"] = settings.SECRET_KEY.get_secret_value()
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REDIS_URL"] = settings.REDIS_URL

    if config_override:
        app.config.update(config_override)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models to register them with SQLAlchemy
    from src import models

    # 快速失败自检：MySQL
    with app.app_context():
        try:
            from sqlalchemy import text

            db.session.execute(text("SELECT 1"))
            logger.info("✅ MySQL connection verified.")
        except Exception as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            if settings.APP_ENV == "dev":
                print("\n" + "=" * 50)
                print("💡 提示: 检测到数据库连接失败。")
                print("请确保你已经启动了本地开发环境的基础设施：")
                print("👉 运行命令: docker compose up -d")
                print("=" * 50 + "\n")
            import sys

            sys.exit(1)

    from src.extensions.redis_ext import redis_manager

    redis_manager.init_app(app)
    logger.info("✅ Redis connection verified.")

    # Register Blueprints
    from src.controllers.api_ctrl import api_bp
    from src.controllers.wechat_ctrl import wechat_bp

    app.register_blueprint(wechat_bp)
    app.register_blueprint(api_bp)

    # Register Error Handlers
    from src.extensions.error_handler import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def add_trace_id():
        import uuid

        from flask import g, request

        # 优先从请求头获取，方便全链路追踪
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        g.trace_id = trace_id

    @app.after_request
    def add_trace_id_to_header(response):
        from flask import g

        if hasattr(g, "trace_id"):
            response.headers["X-Trace-Id"] = g.trace_id
        return response

    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok"})

    # 启动超时检测后台任务
    def _start_timeout_checker():
        import time

        from src.services.timeout_service import timeout_service

        def timeout_checker_loop():
            with app.app_context():
                while True:
                    try:
                        timeout_service.check_and_process_timeouts()
                    except Exception as e:
                        logger.error(f"Error in timeout checker: {e}")
                    time.sleep(timeout_service.check_interval)

        # 在后台线程中运行
        import threading

        thread = threading.Thread(target=timeout_checker_loop, daemon=True, name="TimeoutChecker")
        thread.start()
        logger.info("✅ Timeout checker background thread started")

    # 只在主进程启动后台任务
    import os

    if (os.environ.get("WERKZEUG_RUN_MAIN") == "true" or settings.APP_ENV != "dev") and not app.config.get("TESTING"):
        _start_timeout_checker()

    logger.info(f"🚀 Mini-Avalon started in [{settings.APP_ENV}] mode")
    logger.info(f"📅 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    return app
