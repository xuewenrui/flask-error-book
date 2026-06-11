"""
错题本相关路由（CRUD、列表、筛选）
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import ErrorQuestion, Subject


def init_error_book_routes():
    from routes import error_book_bp

    @error_book_bp.route('')
    @login_required
    def error_book():
        """错题本列表"""
        subject_id = request.args.get('subject_id', type=int)
        tag = request.args.get('tag', '').strip()

        query = ErrorQuestion.query.filter_by(user_id=current_user.id)

        if subject_id:
            query = query.filter_by(subject_id=subject_id)

        if tag:
            query = query.filter(ErrorQuestion.knowledge_tags.contains(tag))

        errors = query.order_by(ErrorQuestion.created_at.desc()).all()
        subjects = Subject.query.all()
        # 收集所有标签
        all_tags_set = set()
        for e in ErrorQuestion.query.filter_by(user_id=current_user.id).all():
            if e.knowledge_tags:
                for t in e.knowledge_tags.split(','):
                    t = t.strip()
                    if t:
                        all_tags_set.add(t)
        all_tags = sorted(all_tags_set)

        return render_template(
            'error_book.html',
            errors=errors,
            subjects=subjects,
            all_tags=all_tags,
            current_subject=subject_id,
            current_tag=tag
        )

    @error_book_bp.route('/add', methods=['GET', 'POST'])
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
            return redirect(url_for('error_book.error_book'))

        return render_template('add_error.html', subjects=subjects)

    @error_book_bp.route('/<int:error_id>')
    @login_required
    def error_detail(error_id):
        """错题详情"""
        error = ErrorQuestion.query.get_or_404(error_id)
        if error.user_id != current_user.id:
            flash('无权访问', 'error')
            return redirect(url_for('error_book.error_book'))
        return render_template('error_detail.html', error=error)

    @error_book_bp.route('/<int:error_id>/toggle-mastered', methods=['POST'])
    @login_required
    def toggle_mastered(error_id):
        """切换掌握状态"""
        error = ErrorQuestion.query.get_or_404(error_id)
        if error.user_id != current_user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403

        error.mastered = not error.mastered
        db.session.commit()
        return jsonify({'success': True, 'mastered': error.mastered})

    @error_book_bp.route('/<int:error_id>/delete', methods=['POST'])
    @login_required
    def delete_error(error_id):
        """删除错题"""
        error = ErrorQuestion.query.get_or_404(error_id)
        if error.user_id != current_user.id:
            flash('无权操作', 'error')
            return redirect(url_for('error_book.error_book'))

        db.session.delete(error)
        db.session.commit()
        flash('错题已删除', 'info')
        return redirect(url_for('error_book.error_book'))

    return error_book_bp
