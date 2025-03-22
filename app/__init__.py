from flask import Flask, url_for, request, redirect, render_template,session,flash,abort
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from time import strftime
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = '123456'
app.jinja_env.auto_reload = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
db = SQLAlchemy(app)   # SQLAlchemy
from flask_socketio import SocketIO

# app.config['TEMPLATE_FOLDER'] = 'templates'
socketio = SocketIO(app, cors_allowed_origins='*')
connected_sids = set()  # 存放已连接的客户端
from app import models,views
from .models import Student,Teacher

@socketio.on('connect')
def on_connect():
    connected_sids.add(request.sid)
    print(f'{request.sid} 已连接')


@socketio.on('disconnect')
def on_disconnect():
    connected_sids.remove(request.sid)
    print(f'{request.sid} 已断开')

@socketio.on('message')
def handle_message(message):
    """收消息"""
    data = message['data']
    print(f'{request.sid} {data}')

@app.route('/',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(time)
        if len(username) ==8:
            teachers = Teacher.query.filter(Teacher.t_id == username).first()
            if teachers:
                if teachers.t_password == password:
                    flash("登陆成功")
                    session['username'] = username
                    session['id'] = teachers.t_id
                    session['name'] = teachers.t_name
                    session['role'] = "teacher"
                    session['attend'] = []
                    if teachers.before:
                        session['time'] = teachers.before
                    else:
                        session['time'] = time
                    teachers.before = time
                    db.session.commit()
                    return redirect(url_for('teacher.home'))
                else:
                    flash("密码错误，请重试")
            else:
                flash("工号错误，请重试")
        else:
            flash("账号不合法，请用学号/工号登录")
    return render_template('login.html')

@app.route('/logout')
def logout():
    # students = Student.query.filter(Student.s_id == session['id']).first()
    # students.num = session['num']
    # db.session.commit()
    session.clear()
    return render_template('login.html')


#拦截器
@app.before_request
def before():
    list = ['png','css','js','ico','xlsx','xls','jpg']
    url_after = request.url.split('.')[-1]
    if url_after in list:
        return None
    url = str(request.endpoint)
    role_ = url.split('.')[0]

    if role_=="student" or role_=='None':
        return None
    if url == 'logout':
        return None
    if url == "login":
        if 'username' in session:
            return redirect("logout")
        else:
            return None
    else:
        if 'username' in session:
            role = url.split('.')[0]
            if role == session['role']:
                return None
            else:
                new_endpoint = session['role'] + '.' + 'home'
                print(role)
                flash('权限不足')
                return redirect(url_for(new_endpoint))
        else:
            flash("未登录")
            return redirect('/')