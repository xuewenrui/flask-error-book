"""
AI 智能错题本与个性化刷题系统
Flask + SQLite/MySQL + Redis + Celery
"""
import os
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, init_redis
from routes import register_routes
from models import User


def create_app(config_class=Config):
    """工厂函数 - 创建 Flask 应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录后再访问此页面。'

    # 初始化 Redis（可选，不可用时降级）
    init_redis(app)

    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 注册路由
    from routes.auth import init_auth_routes
    from routes.error_book import init_error_book_routes
    from routes.practice import init_practice_routes
    from routes.dashboard import init_dashboard_routes

    init_auth_routes()
    init_error_book_routes()
    init_practice_routes()
    init_dashboard_routes()
    register_routes(app)

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html', content='<h1>页面未找到</h1>'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('base.html', content='<h1>服务器内部错误</h1>'), 500

    # 数据库初始化
    with app.app_context():
        db.create_all()
        _seed_subjects()

    return app


def _seed_subjects():
    """初始化预设学科数据"""
    from models import Subject
    if Subject.query.count() == 0:
        subjects = [
            Subject(name='数学', icon='📐'),
            Subject(name='英语', icon='📖'),
            Subject(name='物理', icon='⚡'),
            Subject(name='化学', icon='🧪'),
            Subject(name='生物', icon='🧬'),
            Subject(name='语文', icon='📝'),
            Subject(name='历史', icon='📜'),
            Subject(name='地理', icon='🌍'),
        ]
        db.session.add_all(subjects)
        db.session.commit()


# ============ 启动入口 ============

if __name__ == '__main__':
    app = create_app()
    print("AI智能错题本启动中...")
    print(f"数据库引擎: {Config.get_engine_type()}")
    print("请在浏览器中访问: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
