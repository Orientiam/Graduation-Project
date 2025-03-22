from flask import Blueprint, render_template, request, session,flash,jsonify,redirect,url_for,send_from_directory
from app import get_faces_from_camera as gf
import base64
import os
from .models import Faces,Student,SC,Course,Attendance,Teacher,Student_info,AttendanceSheet,IssuesList
from app import features_extraction_to_csv as fc
from app import db
from datetime import datetime
from sqlalchemy import extract
import json
from os import remove
import dlib
import cv2
import numpy as np
import time
from PIL import Image
import pandas as pd
from app import app
student = Blueprint('student',__name__,static_folder='static')

# Dlib 正向人脸检测器
detector = dlib.get_frontal_face_detector()
# Dlib 人脸 landmark 特征点检测器
predictor = dlib.shape_predictor('app/static/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib Resnet 人脸识别模型，提取 128D 的特征矢量
face_reco_model = dlib.face_recognition_model_v1("app/static/data_dlib/dlib_face_recognition_resnet_model_v1.dat")
# 计算两个128D向量间的欧式距离
def return_euclidean_distance(feature_1, feature_2):
    feature_1 = np.array(feature_1)
    feature_2 = np.array(feature_2)
    dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
    return dist
#人脸识别类
#http://127.0.0.1:5000/student/face_idenitfy/<string:sid>/<string:cid>
@student.route('/face_idenitfy/<string:sid>/<string:cid>',methods=['POST'])
def face_identify(sid,cid):
    results = {}
    rfile = request.files.get('image')
    image = Image.open(rfile)  # 确保这里的image_file_object是文件对象
    # 转换成dlib可以处理的图片格式
    img_array =np.asarray(image)
    faces = detector(img_array, 0)  # 人脸特征数组
    if len(faces)<=0:
        results["data"]="未检测到人脸"
        results["msg"]="error"
        return json.dumps(results, ensure_ascii=False)
    if len(faces)>1:
        results["data"]="请保证只有一个人脸"
        results["msg"]="error"
        return json.dumps(results, ensure_ascii=False)
    shape = predictor(img_array, faces[0])
    sid_features=face_reco_model.compute_face_descriptor(img_array, shape)
    db_sid_features = Faces.query.filter(Faces.s_id==sid).first()
    if db_sid_features:
        someone_feature_str = str(db_sid_features.feature).split(',')
        features_someone_arr = []
        for one_feature in someone_feature_str:
            if one_feature == '':
                features_someone_arr.append('0')
            else:
                features_someone_arr.append(float(one_feature))
    dist=return_euclidean_distance(sid_features,features_someone_arr)
    if dist<0.3:
        attendance=AttendanceSheet.query.filter(AttendanceSheet.s_id == sid,AttendanceSheet.c_id==cid).first()
        if attendance!=None:
            results["data"] = "提交成功"
            results["msg"] = "ok"
            attendance.signintime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            #attendance.result="已签到"
            db.session.commit()
        else:
            results["data"] = "选择课程不对，请重新选择"
            results["msg"] = "error"
    else:
        results["data"] = "提交失败，请重新提交"
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)


# http://127.0.0.1:5000/student/login
@student.route('/login',methods=['POST'])
def login():
    result={}
    try:
        if request.method == 'POST':
            id = request.get_json().get('s_id')
            password = request.get_json().get('password')
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(time)

            students = Student.query.filter(Student.s_id == id).first()
            if students:
                if students.s_password == password:
                    result["flag"]=students.flag
                    result["msg"]="登录成功"
                else:
                    result["msg"]="密码错误"
            else:
                result["msg"]="学号错误"
    except:
        result["msg"] = "error"
    return json.dumps(result, ensure_ascii=False)
# http://127.0.0.1:5000/student/register
@student.route('/register',methods=['POST'])
def register():
    result = {}
    try:
        json_data = request.get_json()
        id = json_data.get("s_id")
        name = json_data.get("s_name")
        password = json_data.get("s_password")
        flag =json_data.get("flag")
        student = Student.query.filter(Student.s_id == id).first()
        student_info=Student_info.query.filter(Student_info.s_id == id).first()
        if student_info:
            student_info.s_id=id
            student_info.s_name=name
        else:
            user_info = Student_info(s_id=id, s_name=name)
            db.session.add(user_info)
        if student:
            student.s_name=name
            student.s_password=password
            student.flag=flag
        else:
            user = Student(s_id=id, s_name=name,s_password=password,flag=flag)
            db.session.add(user)
        db.session.commit()
        result["msg"] = "ok"
    except:
        result["msg"] = "error"
    return json.dumps(result, ensure_ascii=False)
# http://127.0.0.1:5000/student/home
@student.route('/home',methods=['POST'])  #/home,考勤记录
def home():
    try:
        results = {}
        records = []
        json_data = request.get_json()
        id = json_data.get("s_id")
        student = Student.query.filter(Student.s_id==id).first()
        # session['flag'] = student.flag
        attendances = db.session.query(Attendance).filter(Attendance.s_id==id).order_by(Attendance.time.desc()).limit(5).all()
        for i in attendances:
            course = db.session.query(Course).filter(Course.c_id==i.c_id).all()
            dict_results = {}
            dict_results['course']=course[0].c_name
            dict_results['time']=str(i.time)
            dict_results['result']=i.result
            records.append(dict_results)
        results["data"]=records
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

def pre_work_mkdir(path_photos_from_camera):
    # 新建文件夹 / Create folders to save faces images and csv
    if os.path.isdir(path_photos_from_camera):
        pass
    else:
        print(path_photos_from_camera)
        os.mkdir(path_photos_from_camera)

# http://127.0.0.1:5000/student/upload_faces
@student.route("/upload_faces/<string:sid>", methods=['POST'])
def upload_faces(sid):
    results={}
    rfile = request.files.get('image')
    path = "app/static/data/data_faces_from_camera/" + sid
    pre_work_mkdir(path)
    current_face_path = "app/static/data/data_faces_from_camera/" + sid + "/"
    photos_list = os.listdir(current_face_path)
    num = len(photos_list)
    if num >= 5:
        results["data"] = "图片录入过多"
        results["msg"] = "error"
        return json.dumps(results, ensure_ascii=False)
    rfile.filename=str(num+1) + '.jpg'
    rfile_name = rfile.filename
    saved_path = os.path.join(path, rfile_name)
    rfile.save(saved_path)
    up = gf.Face_Register()
    flag = up.single_pocess(saved_path)  #进行上传图片的正确姿势
    if flag != 'right':
        remove(saved_path)
        if flag=="none":
            results["data"]="未检测到人脸，请重新录入"
            results["msg"]="error"
        elif flag=="more":
            results["data"] = "检测到多个人脸，请录入只含单个人脸图片"
            results["msg"] = "error"
        return json.dumps(results, ensure_ascii=False)
    results["data"] = "图片录入成功"
    results["msg"] = "ok"
    return json.dumps(results, ensure_ascii=False)
# http://127.0.0.1:5000/student/upload_facesfeature
#计算特征值存数据库
@student.route('/upload_facesfeature',methods=['POST'])
def upload_facesfeature():
    try:
        results = {}
        sid = str(request.get_json().get('sid'))
        path_images_from_camera = "app/static/data/data_faces_from_camera/"
        path = path_images_from_camera + sid
        print(path)
        features_mean_personX = fc.return_features_mean_personX(path)
        features = str(features_mean_personX[0])
        for i in range(1,128):
            features = features + ',' + str(features_mean_personX[i])
        student = Faces.query.filter(Faces.s_id == sid).first()
        if student:
            student.feature = features
        else:
            face = Faces(s_id=sid,feature=features)
            db.session.add(face)
        db.session.commit()
        print(" >> 特征均值 / The mean of features:", list(features_mean_personX), '\n')
        student = Student.query.filter(Student.s_id==sid).first()
        student.flag=0
        db.session.commit()
        results["msg"] = "ok"
    except Exception as e:
        print('Error:', e)
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# 假设静态文件存储在app/static/data/data_faces_from_camera目录下
@student.route('/static/data/data_faces_from_camera/<path:filename>')
def face_static_file(filename):
    return send_from_directory('/static/data/data_faces_from_camera/', filename)
# http://127.0.0.1:5000/student/my_faces
@student.route('/my_faces',methods=['POST'])
def my_faces():
    results={}
    try:
        sid = str(request.get_json().get('sid'))
        current_face_path = "app/static/data/data_faces_from_camera/" + sid + "/"
        face_path = "static/data/data_faces_from_camera/" + sid + "/"
        photos_list = os.listdir(current_face_path)
        num = len(photos_list)
        paths = []
        for i in range(num):
            imagedict={}
            path =  face_path + str(i+1) + '.jpg'
            imagedict["image"]=path
            paths.append(imagedict)
        results["data"]=paths
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# http://127.0.0.1:5000/student/my_records
@student.route('/my_records',methods=['GET','POST'])
def my_records():
    # sid = session['id']
    try:
        dict = {}
        results={}
        if request.method == 'POST':
            sid=str(request.get_json().get('s_id'))
            cid = str(request.get_json().get('course_id'))
            time = str(request.get_json().get('time'))
            if cid != '' and time != '':
                course = Course.query.filter(Course.c_id==cid).first()
                one_course_records = db.session.query(Attendance).filter(Attendance.s_id==sid,Attendance.c_id==cid,Attendance.time.like(time+'%')).all()
                dict[course] = one_course_records
                courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()

            elif cid !='' and time == '':
                course = Course.query.filter(Course.c_id == cid).first()
                one_course_records = db.session.query(Attendance).filter(Attendance.s_id == sid, Attendance.c_id == cid).all()
                dict[course] = one_course_records
                courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()

            elif cid == '' and time !='':
                courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()
                for course in courses:
                    one_course_records = db.session.query(Attendance).filter(Attendance.s_id == sid,Attendance.c_id == course.c_id,Attendance.time.like(time+'%')).order_by("c_id").all()
                    dict[course] = one_course_records
                courses = db.session.query(Course).join(SC).filter(SC.s_id == sid).order_by("c_id").all()

            else:
                courses = db.session.query(Course).join(SC).filter(SC.s_id==sid).order_by("c_id").all()
                for course in courses:
                    one_course_records = db.session.query(Attendance).filter(Attendance.s_id==sid,Attendance.c_id==course.c_id).order_by("c_id").all()
                    dict[course] = one_course_records
        results["data"]=dict
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# http://127.0.0.1:5000/student/get_all_course
@student.route('/get_all_course',methods=['GET'])
def get_all_course():
    try:
        data=[]
        results={}

        courses = db.session.query(Course).filter(Course.flag=="可选课").all()
        for course in courses:
            dict = {}
            dict["c_id"] =course.c_id
            dict["c_name"]=course.c_name
            teacher = Teacher.query.filter(Teacher.t_id == course.t_id).first()
            dict["teacher"]=teacher.t_name
            data.append(dict)
        results["data"]=data
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
@student.route('/choose_course',methods=['GET','POST'])
def choose_course():
    try:
        results={}

        if request.method == 'POST':
            sid=request.get_json().get('sid')
            cid = request.get_json().get('cid')
            course_info = SC.query.filter(SC.s_id == sid,SC.c_id==cid).first()
            if course_info:
                results["data"] = "该课程已选，不能重复选课"
                results["msg"] = "error"
                return json.dumps(results, ensure_ascii=False)
            sc = SC(s_id=sid, c_id=cid)
            db.session.add(sc)
            db.session.commit()

        results["data"]="选课成功"
        results["msg"]="ok"
    except Exception as e:
        print('Error:', e)
        results["data"] = "选课失败"
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
# http://127.0.0.1:5000/student/get_all_mycourse
@student.route('/get_all_mycourse',methods=['POST'])
def get_all_mycourse():
    try:
        data=[]
        results={}
        sid = request.get_json().get('sid')

        now_have_courses_sc = db.session.query(SC).filter(SC.s_id==sid).all()

        cids = []
        for sc in now_have_courses_sc:
            cids.append(sc.c_id)
        hava_courses = Course.query.filter(Course.c_id.in_(cids)).all()
        for course in hava_courses:
            dict = {}
            dict["c_id"] =course.c_id
            dict["c_name"]=course.c_name
            teacher = Teacher.query.filter(Teacher.t_id == course.t_id).first()
            dict["teacher"]=teacher.t_name
            data.append(dict)
        results["data"]=data
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
# http://127.0.0.1:5000/student/unchoose_course
@student.route('/unchoose_course',methods=['GET','POST'])
def unchoose_course():
    try:
        results = {}
        dict = {}
        if request.method == 'POST':
            sid = request.get_json().get('sid')
            cid = request.get_json().get('cid')
            sc = SC.query.filter(SC.c_id==cid,SC.s_id==sid).first()
            db.session.delete(sc)
            db.session.commit()

        results["data"] = "退课成功"
        results["msg"] = "ok"
    except Exception as e:
        print('Error:', e)
        results["data"] = "退课失败"
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
# http://127.0.0.1:5000/student/update_password
@student.route('/update_password',methods=['GET','POST'])
def update_password():
    results = {}
    try:
        sid = request.get_json().get('sid')
        student = Student.query.filter(Student.s_id==sid).first()
        if request.method == 'POST':
            old = request.form.get('old')
            if old == student.s_password:
                new = request.form.get('new')
                student.s_password = new
                db.session.commit()
                results["data"] = "修改成功！"
                results["msg"] = "ok"
            else:
                results["data"] = "旧密码错误，请重试"
                results["msg"] = "error"
    except:
        results["data"] = "修改失败，请重试"
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
# http://127.0.0.1:5000/student/my_courseform
#课程表
@student.route('/my_courseform',methods=['GET','POST'])
def my_courseform():
    try:
        results={}
        data=[]
        if request.method == 'POST':
            sid=str(request.get_json().get('s_id'))
            week=str(request.get_json().get('week'))
            now_have_courses_sc = SC.query.filter(SC.s_id == sid).all()
            cids = []
            for sc in now_have_courses_sc:
                cids.append(sc.c_id)
            hava_courses = Course.query.filter(Course.c_id.in_(cids)).all()
            for course in hava_courses:
                teacher=Teacher.query.filter(Teacher.t_id==course.t_id).first()
                dict = {}
                dict["name"]=course.c_name
                dict["time"]=course.times
                dict["day"]=course.day
                liststr=course.week.split('-')
                if liststr[0]>week or week>liststr[1]:
                    continue
                dict["week"]=week
                dict["location"]=course.location
                dict["teacher"]=teacher.t_name
                data.append(dict)
        results["data"]=data
        results["msg"]="ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# 假设静态文件存储在app.profileImgs目录下
@student.route('/profileImgs/<path:filename>')
def static_file(filename):
    return send_from_directory('profileImgs', filename)

# http://127.0.0.1:5000/student/update_profileImg/s_id
#上传头像
@student.route("/update_profileImg/<string:s_id>", methods=["POST"])
def update_profileImg(s_id):
    result = {}
    try:
        rfile = request.files.get('image')
        rfile.filename = str(s_id) + '.jpg'
        rfile_name = rfile.filename
        saved_path = os.path.join("app/profileImgs/", rfile_name)
        rfile.save(saved_path)
        result["msg"] = "ok"
    except:
        result["msg"]="error"
    return json.dumps(result, ensure_ascii=False)


# http://127.0.0.1:5000/student/update_student_info
#增加修改学生信息
@student.route('/update_student_info',methods=['POST'])
def update_student_info():
    results = {}
    try:
        sid = request.get_json().get('s_id')
        s_name = request.get_json().get('s_name')
        s_zy= request.get_json().get('s_zy')
        s_xy = request.get_json().get('s_xy')
        s_nj = request.get_json().get('s_nj')
        s_bj = request.get_json().get('s_bj')
        s_zzmm = request.get_json().get('s_zzmm')
        s_nl = request.get_json().get('s_nl')
        s_zw = request.get_json().get('s_zw')
        s_xb = request.get_json().get('s_xb')
        s_lxdh = request.get_json().get('s_lxdh')
        student_info = Student_info.query.filter(Student_info.s_id==sid).first()

        if student_info:
            student_info.s_name = s_name
            student_info.s_zy = s_zy
            student_info.s_xy = s_xy
            student_info.s_nj = s_nj
            student_info.s_bj = s_bj
            student_info.s_zzmm = s_zzmm
            student_info.s_nl = s_nl
            student_info.s_zw = s_zw
            student_info.s_xb = s_xb
            student_info.s_lxdh = s_lxdh
        else:
            studentinfo = Student_info(s_id=sid, s_name=s_name,s_zy=s_zy,s_xy=s_xy,s_nj=s_nj,s_bj=s_bj,s_zzmm=s_zzmm,s_nl=s_nl,s_zw=s_zw,s_xb=s_xb,s_lxdh=s_lxdh)
            db.session.add(studentinfo)
        db.session.commit()
        results["data"] = "修改成功！"
        results["msg"] = "ok"
    except:
        results["data"] = "修改失败，请重试"
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# http://127.0.0.1:5000/student/get_student_info
#获取学生信息
@student.route('/get_student_info',methods=['POST'])
def get_student_info():
    results = {}
    data={}
    try:
        sid = request.get_json().get('s_id')
        student_info = Student_info.query.filter(Student_info.s_id==sid).first()
        if student_info:
            data["s_name"]=student_info.s_name
            data["s_zy"]=student_info.s_zy
            data["s_xy"]=student_info.s_xy
            data["s_nj"]=student_info.s_nj
            data["s_bj"]=student_info.s_bj
            data["s_zzmm"]=student_info.s_zzmm
            data["s_nl"]=student_info.s_nl
            data["s_zw"]=student_info.s_zw
            data["s_xb"]=student_info.s_xb
            data["s_lxdh"]=student_info.s_lxdh

        results["data"] = data
        results["msg"] = "ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)


# http://127.0.0.1:5000/student/get_all_student_info
#获取学生信息
@student.route('/get_all_student_info',methods=['GET'])
def get_all_student_info():
    results = {}
    data=[]
    try:
        students_info=db.session.query(Student_info).all()
        for student_info in students_info:
            dict = {}
            dict["s_id"]=student_info.s_id
            dict["s_name"]=student_info.s_name
            dict["s_zy"]=student_info.s_zy
            dict["s_xy"]=student_info.s_xy
            dict["s_nj"]=student_info.s_nj
            dict["s_bj"]=student_info.s_bj
            dict["s_zzmm"]=student_info.s_zzmm
            dict["s_nl"]=student_info.s_nl
            dict["s_zw"]=student_info.s_zw
            dict["s_xb"]=student_info.s_xb
            dict["s_lxdh"]=student_info.s_lxdh
            data.append(dict)
        results["data"] = data
        results["msg"] = "ok"
    except:
        results["data"] = {}
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)

# 假设静态文件存储在app/studentsinfo目录下
@student.route('/studentsinfo/<path:filename>')
def students_info_file(filename):
    return send_from_directory('studentsinfo', filename)
# http://127.0.0.1:5000/student/save_student_info_to_excel
#保存学生信息
@student.route('/save_student_info_to_excel',methods=['GET'])
def save_student_info_to_excel():
    results = {}
    data=[]
    try:
        directory = "app/studentsinfo/"
        students_info=db.session.query(Student_info).all()
        for student_info in students_info:
            dict = {}
            dict["学号"] = student_info.s_id
            dict["姓名"] = student_info.s_name
            dict["专业"] = student_info.s_zy
            dict["学院"] = student_info.s_xy
            dict["年级"] = student_info.s_nj
            dict["班级"] = student_info.s_bj
            dict["政治面貌"] = student_info.s_zzmm
            dict["年龄"] = student_info.s_nl
            dict["职务"] = student_info.s_zw
            dict["性别"] = student_info.s_xb
            dict["联系方式"] = student_info.s_lxdh
            data.append(dict)
        # 将数据转换为pandas DataFrame
        df = pd.DataFrame(data=data)

        filepath = os.path.join(directory, 'roster.xlsx')
        # 保存到Excel文件
        df.to_excel(filepath, index=False)
        if os.path.exists(filepath):
            results["msg"] = "ok"
        else:
            results["msg"] = "error"
    except:
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)
from app import socketio,connected_sids


# http://127.0.0.1:5000/student/sendmessage
#弹幕
@student.route('/sendmessage',methods=['POST'])
def sendmessage():

    results = {}
    dict={}
    try:
        sid = request.get_json().get('s_id')
        msg = request.get_json().get('msg')
        cid = request.get_json().get('c_id')
        c_name = request.get_json().get('c_name')
        dict["s_id"]=sid
        dict["msg"]=msg
        name = request.get_json().get('name')
        now=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # print(request.sid)
        for resid in connected_sids:
            print(resid)
            socketio.emit('my_response', {'data': f'{sid},{name},{msg}'}, room=resid)
        issuesList = IssuesList(s_id=sid, name=name, c_id=cid,c_name=c_name,time=now,msg=msg)
        db.session.add(issuesList)
        db.session.commit()
        results["msg"] = "ok"
    except:
        results["msg"] = "error"
    return json.dumps(results, ensure_ascii=False)




