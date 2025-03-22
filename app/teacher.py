from flask import Blueprint, render_template, redirect, request, Response, session, flash, jsonify, url_for,Flask

import app
from app import db
from .models import Teacher, Faces, Course, SC, Attendance, Time_id, Student,AttendanceSheet,Student_info,IssuesList
from sqlalchemy.sql import exists
import base64
import os
from app import get_faces_from_camera as gf
from datetime import timedelta
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import dlib
import time
import pandas as pd
import xlsxwriter
import xlwt
from io import BytesIO
from urllib.parse import quote
from flask import send_file
from sqlalchemy import create_engine,func
from datetime import datetime
from flask_socketio import SocketIO
import json
teacher = Blueprint('teacher', __name__, static_folder="static")
# 本次签到的所有人员信息
attend_records = []
# 本次签到的开启时间
the_now_time = ''

@teacher.route('/home')
def home():
    flag = session['id'][0]
    print(flag)
    courses = {}
    course = db.session.query(Course).filter(Course.t_id == session['id']).all()
    for c in course:
        num = db.session.query(SC).filter(SC.c_id == c.c_id).count()
        courses[c] = num
    return render_template('teacher/teacher_home.html', before=session['time'], flag=flag, name=session['name'],
                           courses=courses)




# 老师端
@teacher.route('/reco_faces')
def reco_faces():
    return render_template('teacher/index.html')


# def gen(camera, cid):
#     while True:
#         frame = camera.get_frame(cid)
#         # 使用generator函数输出视频流， 每次请求输出的content类型是image/jpeg
#         print(frame)
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


#人脸识别view函数（视图函数）
# @teacher.route('/video_feed')
# def video_feed():
#     return Response(gen(VideoCamera(), session['course']),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')


@teacher.route('/all_course')
def all_course():
    teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    return render_template('teacher/course_attend.html', courses=teacher_all_course)

@teacher.route('/barrage')
def barrage():
    return render_template('teacher/barrage.html')

# 开启签到
@teacher.route('/records', methods=["POST"])
def records():
    # 开启签到后，开始单次的记录
    result = {}
    try:

        # global attend_records
        # attend_records = []
        db.session.query(AttendanceSheet).delete()
        db.session.commit()
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # cid = request.form.get("id")
        cid = request.get_json().get("id")
        print(cid)
        session['course'] = cid
        session['now_time'] = now
        the_course_students = SC.query.filter(SC.c_id == cid)
        student_ids = []
        for sc in the_course_students:
            student_ids.append(sc.s_id)
        # 考勤记录初始化，所有人未签到
        all_students_attend = []
        for i in range(len(student_ids)):
            someone_addtend = AttendanceSheet(s_id=student_ids[i], c_id=cid, starttime=now, result='缺勤')
            all_students_attend.append(someone_addtend)
        db.session.add_all(all_students_attend)
        db.session.commit()
        result["msg"]="ok"
    except:
        result["msg"] = "error"
    return json.dumps(result, ensure_ascii=False)
    # return redirect(url_for('teacher.all_course'))


@teacher.route('/roll_call/<string:id>', methods=['POST', 'GET'])
def roll_call(id):
    # cid = request.form.get("id")
    cid=id
    print(cid)

    the_course_students = SC.query.filter(SC.c_id == cid)
    student_ids = []
    student_names = []
    for sc in the_course_students:
        student_ids.append(sc.s_id)
    students_info = Student.query.filter(Student.s_id.in_(student_ids))
    for st in students_info:
        student_names.append(st.s_name)

    comma_separated = ', '.join(student_names)
    return render_template('teacher/rall_call.html',namelists=comma_separated)


# 停止签到
@teacher.route('/stop_records', methods=['POST'])
def stop_records():
    result = {}
    try:
        start_time = session['now_time']
        all_students_attend = []
        all_attend=AttendanceSheet.query.all()
        datetime_endtime = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')+timedelta(minutes=15)
        datetime_starttime = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        for attend in all_attend:
            signin_time = attend.signintime
            if attend.signintime==None:
                attend.result = "缺勤"
            elif signin_time<=datetime_endtime and signin_time>=datetime_starttime:
                attend.result="已签到"
            elif signin_time>datetime_endtime:
                attend.result="迟到"
            someone_addtend = Attendance(s_id=attend.s_id, c_id=attend.c_id, time=start_time, result=attend.result,signintime=attend.signintime)
            all_students_attend.append(someone_addtend)
        db.session.add_all(all_students_attend)
        db.session.commit()
        result["msg"]="ok"
    except:
        result["msg"] = "error"
    return json.dumps(result, ensure_ascii=False)


@teacher.route('/select_all_records', methods=['GET', 'POST'])
def select_all_records():
    tid = session['id']
    dict = {}
    num = 0
    if request.method == 'POST':
        cid = request.form.get('course_id')
        sid = request.form.get('sid')
        select_time = request.form.get('time')
        if cid != '' and select_time != '':
            courses = db.session.query(Course).filter(Course.t_id == tid, Course.c_id == cid)
            num = 0
            for course in courses:
                # times = course.times.split('/')
                one_course_all_time_attends = {}
                # for i in range(1, len(times)):
                # one_time = times[i].split(' ')[0]
                # if one_time == select_time:
                if sid != '':
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           func.date(Attendance.time) == select_time,
                                                                           Attendance.s_id == sid).order_by(
                        's_id').all()
                else:
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           func.date(Attendance.time) == select_time).order_by(
                        's_id').all()
                tt = Time_id(id=num, time=select_time)
                num += 1
                one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            courses = db.session.query(Course).filter(Course.t_id == tid)
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        elif cid != '' and select_time == '':
            courses = db.session.query(Course).filter(Course.t_id == tid, Course.c_id == cid)
            num = 0
            for course in courses:
                # times = course.times.split('/')
                one_course_all_time_attends = {}
                # for i in range(1, len(times)):
                if sid == '':
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id).order_by(
                        's_id').all()
                else:
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           Attendance.s_id == sid).order_by(
                        's_id').all()
                tt = Time_id(id=num,time="all")
                num += 1
                one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        elif cid == '' and select_time != '':
            courses = db.session.query(Course).filter(Course.t_id == tid)
            num = 0
            for course in courses:
                # times = course.times.split('/')
                one_course_all_time_attends = {}
                # for i in range(1, len(times)):
                    # one_time = times[i].split(' ')[0]
                    # if one_time == select_time:
                if sid != '':
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           func.date(Attendance.time) == select_time,
                                                                           Attendance.s_id == sid).order_by(
                        's_id').all()
                else:
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           Attendance.time == select_time).order_by('s_id').all()
                tt = Time_id(id=num, time=select_time)
                num += 1
                one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
        else:  # cid = '' select=''
            courses = db.session.query(Course).filter(Course.t_id == tid)
            num = 0
            for course in courses:
                # times = course.times.split('/')
                one_course_all_time_attends = {}
                # for i in range(1, len(times)):
                if sid == '':
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id).order_by(
                        's_id').all()
                else:
                    one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id,
                                                                           Attendance.s_id == sid).all()
                tt = Time_id(id=num,time="all")
                num += 1
                one_course_all_time_attends[tt] = one_time_attends
                dict[course] = one_course_all_time_attends
            return render_template("teacher/show_records.html", dict=dict, courses=courses)
    courses = db.session.query(Course).filter(Course.t_id == tid)
    num = 0
    for course in courses:
        # times = course.times.split('/')
        one_course_all_time_attends = {}
        # for i in range(1, len(times)):
        one_time_attends = db.session.query(Attendance).filter(Attendance.c_id == course.c_id
                                                               ).order_by('s_id').all()
        tt = Time_id(id=num,time="all")
        num += 1
        one_course_all_time_attends[tt] = one_time_attends
        dict[course] = one_course_all_time_attends
    return render_template("teacher/show_records.html", dict=dict, courses=courses)


@teacher.route('/update_attend', methods=['POST'])
def update_attend():
    course = request.form.get('course_id')
    time = request.form.get('time')
    sid = request.form.get('sid')
    result = request.form.get('result')
    one_attend = Attendance.query.filter(Attendance.c_id == course, Attendance.s_id == sid,
                                         func.date(Attendance.time) == time).first()
    if(one_attend):
        one_attend.result = result
        db.session.commit()
    return redirect(url_for('teacher.select_all_records'))


@teacher.route('/course_management', methods=['GET', 'POST'])
def course_management():
    dict = {}
    if request.method == 'POST':
        cid = request.form.get('course_id')
        cname = request.form.get('course_name')
        sid = request.form.get('sid')
        sc = SC.query.filter(SC.c_id == cid, SC.s_id == sid).first()
        db.session.delete(sc)
        db.session.commit()
    teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    for course in teacher_all_course:
        course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                   SC.c_id == course.c_id).all()
        dict[course] = course_student
    return render_template('teacher/course_management.html', dict=dict)


@teacher.route('/new_course', methods=['POST'])
def new_course():
    max = db.session.query(Course).order_by(Course.c_id.desc()).first()
    if max:
        cid = int(max.c_id) + 1
        cid = str(cid)
    else:
        cid = str(100001)
    course = Course(c_id=cid, c_name=request.form.get('cname'), t_id=session['id'],times=request.form.get('time'),day=request.form.get('day'),\
                    week=request.form.get('week'),location=request.form.get('location'))
    db.session.add(course)
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


@teacher.route('/open_course', methods=['POST'])
def open_course():
    cid = request.form.get('course_id')
    course = Course.query.filter(Course.c_id == cid).first()
    course.flag = '可选课'
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


@teacher.route('/close_course', methods=['POST'])
def close_course():
    cid = request.form.get('course_id')
    course = Course.query.filter(Course.c_id == cid).first()
    course.flag = '不可选课'
    db.session.commit()
    return redirect(url_for('teacher.course_management'))


@teacher.route('/update_password', methods=['GET', 'POST'])
def update_password():
    tid = session['id']
    teacher = Teacher.query.filter(Teacher.t_id == tid).first()
    if request.method == 'POST':
        old = request.form.get('old')
        if old == teacher.t_password:
            new = request.form.get('new')
            teacher.t_password = new
            db.session.commit()
            flash('修改成功！')
        else:
            flash('旧密码错误，请重试')
    return render_template('teacher/update_password.html', teacher=teacher)


@teacher.route('/select_sc', methods=['GET', 'POST'])
def select_sc():
    dict = {}
    teacher_all_course = Course.query.filter(Course.t_id == session['id'])
    if request.method == 'POST':
        cid = request.form.get('course_id')
        sid = request.form.get('sid')
        if cid != '' and sid != '':
            course = Course.query.filter(Course.c_id == cid).first()
            dict[course] = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                     SC.c_id == course.c_id, SC.s_id == sid).all()
        elif cid != '' and sid == '':
            course = Course.query.filter(Course.c_id == cid).first()
            dict[course] = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                     SC.c_id == cid).all()
        elif cid == '' and sid != '':
            for course in teacher_all_course:
                course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                           SC.c_id == course.c_id, SC.s_id == sid).all()
                dict[course] = course_student
        else:
            for course in teacher_all_course:
                course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                           SC.c_id == course.c_id).all()
                dict[course] = course_student
        return render_template('teacher/student_getFace.html', dict=dict, courses=teacher_all_course)
    for course in teacher_all_course:
        course_student = db.session.query(Student).join(SC).filter(Student.s_id == SC.s_id,
                                                                   SC.c_id == course.c_id).all()
        dict[course] = course_student
    return render_template('teacher/student_getFace.html', dict=dict, courses=teacher_all_course)


@teacher.route('/open_getFace', methods=['POST'])
def open_getFace():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 1
    db.session.commit()
    return redirect(url_for('teacher.select_sc'))


@teacher.route('/close_getFace', methods=['POST'])
def close_getFace():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 0
    db.session.commit()
    return redirect(url_for('teacher.select_sc'))


@teacher.route('/delete_face', methods=['POST'])
def delete_face():
    sid = request.form.get('sid')
    student = Student.query.filter(Student.s_id == sid).first()
    student.flag = 1
    db.session.commit()

    os.remove('app/static/data/data_faces_from_camera/' + sid + '/1.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/2.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/3.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/4.jpg')
    os.remove('app/static/data/data_faces_from_camera/' + sid + '/5.jpg')
    return redirect(url_for('teacher.select_sc'))


def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['xlsx', 'xls'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# 检测学号存在
def sid_if_exist(sid):
    num = Student.query.filter(Student.s_id.in_(sid)).count()
    return num


# 检测课程号存在
def cid_if_exist(cid):
    num = Course.query.filter(Course.c_id.in_(cid)).count()
    return num


# 检测工号存在
def tid_if_exist(tid):
    num = Teacher.query.filter(Teacher.t_id.in_(tid)).count()
    return num


@teacher.route('upload_sc', methods=['POST'])
def upload_sc():
    sc_file = request.files.get('sc_file')
    msg = 'error'
    if sc_file:
        if allowed_file(sc_file.filename):
            sc_file.save(sc_file.filename)
            df = pd.DataFrame(pd.read_excel(sc_file.filename))
            df1 = df[['学号', '课程号']]
            sid = df1[['学号']].values.T.tolist()[:][0]
            cid = df1[['课程号']].values.T.tolist()[:][0]
            if df.isnull().values.any():
                flash('存在空信息')
            else:
                sid_diff = len(set(sid)) - sid_if_exist(sid)
                cid_diff = len(set(cid)) - cid_if_exist(cid)
                if sid_diff == 0 and cid_diff == 0:
                    flash('success')
                    for i in range(len(sid)):
                        sc = SC(s_id=sid[i], c_id=cid[i])
                        db.session.merge(sc)
                        i += 1
                    db.session.commit()

                elif sid_diff == 0 and cid_diff != 0:
                    flash('有课程号不存在')
                elif sid_diff != 0 and cid_diff == 0:
                    flash('有学号不存在')
                else:
                    flash('有学号、课程号不存在')
            os.remove(sc_file.filename)
        else:
            flash("只能识别'xlsx,xls'文件")
    else:
        flash('请选择文件')
    return redirect(url_for('teacher.course_management'))


@teacher.route('/select_all_teacher', methods=['POST', 'GET'])
def select_all_teacher():
    if request.method == 'POST':
        try:
            id = request.form.get('id')
            flag = request.form.get('flag')
            teacher = Teacher.query.get(id)
            if flag:
                sc = db.session.query(SC).join(Course).filter(SC.c_id == Course.c_id, Course.t_id == id).all()
                [db.session.delete(u) for u in sc]
                Course.query.filter(Course.t_id == id).delete()
            db.session.delete(teacher)
            db.session.commit()
        except Exception as e:
            print('Error:', e)
            flash("出发错误操作")
            return redirect(url_for('teacher.home'))
    teachers = Teacher.query.all()
    dict = {}
    for t in teachers:
        tc = Course.query.filter(Course.t_id == t.t_id).all()
        if tc:
            dict[t] = 1
        else:
            dict[t] = 0
    return render_template('teacher/all_teacher.html', dict=dict)


@teacher.route('/select_all_student', methods=['POST', 'GET'])
def select_all_student():
    if request.method == 'POST':
        try:
            id = request.form.get('id')
            flag = request.form.get('flag')
            student = Student.query.get(id)
            if flag:
                SC.query.filter(SC.s_id == id).delete()
            db.session.delete(student)
            db.session.commit()
        except Exception as e:
            print('Error:', e)
            flash("出发错误操作")
            return redirect(url_for('teacher.home'))
    students = Student.query.all()
    dict = {}
    for s in students:
        tc = SC.query.filter(SC.s_id == s.s_id).all()
        if tc:
            dict[s] = 1
        else:
            dict[s] = 0
    return render_template('teacher/all_student.html', dict=dict)


@teacher.route('/upload_teacher', methods=['POST'])
def upload_teacher():
    file = request.files.get('teacher_file')
    msg = 'error'
    if file:
        if allowed_file(file.filename):
            file.save(file.filename)
            df = pd.DataFrame(pd.read_excel(file.filename))
            df1 = df[['工号', '姓名', '密码']]
            id = df1[['工号']].values.T.tolist()[:][0]
            name = df1[['姓名']].values.T.tolist()[:][0]
            pwd = df1[['密码']].values.T.tolist()[:][0]
            if df.isnull().values.any() or len(id) == 0:
                flash('存在空信息')
            else:
                tid_diff = tid_if_exist(id)
                if tid_diff != 0:
                    flash('工号存在重复')
                else:
                    flash('success')
                    for i in range(len(id)):
                        t = Teacher(t_id=id[i], t_name=name[i], t_password=pwd[i])
                        db.session.add(t)
                        i += 1
                    db.session.commit()
            os.remove(file.filename)

        else:
            flash("只能识别'xlsx,xls'文件")
    else:
        flash('请选择文件')
    return redirect(url_for('teacher.select_all_teacher'))


@teacher.route('/upload_student', methods=['POST'])
def upload_student():
    file = request.files.get('student_file')
    msg = 'error'
    if file:
        if allowed_file(file.filename):
            file.save(file.filename)
            df = pd.DataFrame(pd.read_excel(file.filename))
            df1 = df[['学号', '姓名', '密码']]
            id = df1[['学号']].values.T.tolist()[:][0]
            name = df1[['姓名']].values.T.tolist()[:][0]
            pwd = df1[['密码']].values.T.tolist()[:][0]
            if df.isnull().values.any() or len(id) == 0:
                flash('存在空信息')
            else:
                sid_diff = sid_if_exist(id)
                if sid_diff != 0:
                    flash('学号存在重复')
                else:
                    flash('success')
                    for i in range(len(id)):
                        s = Student(s_id=id[i], s_name=name[i], s_password=pwd[i])
                        db.session.add(s)
                        i += 1
                    db.session.commit()
            os.remove(file.filename)

        else:
            flash("只能识别'xlsx,xls'文件")
    else:
        flash('请选择文件')

    return redirect(url_for('teacher.select_all_student'))


@teacher.route('/download', methods=['POST'])
def download():
    cid = request.form.get('cid')
    cname = request.form.get('cname')
    time = request.form.get('time')
    # 建立数据库引擎
    engine = create_engine('mysql+pymysql://root:root@localhost:3306/test?charset=utf8')
    # 写一条sql
    sql = "select s_id 学号,result 考勤结果 from attendance where c_id='" + str(cid) + "' and time='" + str(time) + "'"
    print(sql)
    # 建立dataframe
    df = pd.read_sql_query(sql, engine)
    out = BytesIO()
    writer = pd.ExcelWriter('out.xlsx', engine='xlsxwriter')
    df.to_excel(excel_writer=writer, sheet_name='Sheet1', index=False)
    writer.save()
    out.seek(0)

    return jsonify({"message": "保存成功，请前往项目目录下查看out.xlsx文件"})

@teacher.route('/select_IssuesList', methods=['POST', 'GET'])
def select_IssuesList():
    if request.method == 'POST':
        try:
            dict = db.session.query(IssuesList).group_by("c_name").order_by('s_id').all()
            cid = request.form.get('c_id')
            # start_time = request.form.get('starttime')
            time = request.form.get('time')
            if cid!="" and time!="":
                issuses = db.session.query(IssuesList).filter(IssuesList.c_id == cid,func.date(IssuesList.time)==time).order_by('s_id').all()
            elif cid=="" and time !="":
                issuses = db.session.query(IssuesList).filter(func.date(IssuesList.time)==time).order_by('s_id').all()
            elif cid!="" and time=="":
                issuses = db.session.query(IssuesList).filter(IssuesList.c_id == cid).order_by('s_id').all()
            else:
                issuses = db.session.query(IssuesList).order_by('s_id').all()
        except Exception as e:
            print('Error:', e)
            flash("出发错误操作")
            return redirect(url_for('teacher.home'))
    return render_template('teacher/classroom_issues.html', dict=dict,issuses=issuses)
@teacher.route('/select_IssuesList_all', methods=['POST', 'GET'])
def select_IssuesList_all():
    try:

        issuses = db.session.query(IssuesList).order_by('s_id').all()
        dict = db.session.query(IssuesList).group_by("c_name").order_by('s_id').all()
    except Exception as e:
        print('Error:', e)
        flash("出发错误操作")
        return redirect(url_for('teacher.home'))

    return render_template('teacher/classroom_issues.html',dict=dict ,issuses=issuses)