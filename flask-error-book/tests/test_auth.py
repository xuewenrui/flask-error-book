"""
测试认证模块（注册、登录、登出、密码校验）
"""
from models import User


class TestAuth:

    def test_register_page_accessible(self, client):
        """注册页面可以正常访问"""
        rv = client.get('/register')
        assert rv.status_code == 200
        assert '创建账户' in rv.data.decode('utf-8')

    def test_register_success(self, client, db):
        """成功注册新用户"""
        rv = client.post('/register', data={
            'username': 'newuser',
            'password': 'testtest',
            'confirm_password': 'testtest',
        }, follow_redirects=True)
        assert rv.status_code == 200
        assert '注册成功' in rv.data.decode('utf-8')
        # 确认数据库中有该用户
        user = User.query.filter_by(username='newuser').first()
        assert user is not None

    def test_register_password_mismatch(self, client):
        """两次密码不一致应失败"""
        rv = client.post('/register', data={
            'username': 'newuser',
            'password': 'testtest',
            'confirm_password': 'wrong',
        })
        assert '两次输入的密码不一致' in rv.data.decode('utf-8')

    def test_register_short_password(self, client):
        """密码过短应失败"""
        rv = client.post('/register', data={
            'username': 'newuser',
            'password': '12345',
            'confirm_password': '12345',
        })
        assert '密码长度不能少于6位' in rv.data.decode('utf-8')

    def test_register_duplicate_username(self, client, db):
        """重复用户名应失败"""
        # 先注册一次
        client.post('/register', data={
            'username': 'dupuser',
            'password': 'testtest',
            'confirm_password': 'testtest',
        })
        # 再注册同名
        rv = client.post('/register', data={
            'username': 'dupuser',
            'password': 'testtest',
            'confirm_password': 'testtest',
        })
        assert '用户名已存在' in rv.data.decode('utf-8')

    def test_login_success(self, client, db):
        """登录成功"""
        # 先注册
        client.post('/register', data={
            'username': 'loginuser',
            'password': 'password123',
            'confirm_password': 'password123',
        })
        # 再登录
        rv = client.post('/login', data={
            'username': 'loginuser',
            'password': 'password123',
        }, follow_redirects=True)
        assert rv.status_code == 200
        assert '欢迎回来' in rv.data.decode('utf-8')

    def test_login_wrong_password(self, client, db):
        """密码错误应失败"""
        client.post('/register', data={
            'username': 'loginuser2',
            'password': 'password123',
            'confirm_password': 'password123',
        })
        rv = client.post('/login', data={
            'username': 'loginuser2',
            'password': 'wrongpassword',
        })
        assert '用户名或密码错误' in rv.data.decode('utf-8')

    def test_login_required_redirect(self, client):
        """未登录访问受保护页面应重定向到登录页"""
        rv = client.get('/dashboard', follow_redirects=True)
        assert rv.status_code == 200
        assert '登录' in rv.data.decode('utf-8')

    def test_logout(self, logged_in_user):
        """登出后无法访问受保护页面"""
        client, user = logged_in_user
        rv = client.get('/logout', follow_redirects=True)
        assert '成功退出登录' in rv.data.decode('utf-8')
        # 退出后访问仪表盘应重定向
        rv = client.get('/dashboard', follow_redirects=True)
        assert '登录' in rv.data.decode('utf-8')

    def test_password_hashing(self):
        """密码哈希不应以明文存储"""
        user = User(username='test')
        user.set_password('secret123')
        assert user.password_hash != 'secret123'
        assert user.check_password('secret123') is True
        assert user.check_password('wrong') is False
