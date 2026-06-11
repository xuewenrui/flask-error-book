"""
Celery 异步任务模块。
- 异步导出错题本为 Markdown 文件
- Redis 不可用时降级为同步执行

启动 Worker: celery -A tasks.celery worker --loglevel=info
依赖: Redis（作为消息代理）
"""
import os
from celery import Celery

# Celery 实例
# 通过 REDIS_URL 配置 broker，默认连本地 Redis
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery = Celery(
    'flask_error_book',
    broker=redis_url,
    backend=redis_url,  # 结果也存 Redis
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 单任务最长 5 分钟
    task_soft_time_limit=240,
)

# ---- 实际任务定义 ----

@celery.task(bind=True, name='export_error_book_markdown')
def export_error_book_markdown(self, user_id, output_dir=None):
    """
    异步导出用户的所有错题为 Markdown 文件。
    参数:
        user_id: 用户 ID
        output_dir: 输出目录（默认项目根目录 exports/）
    返回:
        {'status': 'ok', 'filepath': '...', 'count': N}
    """
    # 在 worker 进程中需要创建 Flask app context
    from flask import Flask
    from config import Config
    from extensions import db
    from models import ErrorQuestion, Subject

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        errors = ErrorQuestion.query.filter_by(user_id=user_id).order_by(
            ErrorQuestion.subject_id, ErrorQuestion.created_at.desc()
        ).all()

        if not errors:
            return {'status': 'ok', 'filepath': None, 'count': 0}

        # 生成 Markdown 内容
        lines = [
            '# 📝 我的错题本 - 导出报告',
            '',
            f'共 {len(errors)} 道错题',
            '',
            '---',
            '',
        ]

        current_subject = None
        for e in errors:
            subject = Subject.query.get(e.subject_id)
            subject_name = subject.name if subject else '未分类'

            if subject_name != current_subject:
                current_subject = subject_name
                lines.append(f'## {subject.icon if subject else "📚"} {subject_name}')
                lines.append('')

            mastery_mark = '✅ 已掌握' if e.mastered else '❌ 未掌握'
            lines.append(f'### {e.id}. {e.question_text}')
            lines.append(f'**状态**: {mastery_mark} | **难度**: {"⭐" * e.difficulty} | **错误次数**: {e.error_count}')
            lines.append('')

            # 选项
            if e.option_a:
                opts = []
                for key in ['A', 'B', 'C', 'D']:
                    opt_text = getattr(e, f'option_{key.lower()}', None)
                    if opt_text:
                        correct = key == e.correct_answer
                        opts.append(f'- {key}{" ✅" if correct else ""}. {opt_text}')
                if opts:
                    lines.extend(opts)
                    lines.append('')

            if e.explanation:
                lines.append(f'**解析**: {e.explanation}')
                lines.append('')

            if e.knowledge_tags:
                tags = '、'.join(t.strip() for t in e.knowledge_tags.split(',') if t.strip())
                lines.append(f'**知识点**: {tags}')
                lines.append('')

            lines.append('---')
            lines.append('')

        content = '\n'.join(lines)

        # 输出目录
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        os.makedirs(output_dir, exist_ok=True)

        filename = f'error_book_user{user_id}.md'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            'status': 'ok',
            'filepath': filepath,
            'count': len(errors),
        }


def export_error_book_sync(user_id, output_dir=None):
    """
    同步版本（Celery 不可用时的 fallback）。
    直接在当前进程中执行。
    """
    import os
    from models import ErrorQuestion, Subject
    from extensions import db

    errors = ErrorQuestion.query.filter_by(user_id=user_id).order_by(
        ErrorQuestion.subject_id, ErrorQuestion.created_at.desc()
    ).all()

    if not errors:
        return {'status': 'ok', 'filepath': None, 'count': 0}

    lines = ['# 📝 我的错题本 - 导出报告', '', f'共 {len(errors)} 道错题', '', '---', '']
    current_subject = None
    for e in errors:
        subject = Subject.query.get(e.subject_id)
        subject_name = subject.name if subject else '未分类'
        if subject_name != current_subject:
            current_subject = subject_name
            lines.append(f'## {subject.icon if subject else "📚"} {subject_name}')
            lines.append('')
        mastery_mark = '✅ 已掌握' if e.mastered else '❌ 未掌握'
        lines.append(f'### {e.id}. {e.question_text}')
        lines.append(f'**状态**: {mastery_mark} | **难度**: {"⭐" * e.difficulty} | **错误次数**: {e.error_count}')
        lines.append('')
        if e.option_a:
            for key in ['A', 'B', 'C', 'D']:
                opt_text = getattr(e, f'option_{key.lower()}', None)
                if opt_text:
                    correct = key == e.correct_answer
                    lines.append(f'- {key}{" ✅" if correct else ""}. {opt_text}')
            lines.append('')
        if e.explanation:
            lines.append(f'**解析**: {e.explanation}')
            lines.append('')
        if e.knowledge_tags:
            tags = '、'.join(t.strip() for t in e.knowledge_tags.split(',') if t.strip())
            lines.append(f'**知识点**: {tags}')
            lines.append('')
        lines.append('---')
        lines.append('')

    content = '\n'.join(lines)
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    os.makedirs(output_dir, exist_ok=True)
    filename = f'error_book_user{user_id}.md'
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'status': 'ok', 'filepath': filepath, 'count': len(errors)}


def start_export_task(user_id):
    """
    智能导出: Redis 可用时走 Celery 异步；不可用时同步执行。
    """
    from extensions import get_redis
    if get_redis() is not None:
        try:
            result = export_error_book_markdown.delay(user_id)
            return {'async': True, 'task_id': result.id}
        except Exception:
            pass
    # Fallback 同步
    return export_error_book_sync(user_id)
