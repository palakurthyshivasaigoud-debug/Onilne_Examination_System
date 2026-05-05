from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import os

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def _seed_database():
    """Auto-seed DB with admin, students, questions and exams if empty."""
    from app.models import User, Question, Exam

    # Admin user
    if not User.query.filter_by(email='admin@exam.com').first():
        admin = User(name='Administrator', email='admin@exam.com', role='admin')
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()
        print("[DB] Created admin user.")

    # Sample students
    for name, email, pw in [
        ('Alice Johnson', 'alice@student.com', 'Student@123'),
        ('Bob Smith',     'bob@student.com',   'Student@123'),
        ('Carol White',   'carol@student.com', 'Student@123'),
    ]:
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email, role='student')
            u.set_password(pw)
            db.session.add(u)
    db.session.commit()

    # Sample questions
    if Question.query.count() == 0:
        questions = [
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
            ('Mathematics', 'What is the value of pi approximately?', '3.14159', '2.71828', '1.61803', '1.41421', 'A', 1),
            ('Mathematics', 'What is the derivative of x squared?', 'x', '2x', '2', 'x squared', 'B', 1),
            ('Mathematics', 'What is 15% of 200?', '25', '30', '35', '40', 'B', 1),
            ('Mathematics', 'How many sides does a hexagon have?', '5', '6', '7', '8', 'B', 1),
            ('Mathematics', 'What is the square root of 144?', '10', '11', '12', '13', 'C', 1),
            ('General Knowledge', 'Who invented the telephone?', 'Thomas Edison', 'Nikola Tesla', 'Alexander Graham Bell', 'Guglielmo Marconi', 'C', 1),
            ('General Knowledge', 'What is the capital of France?', 'London', 'Berlin', 'Paris', 'Madrid', 'C', 1),
            ('General Knowledge', 'Which planet is known as the Red Planet?', 'Venus', 'Jupiter', 'Mars', 'Saturn', 'C', 1),
            ('General Knowledge', 'What is the chemical symbol for Gold?', 'Go', 'Gd', 'Au', 'Ag', 'C', 1),
            ('General Knowledge', 'How many continents are there on Earth?', '5', '6', '7', '8', 'C', 1),
        ]
        for q in questions:
            db.session.add(Question(
                subject=q[0], question_text=q[1],
                option_a=q[2], option_b=q[3], option_c=q[4], option_d=q[5],
                correct_answer=q[6], marks=q[7]
            ))
        db.session.commit()
        print(f"[DB] Inserted {len(questions)} sample questions.")

    # Sample exams
    if Exam.query.count() == 0:
        admin_user = User.query.filter_by(email='admin@exam.com').first()
        for title, subject, duration, nq in [
            ('Computer Science Fundamentals', 'Computer Science', 30, 10),
            ('Mathematics Assessment',        'Mathematics',       25, 10),
            ('General Knowledge Quiz',        'General Knowledge', 20,  5),
        ]:
            db.session.add(Exam(
                title=title, subject=subject,
                duration_minutes=duration, total_questions=nq,
                created_by=admin_user.id, is_active=True
            ))
        db.session.commit()
        print("[DB] Created 3 sample exams.")

    print("[DB] Auto-initialization complete.")


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    from app.config import Config
    app.config.from_object(Config)

    # Ensure screenshots folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    mail.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.student.routes import student_bp
    from app.proctor.routes import proctor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(proctor_bp, url_prefix='/proctor')

    # Auto-initialize database on first startup
    with app.app_context():
        try:
            db.create_all()
            _seed_database()
        except Exception as e:
            print(f"[DB] Auto-init skipped: {e}")

    return app
