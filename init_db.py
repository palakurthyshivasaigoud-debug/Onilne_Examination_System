"""
init_db.py — Run this ONCE to set up the database.

Usage:
  python init_db.py

Works with both SQLite (default, no setup needed) and MySQL (XAMPP).
"""

import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Only do the MySQL pre-check when using MySQL
if not DATABASE_URL or not DATABASE_URL.startswith('sqlite'):
    import pymysql
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'exam_system')
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✓ MySQL database '{DB_NAME}' ready.")
    except Exception as e:
        print(f"\n❌ Cannot connect to MySQL!\n   Error: {e}\n")
        print("   ➤ Start XAMPP MySQL, or use SQLite by setting DATABASE_URL=sqlite:///exam_system.db in .env\n")
        exit(1)
else:
    print(f"✓ Using SQLite: {DATABASE_URL}")

# Initialize Flask app tables
from app import create_app, db
from app.models import User, Question, Exam

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Tables created OK.")

    # Admin user
    if not User.query.filter_by(email='admin@exam.com').first():
        admin = User(name='Administrator', email='admin@exam.com', role='admin')
        admin.set_password('Admin@123')
        db.session.add(admin)
        print("Created admin: admin@exam.com / Admin@123")

    # Sample students
    students_data = [
        ('Alice Johnson', 'alice@student.com', 'Student@123'),
        ('Bob Smith', 'bob@student.com', 'Student@123'),
        ('Carol White', 'carol@student.com', 'Student@123'),
    ]
    for name, email, pw in students_data:
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email, role='student')
            u.set_password(pw)
            db.session.add(u)
            print(f"Created student: {email}")

    db.session.commit()

    # Questions
    if Question.query.count() == 0:
        questions = [
            # Computer Science
            ('Computer Science', 'What does CPU stand for?', 'Central Processing Unit', 'Computer Personal Unit', 'Central Processor Utility', 'Core Processing Unit', 'A', 1),
            ('Computer Science', 'Which data structure uses LIFO principle?', 'Queue', 'Stack', 'Array', 'Linked List', 'B', 1),
            ('Computer Science', 'What is the time complexity of Binary Search?', 'O(n)', 'O(n²)', 'O(log n)', 'O(1)', 'C', 1),
            ('Computer Science', 'Which language is primarily used for web styling?', 'JavaScript', 'Python', 'CSS', 'HTML', 'C', 1),
            ('Computer Science', 'What does HTML stand for?', 'Hyper Text Markup Language', 'High Text Machine Level', 'Hyper Transfer Markup Logic', 'Home Tool Markup Language', 'A', 1),
            ('Computer Science', 'Which operator is used for integer division in Python?', '/', '//', '%', '**', 'B', 1),
            ('Computer Science', 'What is RAM?', 'Read Access Memory', 'Random Access Memory', 'Rapid Array Memory', 'Run-time Access Module', 'B', 1),
            ('Computer Science', 'Which of the following is an OOP concept?', 'Recursion', 'Compilation', 'Inheritance', 'Looping', 'C', 1),
            ('Computer Science', 'What is the base of hexadecimal number system?', '2', '8', '10', '16', 'D', 1),
            ('Computer Science', 'What does SQL stand for?', 'Structured Query Language', 'Simple Query Logic', 'Serial Queue Loop', 'Structured Quick Link', 'A', 1),
            ('Computer Science', 'What does HTTP stand for?', 'Hyper Text Transfer Protocol', 'High Transfer Text Protocol', 'Hyper Transfer Transmission Protocol', 'None of these', 'A', 1),
            ('Computer Science', 'Which of these is NOT a programming language?', 'Python', 'Java', 'HTML', 'Swift', 'C', 1),
            # Mathematics
            ('Mathematics', 'What is the value of pi approximately?', '3.14159', '2.71828', '1.61803', '1.41421', 'A', 1),
            ('Mathematics', 'What is the derivative of x squared?', 'x', '2x', '2', 'x squared', 'B', 1),
            ('Mathematics', 'What is 15% of 200?', '25', '30', '35', '40', 'B', 1),
            ('Mathematics', 'How many sides does a hexagon have?', '5', '6', '7', '8', 'B', 1),
            ('Mathematics', 'What is the square root of 144?', '10', '11', '12', '13', 'C', 1),
            ('Mathematics', 'What is 2 to the power of 10?', '512', '1024', '2048', '256', 'B', 1),
            ('Mathematics', 'The sum of angles in a triangle is?', '90 degrees', '180 degrees', '270 degrees', '360 degrees', 'B', 1),
            ('Mathematics', 'Area of circle with radius 7 (pi=22/7)?', '154', '144', '164', '174', 'A', 1),
            ('Mathematics', 'Solve: 3x + 6 = 21, find x', '3', '4', '5', '6', 'C', 1),
            ('Mathematics', 'What is the LCM of 4 and 6?', '6', '12', '24', '8', 'B', 1),
            # General Knowledge
            ('General Knowledge', 'Who invented the telephone?', 'Thomas Edison', 'Nikola Tesla', 'Alexander Graham Bell', 'Guglielmo Marconi', 'C', 1),
            ('General Knowledge', 'What is the capital of France?', 'London', 'Berlin', 'Paris', 'Madrid', 'C', 1),
            ('General Knowledge', 'Which planet is known as the Red Planet?', 'Venus', 'Jupiter', 'Mars', 'Saturn', 'C', 1),
            ('General Knowledge', 'What is the chemical symbol for Gold?', 'Go', 'Gd', 'Au', 'Ag', 'C', 1),
            ('General Knowledge', 'How many continents are there on Earth?', '5', '6', '7', '8', 'C', 1),
        ]
        for q in questions:
            qobj = Question(
                subject=q[0], question_text=q[1],
                option_a=q[2], option_b=q[3], option_c=q[4], option_d=q[5],
                correct_answer=q[6], marks=q[7]
            )
            db.session.add(qobj)
        db.session.commit()
        print(f"Inserted {len(questions)} sample questions.")

    # Sample Exams
    if Exam.query.count() == 0:
        admin_user = User.query.filter_by(email='admin@exam.com').first()
        exams_data = [
            ('Computer Science Fundamentals', 'Computer Science', 30, 10),
            ('Mathematics Assessment', 'Mathematics', 25, 10),
            ('General Knowledge Quiz', 'General Knowledge', 20, 5),
        ]
        for title, subject, duration, nq in exams_data:
            e = Exam(title=title, subject=subject, duration_minutes=duration,
                     total_questions=nq, created_by=admin_user.id, is_active=True)
            db.session.add(e)
        db.session.commit()
        print("Created 3 sample exams.")

    print("\n✅ Database ready!")
    print("─────────────────────────────────────────")
    print("  Admin:   admin@exam.com / Admin@123")
    print("  Student: alice@student.com / Student@123")
    print("─────────────────────────────────────────")
    print("  Run: python run.py")
    print("  Open: http://localhost:5000")
