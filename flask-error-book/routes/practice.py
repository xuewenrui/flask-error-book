"""
刷题相关路由（出题配置、答题、批改、结果）
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from extensions import db
from models import ErrorQuestion, Subject


def init_practice_routes():
    from routes import practice_bp

    @practice_bp.route('')
    @login_required
    def practice():
        """刷题页面入口"""
        subjects = Subject.query.all()
        all_tags_set = set()
        for e in ErrorQuestion.query.filter_by(user_id=current_user.id).all():
            if e.knowledge_tags:
                for t in e.knowledge_tags.split(','):
                    t = t.strip()
                    if t:
                        all_tags_set.add(t)
        all_tags = sorted(all_tags_set)
        return render_template('practice.html', subjects=subjects, all_tags=all_tags)

    @practice_bp.route('/start', methods=['POST'])
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
            return redirect(url_for('practice.practice'))

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

        return redirect(url_for('practice.practice_session'))

    @practice_bp.route('/session')
    @login_required
    def practice_session():
        """答题页面"""
        questions = session.get('practice_questions', [])
        current_index = session.get('current_index', 0)

        if not questions:
            flash('没有刷题数据，请重新开始', 'warning')
            return redirect(url_for('practice.practice'))

        if current_index >= len(questions):
            return redirect(url_for('practice.practice_result'))

        question = questions[current_index]
        total = len(questions)
        options = [o for o in question['options'] if o['text']]

        return render_template(
            'practice_session.html',
            question=question,
            current_index=current_index,
            total=total,
            options=options
        )

    @practice_bp.route('/answer', methods=['POST'])
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

    @practice_bp.route('/next', methods=['POST'])
    @login_required
    def next_question():
        """下一题"""
        session['current_index'] = session.get('current_index', 0) + 1
        return jsonify({'success': True})

    @practice_bp.route('/result')
    @login_required
    def practice_result():
        """刷题结果"""
        questions = session.get('practice_questions', [])
        answers = session.get('practice_answers', {})

        total = len(questions)
        correct_count = sum(1 for a in answers.values() if a['is_correct'])

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

    return practice_bp
