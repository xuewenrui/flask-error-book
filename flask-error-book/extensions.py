"""
Flask 扩展初始化（db, login_manager, redis_client）
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import redis
import os

db = SQLAlchemy()
login_manager = LoginManager()

# Redis 客户端（可选）
redis_client = None


def init_redis(app):
    """初始化 Redis 连接，失败时降级"""
    global redis_client
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        client = redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        redis_client = client
        app.logger.info(f'Redis connected: {redis_url}')
    except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
        redis_client = None
        app.logger.warning(f'Redis unavailable ({e}), caching disabled. '
                           'Set REDIS_URL env var to enable Redis caching.')


def get_redis():
    """获取 Redis 客户端，可能为 None"""
    return redis_client
