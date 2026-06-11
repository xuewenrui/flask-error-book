"""
测试错题本模块（CRUD、掌握状态切换）
"""
from models import ErrorQuestion


class TestErrorBook:

    def test_error_book_page(self, logged_in_user):
        """错题本页面可访问"""
        client, user = logged_in_user
        rv = client.get('/error-book')
        assert rv.status_code == 200

    def test_add_error_page(self, logged_in_user):
        """添加错题页面可访问"""
        client, user = logged_in_user
        rv = client.get('/error-book/add')
        assert rv.status_code == 200
        assert '添加错题' in rv.data.decode('utf-8')

    def test_add_error_success(self, logged_in_user, db):
        """成功添加一道错题"""
        client, user = logged_in_user
        from models import Subject
        subject = Subject.query.first()

        rv = client.post('/error-book/add', data={
            'subject_id': subject.id,
            'question_text': 'Python 中列表和元组有什么区别？',
            'option_a': '列表可变，元组不可变',
            'option_b': '列表不可变，元组可变',
            'option_c': '两者完全相同',
            'option_d': '两者完全不相同',
            'correct_answer': 'A',
            'user_answer': 'B',
            'explanation': '列表使用[]，可修改；元组使用()，不可修改。',
            'knowledge_tags': 'Python,数据结构',
            'difficulty': 2,
        }, follow_redirects=True)
        assert rv.status_code == 200
        assert '错题添加成功' in rv.data.decode('utf-8')

        # 验证数据库
        error = ErrorQuestion.query.filter_by(user_id=user.id).first()
        assert error is not None
        assert error.question_text == 'Python 中列表和元组有什么区别？'
        assert error.correct_answer == 'A'
        assert 'Python' in error.knowledge_tags

    def test_add_error_missing_required_fields(self, logged_in_user):
        """缺少必填字段应失败"""
        client, user = logged_in_user
        rv = client.post('/error-book/add', data={
            'subject_id': '',
            'question_text': '',
            'correct_answer': '',
        })
        assert '必填项' in rv.data.decode('utf-8')

    def test_error_detail_page(self, logged_in_user, sample_error):
        """错题详情页可访问"""
        client, user = logged_in_user
        error, _ = sample_error
        rv = client.get(f'/error-book/{error.id}')
        assert rv.status_code == 200
        assert '1+1等于几' in rv.data.decode('utf-8')

    def test_toggle_mastered(self, logged_in_user, sample_error, db):
        """切换掌握状态"""
        client, user = logged_in_user
        error, _ = sample_error
        assert error.mastered is False

        rv = client.post(f'/error-book/{error.id}/toggle-mastered')
        data = rv.get_json()
        assert data['success'] is True
        assert data['mastered'] is True

        # 再次切换
        rv = client.post(f'/error-book/{error.id}/toggle-mastered')
        data = rv.get_json()
        assert data['mastered'] is False

    def test_delete_error(self, logged_in_user, sample_error, db):
        """删除错题"""
        client, user = logged_in_user
        error, _ = sample_error
        rv = client.post(f'/error-book/{error.id}/delete', follow_redirects=True)
        assert '错题已删除' in rv.data.decode('utf-8')
        assert ErrorQuestion.query.get(error.id) is None

    def test_filter_by_subject(self, logged_in_user, sample_error, db):
        """按学科筛选错题"""
        client, user = logged_in_user
        error, _ = sample_error

        # 添加一道不同学科的错题
        from models import Subject
        eng = Subject.query.filter_by(name='英语').first()
        from models import ErrorQuestion as EQ
        eq2 = EQ(
            user_id=user.id,
            subject_id=eng.id,
            question_text='What is the past tense of go?',
            option_a='go', option_b='went', option_c='gone', option_d='going',
            correct_answer='B',
        )
        db.session.add(eq2)
        db.session.commit()

        # 按数学筛选
        math = Subject.query.filter_by(name='数学').first()
        rv = client.get(f'/error-book?subject_id={math.id}')
        assert rv.status_code == 200
        content = rv.data.decode('utf-8')
        assert '1+1等于几' in content
        assert 'past tense' not in content
