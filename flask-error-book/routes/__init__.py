"""
路由包初始化 - 注册所有蓝图
"""
from flask import Blueprint

# 认证蓝图
auth_bp = Blueprint('auth', __name__)

# 错题本蓝图
error_book_bp = Blueprint('error_book', __name__, url_prefix='/error-book')

# 刷题蓝图
practice_bp = Blueprint('practice', __name__, url_prefix='/practice')

# 仪表盘蓝图
dashboard_bp = Blueprint('dashboard', __name__)

# 导入各路由模块（触发装饰器注册）
from routes import auth, error_book, practice, dashboard


def register_routes(app):
    """注册所有蓝图到 app"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(error_book_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(practice_bp)
