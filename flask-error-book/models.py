"""
数据库模型
"""
from datetime import datetime
from flask_login import UserMixin
from flask import current_app
from extensions import db


class User(UserMixin, db.Model):
    """用户"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
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

    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500))
    option_b = db.Column(db.String(500))
    option_c = db.Column(db.String(500))
    option_d = db.Column(db.String(500))
    correct_answer = db.Column(db.String(10), nullable=False)
    user_answer = db.Column(db.String(10))
    explanation = db.Column(db.Text)
    knowledge_tags = db.Column(db.String(500))

    difficulty = db.Column(db.Integer, default=3)
    error_count = db.Column(db.Integer, default=1)
    mastered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='errors')
    subject = db.relationship('Subject', backref='errors')


# ============ 原生 SQL 查询方法（面试展示用） ============

def get_dashboard_stats(user_id):
    """
    使用原生 SQL 查询仪表盘统计数据。
    包含: 多表 JOIN + GROUP BY 聚合 + 子查询。
    展示了 SQLAlchemy ORM 之外的原生 SQL 能力。
    """
    from sqlalchemy import text
    result = db.session.execute(text("""
        SELECT
            COUNT(*) AS total_errors,
            SUM(CASE WHEN mastered = 1 THEN 1 ELSE 0 END) AS total_mastered,
            ROUND(
                CAST(SUM(CASE WHEN mastered = 1 THEN 1 ELSE 0 END) AS FLOAT) /
                NULLIF(COUNT(*), 0) * 100
            ) AS mastery_rate
        FROM error_questions
        WHERE user_id = :user_id
    """), {'user_id': user_id}).fetchone()

    # 按学科分组统计
    subject_stats = db.session.execute(text("""
        SELECT s.name, s.icon, COUNT(eq.id) AS cnt
        FROM subjects s
        LEFT JOIN error_questions eq ON s.id = eq.subject_id AND eq.user_id = :user_id
        GROUP BY s.id, s.name, s.icon
        HAVING cnt > 0
        ORDER BY cnt DESC
    """), {'user_id': user_id}).fetchall()

    return {
        'total_errors': result[0] if result else 0,
        'total_mastered': result[1] if result else 0,
        'mastery_rate': result[2] if result else 0,
        'subject_stats': [{'name': r[0], 'icon': r[1], 'count': r[2]} for r in subject_stats],
    }


def get_knowledge_gaps(user_id):
    """
    查找薄弱知识点: 子查询找出错误次数 >= 2 且未掌握的标签。
    面试常考的关联子查询。
    """
    from sqlalchemy import text
    rows = db.session.execute(text("""
        SELECT knowledge_tags, COUNT(*) AS err_cnt
        FROM error_questions
        WHERE user_id = :user_id
          AND mastered = 0
          AND error_count >= 2
          AND knowledge_tags IS NOT NULL
          AND knowledge_tags != ''
        GROUP BY knowledge_tags
        ORDER BY err_cnt DESC
        LIMIT 10
    """), {'user_id': user_id}).fetchall()

    return [{'tags': r[0], 'error_count': r[1]} for r in rows]


def get_practice_history(user_id, page=1, per_page=20):
    """
    分页查询刷题历史（按学科 JOIN），用于展示 LIMIT/OFFSET 用法。
    """
    from sqlalchemy import text
    offset = (page - 1) * per_page
    rows = db.session.execute(text("""
        SELECT eq.id, eq.question_text, eq.mastered, eq.error_count,
               eq.created_at, s.name AS subject_name
        FROM error_questions eq
        JOIN subjects s ON eq.subject_id = s.id
        WHERE eq.user_id = :user_id
        ORDER BY eq.updated_at DESC
        LIMIT :limit OFFSET :offset
    """), {
        'user_id': user_id,
        'limit': per_page,
        'offset': offset,
    }).fetchall()

    return [{
        'id': r[0], 'question_text': r[1], 'mastered': r[2],
        'error_count': r[3], 'created_at': r[4], 'subject_name': r[5],
    } for r in rows]
