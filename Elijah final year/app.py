import os
import math
import csv
import random  # Added for OTP generation
from io import StringIO
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message  # Added for Email support
from flask import flash 

app = Flask(__name__, static_folder='static')
app.secret_key = "run_biometric_final_2026_locked"

# --- EMAIL CONFIGURATION (Update with your details) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'eirekholoelijah6@gmail.com' # Replace with your school or system email
app.config['MAIL_PASSWORD'] = 'egul ooyn xwks krvq'   # Replace with your Google App Password
mail = Mail(app)

# --- DATABASE SETUP ---

# 1. Look for the live cloud database key variable from Render/Supabase
database_url = os.environ.get('postgresql://postgres.ktvagrhteattxxliwgop:Huntuathebighead%402004@aws-0-eu-central-1.pooler.supabase.com:6543/postgres')

if database_url:
    # 2. Fix the link format so SQLAlchemy connects to Supabase cleanly
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # If something goes wrong, break instead of switching back to SQLite
    raise ValueError("No DATABASE_URL found! Connection to Supabase failed.")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 3. This line automatically builds your tables inside SUPABASE the moment the app boots up!
with app.app_context():
    db.create_all()
# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    id_number = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False) 
    password = db.Column(db.String(100))
    role = db.Column(db.String(10)) 
    device_id = db.Column(db.String(200), nullable=True)
    otp = db.Column(db.String(6), nullable=True) # Added to store OTP

class CourseSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20))
    date_held = db.Column(db.Date, default=datetime.now().date)

class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matric_no = db.Column(db.String(50))
    full_name = db.Column(db.String(100))
    course_code = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.now)

# --- CONFIGURATION ---
ALLOWED_RADIUS = 0.05 
STAFF_PREFIX = "RUN/REG/JSF/"
OPEN_SESSIONS = {} 

LOCATIONS = {
    'COMP_LAB': {'lat': 7.6816386698268335, 'lon': 4.458876256050976},
    'AUDITORIUM': {'lat': 6.7050, 'lon': 3.4050},
    'LECTURE_HALL_A': {'lat': 6.7025, 'lon': 3.4022}
}

COURSES = [
    {'code': 'CSC 401', 'title': 'Biometric Security', 'location': 'COMP_LAB'},
    {'code': 'EEE 401', 'title': 'Engineering Math', 'location': 'COMP_LAB'},
    {'code': 'FIC 401', 'title': 'Faith Integrated course', 'location': 'COMP_LAB'},
    {'code': 'BCH 301', 'title': 'Introduction to Biochemistry', 'location': 'COMP_LAB'},
    {'code': 'MLS 412', 'title': 'Clinical Testing', 'location': 'COMP_LAB'},
    {'code': 'NSC 501', 'title': 'Patient Diagnosis', 'location': 'COMP_LAB'},
    {'code': 'CSC 403', 'title': 'Software Engineering', 'location': 'COMP_LAB'},
    {'code': 'CSC 405', 'title': 'Data Mining', 'location': 'LECTURE_HALL_A'},
    {'code': 'GST 411', 'title': 'Entrepreneurship', 'location': 'AUDITORIUM'}
]

# --- ROUTES ---

@app.route('/')
def home(): return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get data from the form
        uid = request.form.get('user_id', '').strip().upper()
        pwd = request.form.get('password', '').strip()
        current_device = request.form.get('device_id') 

        # Query the database
        user = User.query.filter_by(id_number=uid, password=pwd).first()
        
        if user:
            # AUTO-LOCK FEATURE: If device was reset by admin, lock to current phone
            if user.role == 'student' and user.device_id is None:
                user.device_id = current_device
                db.session.commit()
            
            # Save user data to the session
            session.update({
                'user_id': user.id_number, 
                'full_name': user.full_name, 
                'role': user.role
            })
            
            # Redirect based on role
            if user.role == 'lecturer':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        
        # --- UPDATED: FLASH ERROR AND REDIRECT INSTEAD OF RETURNING STRING ---
        flash("Invalid Credentials. Please check your ID or password.", "danger")
        return redirect(url_for('home')) # Or redirect(url_for('login'))

    # If the method is GET, show the login screen
    return render_template('login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        
        if not email.endswith('@run.edu.ng'):
            return "Error: Use your official @run.edu.ng email.", 400
            
        full_name = request.form.get('full_name')
        id_number = request.form.get('id_number').upper()
        password = request.form.get('password')
        role = request.form.get('role')
        device_id = request.form.get('device_id')

        new_user = User(
            full_name=full_name, 
            id_number=id_number, 
            email=email, 
            password=password, 
            role=role,
            device_id=device_id
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "Error: Email or ID Number already exists.", 400
            
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))
            user.otp = otp_code
            db.session.commit()
            
            # Send Email
            msg = Message("RUN Attendance Password Reset", 
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[user.email])
            msg.body = f"Hello {user.full_name}, your OTP for password reset is: {otp_code}"
            mail.send(msg)
            
            return render_template('reset_password.html', email=email) # Redirect to a page to enter OTP
        return "Email not found in our system."
    return render_template('forgot_password.html')

@app.route('/reset_password_verify', methods=['POST'])
def reset_password_verify():
    email = request.form.get('email')
    user_otp = request.form.get('otp')
    new_password = request.form.get('new_password')
    
    user = User.query.filter_by(email=email, otp=user_otp).first()
    if user:
        user.password = new_password
        user.otp = None # Clear OTP after use
        db.session.commit()
        return "Password Reset Successful! <a href='/'>Login now</a>"
    return "Invalid OTP. <a href='/forgot_password'>Try again</a>"

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session: return redirect('/')
    clist = []
    for c in COURSES:
        att = AttendanceLog.query.filter_by(matric_no=session['user_id'], course_code=c['code']).count()
        total = CourseSession.query.filter_by(course_code=c['code']).count()
        clist.append({**c, 'attended': att, 'total': total})
    return render_template('student_dash.html', courses=clist, open_sessions=OPEN_SESSIONS, full_name=session['full_name'])

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'lecturer': return redirect('/')
    v, cc = request.args.get('view'), request.args.get('course')
    if v == 'manage_students':
        return render_template('admin_dash.html', students=User.query.filter_by(role='student').all(), view_mode="manage")
    if cc:
        total = CourseSession.query.filter_by(course_code=cc).count()
        sum_logs = db.session.query(
            AttendanceLog.full_name, 
            AttendanceLog.matric_no, 
            db.func.count(AttendanceLog.id).label('attended')
        ).filter_by(course_code=cc).group_by(AttendanceLog.matric_no).all()
        return render_template('admin_dash.html', summary_logs=sum_logs, total_held=total, course_name=cc, view_mode="students")
    return render_template('admin_dash.html', courses=COURSES, view_mode="courses", open_sessions=OPEN_SESSIONS)

@app.route('/admin/toggle_session/<course_code>')
def toggle_session(course_code):
    status = OPEN_SESSIONS.get(course_code, False)
    if not status: 
        today = datetime.now().date()
        if not CourseSession.query.filter_by(course_code=course_code, date_held=today).first():
            db.session.add(CourseSession(course_code=course_code))
            db.session.commit()
    OPEN_SESSIONS[course_code] = not status
    return redirect(url_for('admin_dashboard'))

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    cc = data.get('course')
    if not data.get('biometric_verified'): return jsonify({"message": "Biometric verification failed!"})
    if not OPEN_SESSIONS.get(cc, False): return jsonify({"message": "Session is closed!"})
    
    user = User.query.filter_by(id_number=session.get('user_id')).first()
    
    # --- DEVICE BINDING SECURITY LAYER ---
    if user.role == 'student' and data.get('device') != user.device_id: 
        return jsonify({"message": "Unauthorized device! Reset via Admin if you changed phones."})
    
    today = datetime.now().date()
    if AttendanceLog.query.filter(AttendanceLog.matric_no==user.id_number, AttendanceLog.course_code==cc, db.func.date(AttendanceLog.timestamp)==today).first():
        return jsonify({"message": "Already signed for today!"})
    
    loc = LOCATIONS[next(i for i in COURSES if i['code']==cc)['location']]
    dist = math.sqrt((float(data['latitude'])-loc['lat'])**2 + (float(data['longitude'])-loc['lon'])**2)
    if dist > ALLOWED_RADIUS: return jsonify({"message": "Not in lecture hall!"})
    
    db.session.add(AttendanceLog(matric_no=user.id_number, full_name=user.full_name, course_code=cc))
    db.session.commit()
    return jsonify({"message": "Attendance Marked Successfully"})

@app.route('/admin/download_course_report/<course_code>')
def download_course_report(course_code):
    total_held = CourseSession.query.filter_by(course_code=course_code).count()
    logs = db.session.query(
        User.full_name, 
        User.id_number, 
        db.func.count(AttendanceLog.id).label('attended_count')
    ).join(AttendanceLog, User.id_number == AttendanceLog.matric_no)\
     .filter(AttendanceLog.course_code == course_code)\
     .group_by(User.id_number).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Full Name', 'Matric Number', 'Attended', 'Total Sessions', 'Percentage'])
    for name, matric, count in logs:
        perc = f"{round((count / total_held * 100), 1)}%" if total_held > 0 else "0%"
        cw.writerow([name, matric, count, total_held, perc])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={course_code}_Report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/clear_device/<int:user_id>')
def clear_device(user_id):
    u = User.query.get(user_id)
    if u: u.device_id = None; db.session.commit()
    return redirect(url_for('admin_dashboard', view='manage_students'))

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__ == '__main__':
    import os
    # Render will inject a PORT environment variable dynamically
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
