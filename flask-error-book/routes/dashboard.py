"""
仪表盘和知识图谱路由
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import ErrorQuestion, Subject, get_dashboard_stats, get_knowledge_gaps
from cache import get_cache, set_cache
import json


def init_dashboard_routes():
    from routes import dashboard_bp

    @dashboard_bp.route('/dashboard')
    @login_required
    def dashboard():
        """学习仪表盘"""
        # 尝试从 Redis 缓存读取统计数据
        cache_key = f'dashboard:user:{current_user.id}'
        cached = get_cache(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return render_template('dashboard.html', **data)
            except Exception:
                pass

        # 使用原生 SQL 获取统计数据
        stats = get_dashboard_stats(current_user.id)
        total_errors = stats['total_errors']
        total_mastered = stats['total_mastered']
        mastery_rate = stats['mastery_rate']
        subject_stats = stats['subject_stats']

        # 最近错题
        recent_errors = ErrorQuestion.query.filter_by(user_id=current_user.id) \
            .order_by(ErrorQuestion.created_at.desc()).limit(5).all()

        # 所有标签
        all_tags_set = set()
        for e in ErrorQuestion.query.filter_by(user_id=current_user.id).all():
            if e.knowledge_tags:
                for t in e.knowledge_tags.split(','):
                    t = t.strip()
                    if t:
                        all_tags_set.add(t)
        all_tags = sorted(all_tags_set)

        # 缓存到 Redis（5 分钟过期）
        template_data = {
            'total_errors': total_errors,
            'total_mastered': total_mastered,
            'mastery_rate': mastery_rate,
            'subject_stats': subject_stats,
            'recent_errors': recent_errors,  # ORM 对象不能直接序列化，单独处理
            'all_tags': all_tags,
        }
        try:
            set_cache(cache_key, json.dumps({
                'total_errors': total_errors,
                'total_mastered': total_mastered,
                'mastery_rate': mastery_rate,
                'subject_stats': subject_stats,
                'recent_errors': [],  # 不缓存 ORM 对象
                'all_tags': all_tags,
            }), expire_seconds=300)
        except Exception:
            pass

        return render_template(
            'dashboard.html',
            total_errors=total_errors,
            total_mastered=total_mastered,
            mastery_rate=mastery_rate,
            subject_stats=subject_stats,
            recent_errors=recent_errors,
            all_tags=all_tags,
        )

    @dashboard_bp.route('/knowledge-map')
    @login_required
    def knowledge_map():
        """知识图谱"""
        all_tags_set = set()
        tag_stats = []
        for e in ErrorQuestion.query.filter_by(user_id=current_user.id).all():
            if e.knowledge_tags:
                for t in e.knowledge_tags.split(','):
                    t = t.strip()
                    if t and t not in all_tags_set:
                        all_tags_set.add(t)
                        count = ErrorQuestion.query.filter_by(user_id=current_user.id) \
                            .filter(ErrorQuestion.knowledge_tags.contains(t)).count()
                        tag_stats.append({'name': t, 'count': count})

        # 按错题数降序排列
        tag_stats.sort(key=lambda x: x['count'], reverse=True)
        return render_template('knowledge_map.html', tag_stats=tag_stats)

    @dashboard_bp.route('/knowledge-gaps')
    @login_required
    def knowledge_gaps():
        """薄弱知识点分析（原生SQL示例）"""
        gaps = get_knowledge_gaps(current_user.id)
        return render_template('knowledge_map.html', tag_stats=gaps)

    @dashboard_bp.route('/api/export-error-book', methods=['POST'])
    @login_required
    def export_error_book():
        """导出错题本为 Markdown（尝试异步，失败则同步）"""
        from tasks import start_export_task
        result = start_export_task(current_user.id)

        if result.get('async'):
            return jsonify({
                'success': True,
                'async': True,
                'task_id': result['task_id'],
                'message': '导出任务已提交，将在后台处理。'
            })
        else:
            return jsonify({
                'success': True,
                'async': False,
                'filepath': result.get('filepath'),
                'count': result.get('count'),
                'message': f'已导出 {result.get("count", 0)} 道错题。'
            })

    return dashboard_bp
