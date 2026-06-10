# 部署到 Render（免费）的完整指南

## 1. 方案选择：为什么用 Render？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Render Free** ✅ | 免费 HTTPS 域名；无需开着电脑；自动部署 | 冷启动慢（30秒）；每月550小时 |
| ngrok | 即时部署；延迟低 | 域名变来变去；要开着电脑 |
| Railway | 体验好 | **已取消免费计划**（$5/月起步） |

> 👉 **选 Render**：不用开电脑、免费 HTTPS、域名固定。

## 2. 第一步：准备代码（增加 gunicorn + Procfile）

在项目目录下打开终端，依次操作：

### （1）先更新 requirements.txt

在原来 `G:\Users\工作文件夹\flask-error-book\requirements.txt` 的末尾加入一行：
```
gunicorn==23.0.0
```

### （2）在项目目录新建一个文件 `Procfile`（不带扩展名）

内容只有一行：
```
web: gunicorn app:app
```

### （3）在 `app.py` 最后加两行，确保数据库自动初始化

找到 `app.py` 的末尾这几行：
```
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_subjects()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

改成（保留原有内容，文件最末尾额外增加）：
```
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_subjects()
    app.run(debug=True, host='0.0.0.0', port=5000)

# ===== Render 启动时自动建表 =====
with app.app_context():
    db.create_all()
    seed_subjects()
```

## 3. 为什么要在这么操作 -- 你需要确保数据库能正常创建

### 如何创建&启动？

**先在本地运行一次**，确保数据库文件 `instance/error_book.db` 已生成：
```bash
cd "G:\Users\工作文件夹\flask-error-book\"
python app.py
```

看到：
```
 * Running on http://127.0.0.1:5000
```

然后 `Ctrl+C` 关闭。

## 4. 第二步（去 Render 上部署）

### 4.1 注册 Render 账户

浏览器打开 https://dashboard.render.com/
→ 点 "Sign Up"
→ 选择 "GitHub" 方式注册（最简单的，后续自动化部署必须）

### 4.2 将项目上传到 GitHub

**第一步：在 GitHub 上创建新仓库**

浏览器打开 https://github.com/new
→ Repository name 填：`flask-error-book`
→ 选 **Public**（免费私有仓库其实也行）
→ 点 "Create repository"

创建后，GitHub 会跳转到一个页面，显示类似：
```
git remote add origin https://github.com/你的用户名/flask-error-book.git
git branch -M main
git push -u origin main
```

**第二步：将项目推送到 GitHub**

在 VS Code 或终端，打开项目目录，执行：
```bash
cd "G:\Users\工作文件夹\flask-error-book\"

git init
git add .
git commit -m "first commit: Flask error book app"
git branch -M main
git remote add origin https://github.com/你的用户名/flask-error-book.git
git push -u origin main
```

如果报 `error: remote origin already exists`：
```bash
git remote remove origin
git remote add origin https://github.com/你的用户名/flask-error-book.git
git push -u origin main
```

### 4.3 Render 上创建 Web Service

1. 回到 https://dashboard.render.com/
2. 点右上角的 **"New +"** 按钮 → 选 **"Web Service"**
3. 在弹出的授权页面中，选择刚才的仓库 `flask-error-book` → 点 "Connect"
4. 填配置：
   - **Name**：随便取，比如 `ai-error-book`（这会变成域名 `ai-error-book.onrender.com`）
   - **Region**：选 `Singapore`（离中国最近，访问更快）
   - **Branch**：`main`
   - **Runtime**：`Python 3`
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`gunicorn app:app`
   - **Free Instance**：选 Free（$0/month）
5. 拉到最下面，点 **"Create Web Service"**

### 4.4 部署会自己跑

创建后 Render 会自动开始部署（选新加坡节点，大概 3~6 分钟）：
1. 先 `pip install -r requirements.txt` 安装依赖
2. 再用 `gunicorn app:app` 启动
3. 部署成功后，页面顶部会显示绿色的 "Live" 和一个链接

点击那个链接就是你的网站！

例：`https://ai-error-book.onrender.com`

## 5. 第三步：验证

打开浏览器 → 访问 Render 给的那个链接（比如 `https://ai-error-book.onrender.com`）

预期行为：
- ✅ 回车后自动跳转到 `/login` 登录页面
- ✅ 能看到登录表单（用户名 + 密码输入框）
- ✅ 点"立即注册"可以跳转到注册页面
- ✅ 注册一个账号 → 登录进去 → 仪表盘正常显示
- ✅ 加一条错题 → 错题本列表里能看到 → 刷题能正常出题

如果看到 502 / "应用启动失败" / 加载很久 → 见下方的排查

## 6. 常见报错（如果出现）

| 报错 | 怎么办 |
|------|--------|
| 浏览器打不开，DNS 找不到 | 等 30 秒再试（冷启动慢，正常） |
| 页面是 502 Bad Gateway | 1. 检查 Render 里的 "Logs" 有没有报错；2. 是否忘记加 gunicorn；3. 是否忘记把 `Procfile` + `requirements.txt` push 上去 |
| `ModuleNotFoundError: No module named 'flask'` | `requirements.txt` 里检查是否包含 `Flask` |
| `ImportError: gunicorn` | `requirements.txt` 里是否包含 `gunicorn` |
| 登录后回退到登录页（无限重定向） | `SECRET_KEY` 需要固定（上面已经做了） |
| `git push` 报错 | 检查 GitHub 仓库是否创建成功，远程地址是否正确 |

## 7. 关于数据库

这个项目用的是 SQLite，数据库是一个文件 `error_book.db`，存在项目目录下。

- **Render 上的限制**：每次部署或重启，数据库都会**重置**（变成初始空库）——因为 Render 免费版没有持久磁盘
- **如果不在乎**：每次部署后重新注册用户、导入数据就行
- **如果需要持久化**：改用 Supabase（免费 PostgreSQL，有 500MB）= 后续再改

## 8. 终极办法（如果 Render 一直搞不定）

如果你不想折腾 GitHub（嫌麻烦），可以用 ngrok 直接暴露本地的 Flask 服务：

1. 到 https://ngrok.com/ 注册
2. 下载 ngrok.exe（Windows 版）
3. 打开本地终端，启动 Flask：
```bash
cd "G:\Users\工作文件夹\flask-error-book\"
python app.py
```
4. 再开一个终端，进入 ngrok 所在的文件夹：
```bash
ngrok config add-authtoken 你的token
ngrok http 5000
```
5. ngrok 会给一个类似 `https://abc123.ngrok-free.app` 的域名
6. 发给别人这个域名就能访问了（前提你的电脑不关机）

**ngrok 对比 Render**：
- ✅：立刻生效、本地调试方便、不需要 GitHub
- ❌：电脑关机就不能用了、域名不固定（免费版）

---

## 9. 这么写的部署说明（用于中期报告）

### 系统部署方案

本项目采用 Render 云平台进行免费部署（或 ngrok 内网穿透作为备选方案）。部署架构如下：

1. **代码托管**：项目源码托管于 GitHub 仓库，便于版本管理与自动部署
2. **应用部署**：通过 Render Web Service 部署 Flask + gunicorn，选择新加坡节点以优化中国地区访问速度
3. **数据库**：本地采用 SQLite，正式部署时使用 Render 持久磁盘（或迁移至 Supabase 免费 PostgreSQL）
4. **访问方式**：部署完成后获得 HTTPS 加密访问域名（例如 `https://ai-error-book.onrender.com`），可通过任何设备外网访问

**部署步骤总结**：
1. 准备 `requirements.txt`（含 Flask + gunicorn）和 `Procfile`
2. 将代码推送至 GitHub 仓库
3. 在 Render 控制台创建 Web Service，指定 Python 3 运行时
4. 配置启动命令为 `gunicorn app:app`
5. 等待约 3-5 分钟完成自动构建和部署
6. 访问生成的 HTTPS 链接测试功能完整性
