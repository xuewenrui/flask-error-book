"""
AI 智能错题本与个性化刷题系统
Flask + SQLite 基础版本
"""
import os
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# ============ 应用初始化 ============

app = Flask(__name__)
# 使用固定的SECRET_KEY，避免每次重启后session失效
app.config['SECRET_KEY'] = 'ai-error-book-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///error_book.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录后再访问此页面。'

# ============ 数据库模型 ============

class User(UserMixin, db.Model):
    """用户"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Subject(db.Model):
    """学科"""
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='📚')


class ErrorQuestion(db.Model):
    """错题"""
    __tablename__ = 'error_questions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)

    question_text = db.Column(db.Text, nullable=False)       # 题目内容
    option_a = db.Column(db.String(500))                     # 选项A
    option_b = db.Column(db.String(500))                     # 选项B
    option_c = db.Column(db.String(500))                     # 选项C
    option_d = db.Column(db.String(500))                     # 选项D
    correct_answer = db.Column(db.String(10), nullable=False)  # 正确答案 A/B/C/D
    user_answer = db.Column(db.String(10))                     # 用户当时选的答案
    explanation = db.Column(db.Text)                          # 解析
    knowledge_tags = db.Column(db.String(500))                # 知识点标签（逗号分隔）

    difficulty = db.Column(db.Integer, default=3)            # 难度 1-5
    error_count = db.Column(db.Integer, default=1)           # 错误次数
    mastered = db.Column(db.Boolean, default=False)          # 是否已掌握
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = db.relationship('User', backref='errors')
    subject = db.relationship('Subject', backref='errors')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============ 辅助函数 ============

def seed_subjects():
    """初始化预设学科数据"""
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


def get_all_knowledge_tags(user_id):
    """获取当前用户的所有知识点标签"""
    errors = ErrorQuestion.query.filter_by(user_id=user_id).all()
    tags_set = set()
    for e in errors:
        if e.knowledge_tags:
            for tag in e.knowledge_tags.split(','):
                tag = tag.strip()
                if tag:
                    tags_set.add(tag)
    return sorted(tags_set)


# ============ 认证路由 ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
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
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'欢迎回来，{username}！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('login'))


# ============ 功能路由 ============

@app.route('/dashboard')
@login_required
def dashboard():
    """学习仪表盘"""
    total_errors = ErrorQuestion.query.filter_by(user_id=current_user.id).count()
    total_mastered = ErrorQuestion.query.filter_by(
        user_id=current_user.id, mastered=True
    ).count()
    total_practice = db.session.query(db.func.count(ErrorQuestion.id)).filter_by(
        user_id=current_user.id
    ).scalar() or 0

    # 各学科错题数
    subjects = Subject.query.all()
    subject_stats = []
    for s in subjects:
        count = ErrorQuestion.query.filter_by(
            user_id=current_user.id, subject_id=s.id
        ).count()
        if count > 0:
            subject_stats.append({'name': s.name, 'icon': s.icon, 'count': count})

    # 最近错题
    recent_errors = ErrorQuestion.query.filter_by(user_id=current_user.id) \
        .order_by(ErrorQuestion.created_at.desc()).limit(5).all()

    # 所有标签
    all_tags = get_all_knowledge_tags(current_user.id)

    return render_template(
        'dashboard.html',
        total_errors=total_errors,
        total_mastered=total_mastered,
        mastery_rate=round(total_mastered / total_errors * 100) if total_errors > 0 else 0,
        subject_stats=subject_stats,
        recent_errors=recent_errors,
        all_tags=all_tags
    )


@app.route('/error-book')
@login_required
def error_book():
    """错题本列表"""
    subject_id = request.args.get('subject_id', type=int)
    tag = request.args.get('tag', '').strip()

    query = ErrorQuestion.query.filter_by(user_id=current_user.id)

    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    if tag:
        # 模糊匹配知识点标签
        query = query.filter(ErrorQuestion.knowledge_tags.contains(tag))

    errors = query.order_by(ErrorQuestion.created_at.desc()).all()
    subjects = Subject.query.all()
    all_tags = get_all_knowledge_tags(current_user.id)

    return render_template(
        'error_book.html',
        errors=errors,
        subjects=subjects,
        all_tags=all_tags,
        current_subject=subject_id,
        current_tag=tag
    )


@app.route('/error-book/add', methods=['GET', 'POST'])
@login_required
def add_error():
    """添加错题"""
    subjects = Subject.query.all()

    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        user_answer = request.form.get('user_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        knowledge_tags = request.form.get('knowledge_tags', '').strip()
        difficulty = request.form.get('difficulty', 3, type=int)

        if not question_text or not correct_answer or not subject_id:
            flash('题目内容、正确答案和学科为必填项', 'error')
            return render_template('add_error.html', subjects=subjects)

        error = ErrorQuestion(
            user_id=current_user.id,
            subject_id=subject_id,
            question_text=question_text,
            option_a=option_a or None,
            option_b=option_b or None,
            option_c=option_c or None,
            option_d=option_d or None,
            correct_answer=correct_answer,
            user_answer=user_answer or None,
            explanation=explanation or None,
            knowledge_tags=knowledge_tags or None,
            difficulty=difficulty,
        )
        db.session.add(error)
        db.session.commit()

        flash('错题添加成功！', 'success')
        return redirect(url_for('error_book'))

    return render_template('add_error.html', subjects=subjects)


@app.route('/error-book/<int:error_id>')
@login_required
def error_detail(error_id):
    """错题详情"""
    error = ErrorQuestion.query.get_or_404(error_id)
    if error.user_id != current_user.id:
        flash('无权访问', 'error')
        return redirect(url_for('error_book'))
    return render_template('error_detail.html', error=error)


@app.route('/error-book/<int:error_id>/toggle-mastered', methods=['POST'])
@login_required
def toggle_mastered(error_id):
    """切换掌握状态"""
    error = ErrorQuestion.query.get_or_404(error_id)
    if error.user_id != current_user.id:
        return jsonify({'success': False, 'error': '无权操作'}), 403

    error.mastered = not error.mastered
    db.session.commit()
    return jsonify({'success': True, 'mastered': error.mastered})


@app.route('/error-book/<int:error_id>/delete', methods=['POST'])
@login_required
def delete_error(error_id):
    """删除错题"""
    error = ErrorQuestion.query.get_or_404(error_id)
    if error.user_id != current_user.id:
        flash('无权操作', 'error')
        return redirect(url_for('error_book'))

    db.session.delete(error)
    db.session.commit()
    flash('错题已删除', 'info')
    return redirect(url_for('error_book'))


@app.route('/practice')
@login_required
def practice():
    """刷题页面入口"""
    subjects = Subject.query.all()
    all_tags = get_all_knowledge_tags(current_user.id)
    return render_template('practice.html', subjects=subjects, all_tags=all_tags)


@app.route('/practice/start', methods=['POST'])
@login_required
def start_practice():
    """开始刷题"""
    subject_id = request.form.get('subject_id', type=int)
    tag = request.form.get('tag', '').strip()
    count = request.form.get('count', 5, type=int)

    query = ErrorQuestion.query.filter_by(user_id=current_user.id)

    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if tag:
        query = query.filter(ErrorQuestion.knowledge_tags.contains(tag))

    errors = query.order_by(db.func.random()).limit(count).all()

    if not errors:
        flash('没有符合条件的错题，请先添加错题或调整筛选条件', 'warning')
        return redirect(url_for('practice'))

    # 将错题数据存入session供刷题使用
    practice_questions = []
    for e in errors:
        practice_questions.append({
            'id': e.id,
            'subject': e.subject.name,
            'question_text': e.question_text,
            'options': [
                {'key': 'A', 'text': e.option_a},
                {'key': 'B', 'text': e.option_b},
                {'key': 'C', 'text': e.option_c},
                {'key': 'D', 'text': e.option_d},
            ],
            'correct_answer': e.correct_answer,
            'explanation': e.explanation or '暂无解析',
            'knowledge_tags': e.knowledge_tags or '',
        })

    session['practice_questions'] = practice_questions
    session['current_index'] = 0
    session['practice_answers'] = {}

    return redirect(url_for('practice_session'))


@app.route('/practice/session')
@login_required
def practice_session():
    """答题页面"""
    questions = session.get('practice_questions', [])
    current_index = session.get('current_index', 0)

    if not questions:
        flash('没有刷题数据，请重新开始', 'warning')
        return redirect(url_for('practice'))

    if current_index >= len(questions):
        return redirect(url_for('practice_result'))

    question = questions[current_index]
    total = len(questions)
    # 只显示有内容的选项
    options = [o for o in question['options'] if o['text']]

    return render_template(
        'practice_session.html',
        question=question,
        current_index=current_index,
        total=total,
        options=options
    )


@app.route('/practice/answer', methods=['POST'])
@login_required
def submit_answer():
    """提交答案"""
    questions = session.get('practice_questions', [])
    current_index = session.get('current_index', 0)
    user_answer = request.form.get('answer', '').strip().upper()

    if 'practice_answers' not in session:
        session['practice_answers'] = {}

    answers = session['practice_answers']

    if current_index < len(questions):
        q = questions[current_index]
        is_correct = (user_answer == q['correct_answer'])
        answers[str(current_index)] = {
            'user_answer': user_answer,
            'correct_answer': q['correct_answer'],
            'is_correct': is_correct,
        }
        session['practice_answers'] = answers

    return jsonify({'success': True, **answers[str(current_index)]})


@app.route('/practice/next', methods=['POST'])
@login_required
def next_question():
    session['current_index'] = session.get('current_index', 0) + 1
    return jsonify({'success': True})


@app.route('/practice/result')
@login_required
def practice_result():
    """刷题结果"""
    questions = session.get('practice_questions', [])
    answers = session.get('practice_answers', {})

    total = len(questions)
    correct_count = sum(1 for a in answers.values() if a['is_correct'])

    # 拼装结果
    results = []
    for i, q in enumerate(questions):
        a = answers.get(str(i), {})
        results.append({
            'question': q,
            'user_answer': a.get('user_answer', '未作答'),
            'correct_answer': a.get('correct_answer', q['correct_answer']),
            'is_correct': a.get('is_correct', False),
        })

    score = round(correct_count / total * 100, 1) if total > 0 else 0

    return render_template(
        'practice_result.html',
        results=results,
        total=total,
        correct_count=correct_count,
        score=score
    )


@app.route('/knowledge-map')
@login_required
def knowledge_map():
    """知识图谱"""
    all_tags = get_all_knowledge_tags(current_user.id)

    # 统计每个标签的错题数
    tag_stats = []
    for tag in all_tags:
        count = ErrorQuestion.query.filter_by(user_id=current_user.id) \
            .filter(ErrorQuestion.knowledge_tags.contains(tag)).count()
        tag_stats.append({'name': tag, 'count': count})

    return render_template('knowledge_map.html', tag_stats=tag_stats)


# ============ 启动入口 ============

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_subjects()
    app.run(debug=True, host='0.0.0.0', port=5000)

# ===== Render 启动时自动建表与初始化 =====
with app.app_context():
    db.create_all()
    seed_subjects()

