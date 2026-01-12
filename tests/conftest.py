import pytest
import os
import sys

# 将 src 加入路径，方便导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment to test
os.environ["APP_ENV"] = "test"

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    from src.app_factory import create_app, db
    from unittest import mock
    
    # Mock redis_client before app creation
    with mock.patch('src.extensions.redis_ext.Redis.from_url') as mock_from_url:
        mock_redis = mock_from_url.return_value
        # Mock common methods
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        })
        
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()
