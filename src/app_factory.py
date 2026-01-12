from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from src.config.settings import settings
from src.utils.logger import setup_logging, get_logger

# Extensions
db = SQLAlchemy()

logger = get_logger(__name__)

def create_app(config_override=None):
    setup_logging()
    
    app = Flask(__name__)
    
    # Configuration
    app.config["APP_ENV"] = settings.APP_ENV
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REDIS_URL"] = settings.REDIS_URL
    
    if config_override:
        app.config.update(config_override)
        
    # Initialize extensions
    db.init_app(app)
    
    # 快速失败自检：MySQL
    with app.app_context():
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            logger.info("✅ MySQL connection verified.")
        except Exception as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            if settings.APP_ENV == 'dev':
                print("\n" + "="*50)
                print("💡 提示: 检测到数据库连接失败。")
                print("请确保你已经启动了本地开发环境的基础设施：")
                print("👉 运行命令: docker compose up -d")
                print("="*50 + "\n")
            import sys
            sys.exit(1)

    from src.extensions.redis_ext import redis_manager
    redis_manager.init_app(app)
    logger.info("✅ Redis connection verified.")
    
    # Register Blueprints
    from src.controllers.wechat_ctrl import wechat_bp
    from src.controllers.api_ctrl import api_bp
    
    app.register_blueprint(wechat_bp)
    app.register_blueprint(api_bp)
    
    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok"})

    logger.info(f"🚀 Mini-Avalon started in [{settings.APP_ENV}] mode")
    logger.info(f"📅 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    return app
