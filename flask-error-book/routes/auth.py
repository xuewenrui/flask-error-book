"""
认证相关路由（注册、登录、登出）
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from extensions import db
from models import User


def init_auth_routes():
    """在 routes/__init__.py 中调用此函数来注册路由"""
    from routes import auth_bp

    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm = request.form.get('confirm_password', '').strip()

            if not username or not password:
                flash('用户名和密码不能为空', 'error')
                return render_template('register.html')

            if password != confirm:
                flash('两次输入的密码不一致', 'error')
                return render_template('register.html')

            if len(password) < 6:
                flash('密码长度不能少于6位', 'error')
                return render_template('register.html')

            if User.query.filter_by(username=username).first():
                flash('用户名已存在，请换一个', 'error')
                return render_template('register.html')

            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))

        return render_template('register.html')

    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            remember = request.form.get('remember') == 'on'

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user, remember=remember)
                flash(f'欢迎回来，{username}！', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.dashboard'))
            else:
                flash('用户名或密码错误', 'error')

        return render_template('login.html')

    @auth_bp.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('您已成功退出登录', 'info')
        return redirect(url_for('auth.login'))

    @auth_bp.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.dashboard'))
        return redirect(url_for('auth.login'))

    return auth_bp
