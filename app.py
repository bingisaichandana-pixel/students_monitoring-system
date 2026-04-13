from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import mysql.connector

app = Flask(__name__,static_folder='static')
app.secret_key ="secret123"

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="students_monitoring"
    )
#---------home(new)------

@app.route('/')
def home():
    return redirect('/login')

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route('/dashboard')
def dashboard():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Total students
    cur.execute("SELECT COUNT(*) AS total FROM students")
    total = cur.fetchone()['total']

    # Weak students
    cur.execute("""
        SELECT COUNT(*) AS weak
        FROM marks
        WHERE internal1 < 15 OR internal2 < 15
    """)
    weak = cur.fetchone()['weak']

    # Strong students (logic)
    strong = total - weak

    return render_template(
        'dashboard.html',
        total=total,
        weak=weak,
        strong=strong
    )
#-------------------------
#CHART ROUTE
#-------------------------
@app.route('/charts')
def charts():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT s.name,
        AVG(m.internal1 + m.internal2 + m.assignment) AS avg_marks
        FROM students s
        JOIN marks m ON s.id = m.student_id
        GROUP BY s.id
    """)

    data = cur.fetchall()

    # ✅ convert to lists
    names = [row['name'] for row in data]
    marks = [float(row['avg_marks']) for row in data]
    
    print("NAMES:",names)
    print("MARKS:",marks)

    return render_template('charts.html', names=names, marks=marks)
    

# -----------------------------
# STUDENTS
# -----------------------------
@app.route('/students')
def students():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM students")
    data = cur.fetchall()

    return render_template('students.html', students=data)

# -----------------------------
# ADD STUDENT
# -----------------------------
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user'not in session:
       return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']

        conn = get_db()
        cur = conn.cursor()

        cur.execute("INSERT INTO students (name, roll) VALUES (%s, %s)", (name, roll))
        conn.commit()
        conn.close()

        return redirect('/students')

    return render_template('add_student.html')
#-------------------------
#DELETE STUDENTS
# -------------------------
@app.route('/delete_student/<int:id>')
def delete_student(id):
    conn = get_db()
    cur = conn.cursor()

    # delete related data first (important ⚠️)
    cur.execute("DELETE FROM marks WHERE student_id=%s", (id,))
    cur.execute("DELETE FROM participation WHERE student_id=%s", (id,))
    cur.execute("DELETE FROM homework WHERE student_id=%s", (id,))
    cur.execute("DELETE FROM conduct WHERE student_id=%s", (id,))

    # delete student
    cur.execute("DELETE FROM students WHERE id=%s", (id,))

    conn.commit()
    conn.close()

    return redirect('/students') 
#---------------------------
#edit
#---------------
@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']

        cur.execute("""
            UPDATE students 
            SET name=%s, roll=%s 
            WHERE id=%s
        """, (name, roll, id))

        conn.commit()
        conn.close()

        return redirect('/students')

    # GET request
    cur.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cur.fetchone()

    return render_template('edit_student.html', student=student)

# -----------------------------
# MARKS
# -----------------------------
@app.route('/marks', methods=['GET', 'POST'])
def marks():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get all students for dropdown
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        internal1 = request.form['internal1']
        internal2 = request.form['internal2']
        assignment = request.form['assignment']

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO marks (student_id, subject, internal1, internal2, assignment)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, subject, internal1, internal2, assignment))

        conn.commit()

        return redirect('/marks')

    return render_template('marks.html', students=students)
# -----------------------------
# STUDENT PROFILE (NEW 🔥)
# -----------------------------
@app.route('/student/<int:id>')
def student_profile(id):
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Student details
    cur.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cur.fetchone()

    # Marks
    cur.execute("SELECT * FROM marks WHERE student_id=%s", (id,))
    marks = cur.fetchall()

    # Homework
    cur.execute("SELECT * FROM homework WHERE student_id=%s", (id,))
    homework = cur.fetchall()

    # Participation
    cur.execute("SELECT * FROM participation WHERE student_id=%s", (id,))
    participation = cur.fetchall()

    # Conduct
    cur.execute("SELECT * FROM conduct WHERE student_id=%s", (id,))
    conduct = cur.fetchall()

    return render_template(
        'student_profile.html',
        student=student,
        marks=marks,
        homework=homework,
        participation=participation,
        conduct=conduct
    )

# -----------------------------
# REPORTS
# -----------------------------
@app.route('/reports')
def reports():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT s.name, m.subject,
               MAX(m.internal1) AS internal1,
               MAX(m.internal2) AS internal2,
               MAX(m.assignment) AS assignment,
               (MAX(m.internal1)+MAX(m.internal2)+MAX(m.assignment)) AS total,
               (MAX(m.internal1)+MAX(m.internal2)+MAX(m.assignment))/3 AS average
        FROM marks m
        JOIN students s ON m.student_id = s.id
        GROUP BY s.id, s.name, m.subject
    """)

    data = cur.fetchall()

    for row in data:
        if row['average'] < 10:
            row['status'] = 'Fail'
        else:
            row['status'] = 'Pass'

    return render_template('reports.html', data=data)
 # -----------------------------
# ALERTS
# -----------------------------
@app.route('/alerts')
def alerts():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT s.name, m.subject, m.internal1, m.internal2,m.assignment
        FROM students s
        JOIN marks m ON s.id = m.student_id
        WHERE m.internal1 < 15 OR m.internal2 < 15
        OR m.assignment<10
    """)

    data = cur.fetchall()

    return render_template('alerts.html', students=data)

#--------------------------
# STATIC PAGES
# -----------------------------
@app.route('/participation', methods=['GET', 'POST'])
def participation():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get students for dropdown
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    # If form submitted → insert data
    if request.method == 'POST':
        student_id = request.form['student_id']
        status = request.form['status']
        date = request.form['date']

        cur.execute("""
            INSERT INTO participation (student_id, status, date)
            VALUES (%s, %s, %s)
        """, (student_id, status, date))

        conn.commit()

    # Always fetch updated data
    cur.execute("""
        SELECT s.name, p.status, p.date
        FROM participation p
        JOIN students s ON s.id = p.student_id
    """)

    data = cur.fetchall()

    return render_template(
        'participation.html',
        students=students,
        data=data
    )
        

    
@app.route('/homework', methods=['GET', 'POST'])
def homework():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get students for dropdown
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        status = request.form['status']
        date = request.form['date']

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO homework (student_id, subject, status, date)
            VALUES (%s, %s, %s, %s)
        """, (student_id, subject, status, date))

        conn.commit()

    # Show all records
    cur.execute("""
        SELECT s.name, h.subject, h.status, h.date
        FROM homework h
        JOIN students s ON s.id = h.student_id
    """)
    data = cur.fetchall()

    return render_template('homework.html', students=students, data=data)

@app.route('/conduct', methods=['GET', 'POST'])
def conduct():
    if 'user'not in session:
       return redirect('/login')
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Get students
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form['student_id']
        remarks = request.form['remarks']
        date = request.form['date']

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO conduct (student_id, remarks, date)
            VALUES (%s, %s, %s)
        """, (student_id, remarks, date))

        conn.commit()

    # Show all records
    cur.execute("""
        SELECT s.name, c.remarks, c.date
        FROM conduct c
        JOIN students s ON s.id = c.student_id
    """)
    data = cur.fetchall()

    return render_template('conduct.html', students=students, data=data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        conn = get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        conn.close()

        # Validate username exists and check the hashed password
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            flash('Logged in successfully!', 'success')
            return redirect('/dashboard')
        # Fallback for plain-text passwords (backward compatibility)
        elif user and user['password'] == password:
            session['user'] = username
            flash('Logged in successfully! Please update your password to a hashed version.', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect('/login')


    
# -----------------------------
# RUN
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
