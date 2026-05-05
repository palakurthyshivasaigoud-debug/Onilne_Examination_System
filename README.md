# 🎓 ExamPro — Online Examination System

A full-featured, production-ready online examination system with AI webcam proctoring, anti-cheating, analytics dashboard, and automatic email results.

---

LIVE DEMO: https://onilneexaminationsystem-production.up.railway.app/admin/dashboard

## ⚡ Quick Start

### Prerequisites
- XAMPP (for MySQL) — [Download](https://www.apachefriends.org/)
- Python 3.9+ — [Download](https://www.python.org/)
- VS Code (recommended editor)

---

## 🚀 Setup Instructions

### Step 1 — Start XAMPP
1. Open **XAMPP Control Panel**
2. Click **Start** next to **MySQL**
3. (Optional) Click Start next to Apache for phpMyAdmin access at `http://localhost/phpmyadmin`

### Step 2 — Configure Environment
Copy `.env.example` to `.env` (already done) and update your email credentials:
```
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_gmail_app_password
```

To get a Gmail App Password:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to **App Passwords** → Generate for "Mail"
4. Paste the 16-character password into `.env`

> **Note:** Email is optional — the system works without it (exam results still save to DB).

### Step 3 — Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Initialize Database
```bash
python init_db.py
```
This will:
- Create `exam_system` database automatically
- Create all tables
- Insert admin user, sample students, questions, and exams

### Step 5 — Run the App
```bash
python run.py
```

Open your browser at: **http://localhost:5000**

---

## 🔑 Default Login Credentials

| Role    | Email                  | Password     |
|---------|------------------------|--------------|
| Admin   | admin@exam.com         | Admin@123    |
| Student | alice@student.com      | Student@123  |
| Student | bob@student.com        | Student@123  |

---

## 📁 Project Structure

```
hackathon/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration from .env
│   ├── models.py            # SQLAlchemy models
│   ├── email_service.py     # Gmail SMTP email
│   ├── auth/routes.py       # Login, Register, Logout
│   ├── admin/routes.py      # Admin dashboard, CRUD
│   ├── student/routes.py    # Exam flow, results
│   └── proctor/routes.py    # OpenCV face detection
├── templates/
│   ├── auth/                # Login, Register HTML
│   ├── admin/               # Admin panel templates
│   └── student/             # Student panel templates
├── static/
│   ├── css/style.css        # Main dark theme CSS
│   ├── css/exam.css         # Exam interface CSS
│   ├── js/exam.js           # Anti-cheat + webcam + timer
│   └── js/main.js           # General helpers
├── .env                     # Environment config (private)
├── init_db.py               # DB initialization script
├── run.py                   # Development server
├── wsgi.py                  # Production (Gunicorn) entry
└── requirements.txt
```

---

## 🛡 Features

### Anti-Cheating
- ❌ Right-click disabled
- ❌ Copy/Paste/Print screen blocked
- ❌ Dev tools shortcut blocked
- ⚠ Tab switching: **1st switch = warning**, **2nd switch = auto-terminate**
- 📸 Fullscreen enforcement

### AI Proctoring (OpenCV)
- 📷 Webcam activated during exam
- 📸 Snapshot every 5 seconds
- 😶 **No face detected** → alert shown + logged
- 👥 **Multiple faces** → alert shown + logged
- All events stored in `proctoring_logs` table

### Exam Engine
- 🎲 Random question selection from subject bank
- ⏱ Countdown timer with auto-submit
- 📊 Instant auto-grading
- 💾 Scores saved to database
- 📧 Result email sent via Gmail

### Admin Dashboard
- 📊 Score distribution bar chart
- 📈 Recent scores line chart
- 🏆 Highest / Average / Lowest score
- ❓ Question bank CRUD
- 📝 Exam management (create, toggle, delete)
- 👥 Student management
- 🔍 Result detail with proctoring logs

---

## 🌐 Production Deployment (Gunicorn)

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 4
```

For Render/Railway deployment, set the same environment variables in the dashboard.

---

## 📧 Email Configuration

The system sends an HTML result email after each exam submission. If email is not configured, the system continues to work — only email sending is skipped (with a console warning).

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `Can't connect to MySQL` | Start XAMPP → MySQL |
| `pip install` fails | Run as Administrator |
| Webcam not working | Allow camera in browser popup |
| Email not sending | Check Gmail App Password in `.env` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
