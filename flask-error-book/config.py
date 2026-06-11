"""
Flask 应用配置
支持 SQLite（默认）和 MySQL（通过 DATABASE_URL 环境变量切换）
"""
import os
import sys


class Config:
    """基础配置"""
    # Flask 密钥
    SECRET_KEY = os.getenv('SECRET_KEY', 'ai-error-book-secret-key-2026')

    # 数据库配置
    # 默认使用 SQLite，设置 DATABASE_URL 环境变量可切换到 MySQL
    # MySQL 格式: mysql+pymysql://user:password@host:port/dbname
    DATABASE_URL = os.getenv('DATABASE_URL', '')

    if DATABASE_URL:
        # MySQL / PostgreSQL 等
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL.startswith('mysql://'):
            # PyMySQL 需要 mysql+pymysql:// 格式
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('mysql://', 'mysql+pymysql://', 1)
    else:
        # 默认 SQLite
        basedir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(basedir, 'instance', 'error_book.db')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQL_ECHO', 'false').lower() == 'true'

    # Redis 配置（可选，不设置则缓存降级为无操作）
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    @staticmethod
    def get_engine_type():
        """返回当前使用的数据库引擎类型: 'sqlite' | 'mysql' | 'postgresql'"""
        uri = Config.SQLALCHEMY_DATABASE_URI
        if 'sqlite' in uri:
            return 'sqlite'
        elif 'mysql' in uri or 'pymysql' in uri:
            return 'mysql'
        elif 'postgresql' in uri:
            return 'postgresql'
        return 'unknown'
