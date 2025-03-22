from app import db #db是在app/__init__.py生成的关联后的SQLAlchemy实例

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(320), unique=True)
    password = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(320), unique=True)
    password = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

class Student(db.Model):
    __tablename__ = 'students'
    s_id= db.Column(db.String(13), primary_key=True)
    s_name = db.Column(db.String(80), nullable=False)
    s_password = db.Column(db.String(32), nullable=False)
    flag = db.Column(db.Integer, default=0)
    before = db.Column(db.DateTime)

    def __repr__(self):
        return '<Student %r,%r>' % (self.s_id,self.s_name)

class Student_info(db.Model):
    __tablename__ = 'students_info'
    s_id= db.Column(db.String(13), primary_key=True)
    s_name = db.Column(db.String(80), nullable=False)
    s_zy = db.Column(db.String(32), nullable=False)
    s_xy = db.Column(db.String(32), nullable=False)
    s_nj = db.Column(db.String(32), nullable=False)
    s_bj = db.Column(db.String(32), nullable=False)
    s_zzmm = db.Column(db.String(32), nullable=False)
    s_nl = db.Column(db.String(32), nullable=False)
    s_zw = db.Column(db.String(32), nullable=False)
    s_xb = db.Column(db.String(32), nullable=False)
    s_lxdh = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '<Student_info %r,%r>' % (self.s_id,self.s_name)



class Teacher(db.Model):
    __tablename__ = 'teachers'
    t_id= db.Column(db.String(8), primary_key=True)
    t_name = db.Column(db.String(80), nullable=False)
    t_password = db.Column(db.String(32), nullable=False)
    before = db.Column(db.DateTime)

    def __repr__(self):
        return '<Teacher %r,%r>' % (self.t_id,self.t_name)

class Faces(db.Model):
    __tablename__ = 'student_faces'
    s_id = db.Column(db.String(13), primary_key=True)
    feature = db.Column(db.Text,nullable=False)

    def __repr__(self):
        return '<Faces %r>' % self.s_id


class Course(db.Model):
    # day: '五', name: "编译原理", teacher: "教师A", week: "8", time: "1-3", location: "第一课室大楼"},
    __tablename__ = 'courses'
    c_id = db.Column(db.String(6), primary_key=True)
    t_id = db.Column(db.String(8),db.ForeignKey('teachers.t_id'),nullable=False)
    c_name = db.Column(db.String(100),nullable=False)
    times = db.Column(db.Text,default="1-2")
    day=db.Column(db.String(30),nullable=False)
    week = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(30), nullable=False)
    flag = db.Column(db.String(50), default="不可选课")

    def __repr__(self):
        return '<Course %r,%r,%r>' % (self.c_id,self.t_id,self.c_name)

class SC(db.Model):
    __tablename__ = 'student_course'
    s_id = db.Column(db.String(13),db.ForeignKey('students.s_id'),primary_key=True)
    c_id = db.Column(db.String(100),db.ForeignKey('courses.c_id') ,primary_key=True)

    def __repr__(self):
        return '<SC %r,%r> '%( self.s_id,self.c_id)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer,primary_key=True)
    s_id = db.Column(db.String(13), db.ForeignKey('students.s_id'))
    c_id = db.Column(db.String(100), db.ForeignKey('courses.c_id'))
    time = db.Column(db.DateTime)
    result = db.Column(db.String(10),nullable=False)
    signintime = db.Column(db.DateTime)

    def __repr__(self):
        return '<Attendance %r,%r,%r,%r>' % (self.s_id,self.c_id,self.time,self.result)

class Time_id():
    id = ''
    time = ''

    def __init__(self,id,time):
        self.id = id
        self.time = time

class choose_course():
    __tablename___ = 'choose_course'
    c_id = db.Column(db.String(6), primary_key=True)
    t_id = db.Column(db.String(8), nullable=False)
    c_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return '<Course %r,%r,%r>' % (self.c_id,self.t_id,self.c_name)


class AttendanceSheet(db.Model):
    __tablename__ = 'attendancesheet'
    s_id = db.Column(db.String(13), db.ForeignKey('students.s_id'),primary_key=True)
    c_id = db.Column(db.String(100), db.ForeignKey('courses.c_id'))
    starttime = db.Column(db.DateTime)
    result = db.Column(db.String(10), nullable=False)
    signintime = db.Column(db.DateTime)
    #endtime = db.Column(db.DateTime)

    def __repr__(self):
        return '<AttendanceSheet %r,%r,%r,%r>' % (self.s_id,self.c_id,self.signintime)

class IssuesList(db.Model):
    __tablename__ = 'issues_list'
    id = db.Column(db.Integer, primary_key=True)
    s_id = db.Column(db.String(13), db.ForeignKey('students.s_id'))
    c_id = db.Column(db.String(100), db.ForeignKey('courses.c_id'))
    name = db.Column(db.String(255), nullable=False)
    msg = db.Column(db.String(10), nullable=False)
    c_name = db.Column(db.String(255), nullable=False)
    time = db.Column(db.DateTime)

    def __repr__(self):
        return '<IssuesList %r,%r,%r,%r>' % (self.s_id,self.c_id,self.time)