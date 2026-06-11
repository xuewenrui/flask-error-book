"""
测试刷题模块（出题配置、答题、成绩计算）
"""
import json


class TestPractice:

    def test_practice_page(self, logged_in_user):
        """刷题入口可访问"""
        client, user = logged_in_user
        rv = client.get('/practice')
        assert rv.status_code == 200
        assert '开始刷题' in rv.data.decode('utf-8')

    def test_start_practice_no_errors(self, logged_in_user):
        """没有错题时开始刷题应提示"""
        client, user = logged_in_user
        rv = client.post('/practice/start', data={
            'subject_id': '',
            'tag': '',
            'count': 5,
        }, follow_redirects=True)
        assert '没有符合条件的错题' in rv.data.decode('utf-8')

    def test_start_practice_with_errors(self, logged_in_user, sample_error):
        """有错题时开始刷题应跳转到答题页"""
        client, user = logged_in_user
        error, _ = sample_error

        rv = client.post('/practice/start', data={
            'subject_id': '',
            'tag': '',
            'count': 5,
        }, follow_redirects=True)
        assert rv.status_code == 200
        # 应跳转到答题页
        assert '第' in rv.data.decode('utf-8')

    def test_submit_answer(self, logged_in_user, sample_error):
        """提交答案并验证判分逻辑"""
        client, user = logged_in_user
        error, _ = sample_error
        # 正确答案是 B

        # 先开始刷题
        client.post('/practice/start', data={
            'subject_id': '',
            'tag': '',
            'count': 1,
        })

        # 提交正确答案
        with client.session_transaction() as sess:
            assert 'practice_questions' in sess
            assert len(sess['practice_questions']) == 1

        rv = client.post('/practice/answer', data={'answer': 'B'})
        data = rv.get_json()
        assert data['success'] is True
        assert data['is_correct'] is True

    def test_submit_wrong_answer(self, logged_in_user, sample_error):
        """提交错误答案"""
        client, user = logged_in_user

        client.post('/practice/start', data={
            'subject_id': '',
            'tag': '',
            'count': 1,
        })

        rv = client.post('/practice/answer', data={'answer': 'A'})
        data = rv.get_json()
        assert data['is_correct'] is False
        assert data['correct_answer'] == 'B'

    def test_practice_result_page(self, logged_in_user, sample_error):
        """刷题结果页面"""
        client, user = logged_in_user

        client.post('/practice/start', data={
            'subject_id': '',
            'tag': '',
            'count': 1,
        })

        # 答完题
        client.post('/practice/answer', data={'answer': 'B'})

        # 模拟完成所有题后跳转
        with client.session_transaction() as sess:
            sess['current_index'] = 1  # 超过题目数

        rv = client.get('/practice/result')
        assert rv.status_code == 200
        assert '刷题结果' in rv.data.decode('utf-8')
