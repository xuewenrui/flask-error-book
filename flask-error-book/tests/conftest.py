"""
pytest 测试配置 — 共享 fixtures

用法: pytest tests/ -v
"""
import pytest
import os
import tempfile

# 确保测试使用 SQLite（不影响本地开发数据库）
os.environ['DATABASE_URL'] = ''  # 空值 = 使用 SQLite
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'  # Redis 不可用时可降级

from app import create_app
from extensions import db as _db


# 在导入 models 前先创建 app 并初始化 db，防止 create_app 中的 _seed_subjects 干扰测试
_app_instance = create_app()
_app_instance.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

from models import User, Subject, ErrorQuestion


@pytest.fixture(scope='session')
def app():
    """创建 Flask 测试应用（Session 级别，所有测试共享）"""
    _app_instance.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
    })
    return _app_instance


@pytest.fixture()
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture()
def db(app):
    """数据库（每个测试重新建表）"""
    with app.app_context():
        _db.create_all()
        # 先检查是否已有学科数据（create_app 可能已 seed）
        existing = Subject.query.count()
        if existing == 0:
            subjects = [
                Subject(name='数学', icon='📐'),
                Subject(name='英语', icon='📖'),
                Subject(name='物理', icon='⚡'),
            ]
            _db.session.add_all(subjects)
            _db.session.commit()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def logged_in_user(client, db, app):
    """创建并登录一个测试用户，返回 (client, user)"""
    user = User(username='testuser')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    # 登录
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123',
    }, follow_redirects=True)

    return client, user


@pytest.fixture()
def sample_error(logged_in_user, db):
    """创建一个示例错题"""
    client, user = logged_in_user
    subject = Subject.query.first()
    error = ErrorQuestion(
        user_id=user.id,
        subject_id=subject.id,
        question_text='1+1等于几？',
        option_a='1',
        option_b='2',
        option_c='3',
        option_d='4',
        correct_answer='B',
        user_answer='A',
        explanation='1+1=2，基础加法。',
        knowledge_tags='加法,数学基础',
        difficulty=1,
    )
    db.session.add(error)
    db.session.commit()
    return error, user
