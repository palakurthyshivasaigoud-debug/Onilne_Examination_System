from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models import User, Question, Exam, Result, ProctoringLog
from app import db
from sqlalchemy.orm import joinedload
from datetime import datetime
import json
import re
import os

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

admin_bp = Blueprint('admin', __name__)


def _get_all_subjects():
    """Return a merged, sorted list of subjects from the Subject table +
    any subjects already used in questions (as a fallback)."""
    from app.models import Subject as SubjectModel
    # Subjects from the Subject management table
    managed = [s.name for s in SubjectModel.query.order_by(SubjectModel.name).all()]
    # Subjects already on questions (fallback / legacy)
    from_questions = [
        s[0] for s in db.session.query(Question.subject).distinct().all()
        if s[0]
    ]
    # Merge and deduplicate, preserve order
    merged = managed[:]
    for s in from_questions:
        if s not in merged:
            merged.append(s)
    return sorted(merged)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_students = User.query.filter_by(role='student').count()
    total_questions = Question.query.count()
    total_exams = Exam.query.count()
    total_results = Result.query.count()

    submitted_results = Result.query.filter(
        Result.submitted_at.isnot(None),
        Result.percentage.isnot(None)
    ).all()
    # Safe float conversion, skip any None values
    percentages = [float(r.percentage) for r in submitted_results if r.percentage is not None]

    avg_score = round(sum(percentages) / len(percentages), 1) if percentages else 0
    highest_score = round(max(percentages), 1) if percentages else 0
    lowest_score = round(min(percentages), 1) if percentages else 0

    # Score distribution buckets
    buckets = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for p in percentages:
        if p <= 20: buckets['0-20'] += 1
        elif p <= 40: buckets['21-40'] += 1
        elif p <= 60: buckets['41-60'] += 1
        elif p <= 80: buckets['61-80'] += 1
        else: buckets['81-100'] += 1

    # Recent results for line chart (last 10)
    recent = Result.query.filter(
        Result.submitted_at.isnot(None),
        Result.percentage.isnot(None)
    ).order_by(Result.submitted_at.desc()).limit(10).all()
    recent.reverse()
    line_labels = [f'Attempt {i+1}' for i in range(len(recent))]
    line_data = [float(r.percentage) for r in recent]

    return render_template('admin/dashboard.html',
        total_students=total_students,
        total_questions=total_questions,
        total_exams=total_exams,
        total_results=total_results,
        avg_score=avg_score,
        highest_score=highest_score,
        lowest_score=lowest_score,
        bucket_labels=list(buckets.keys()),
        bucket_data=list(buckets.values()),
        line_labels=line_labels,
        line_data=line_data
    )


# -------- QUESTIONS CRUD --------

@admin_bp.route('/questions')
@login_required
@admin_required
def questions():
    subject_filter = request.args.get('subject', '')
    query = Question.query
    if subject_filter:
        query = query.filter_by(subject=subject_filter)
    questions_list = query.order_by(Question.created_at.desc()).all()
    subjects = db.session.query(Question.subject).distinct().all()
    subjects = [s[0] for s in subjects]
    return render_template('admin/questions.html',
                           questions=questions_list,
                           subjects=subjects,
                           selected_subject=subject_filter)


@admin_bp.route('/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_question():
    if request.method == 'POST':
        q = Question(
            subject=request.form['subject'],
            question_text=request.form['question_text'],
            option_a=request.form['option_a'],
            option_b=request.form['option_b'],
            option_c=request.form['option_c'],
            option_d=request.form['option_d'],
            correct_answer=request.form['correct_answer'],
            marks=int(request.form.get('marks', 1))
        )
        db.session.add(q)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin.questions'))
    subjects = _get_all_subjects()
    return render_template('admin/question_form.html', question=None, action='Add', subjects=subjects)


@admin_bp.route('/questions/edit/<int:qid>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_question(qid):
    q = Question.query.get_or_404(qid)
    if request.method == 'POST':
        q.subject = request.form['subject']
        q.question_text = request.form['question_text']
        q.option_a = request.form['option_a']
        q.option_b = request.form['option_b']
        q.option_c = request.form['option_c']
        q.option_d = request.form['option_d']
        q.correct_answer = request.form['correct_answer']
        q.marks = int(request.form.get('marks', 1))
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin.questions'))
    subjects = _get_all_subjects()
    return render_template('admin/question_form.html', question=q, action='Edit', subjects=subjects)


@admin_bp.route('/questions/delete/<int:qid>', methods=['POST'])
@login_required
@admin_required
def delete_question(qid):
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    flash('Question deleted.', 'warning')
    return redirect(url_for('admin.questions'))


@admin_bp.route('/questions/import-pdf', methods=['GET', 'POST'])
@login_required
@admin_required
def import_pdf():
    """Import MCQ questions from a PDF file."""
    if not PDF_SUPPORT:
        flash('PDF support not installed. Run: pip install pdfplumber', 'danger')
        return redirect(url_for('admin.questions'))

    parsed = []
    errors = []

    if request.method == 'POST':
        # ── IMPORT confirmed questions ─────────────────────────
        if 'confirm_import' in request.form:
            subject = request.form.get('subject', 'General')
            imported = 0
            for i in range(int(request.form.get('count', 0))):
                qt = request.form.get(f'q_{i}_text', '').strip()
                oa = request.form.get(f'q_{i}_a', '').strip()
                ob = request.form.get(f'q_{i}_b', '').strip()
                oc = request.form.get(f'q_{i}_c', '').strip()
                od = request.form.get(f'q_{i}_d', '').strip()
                ans = request.form.get(f'q_{i}_ans', 'A').strip().upper()
                if qt and oa and ob and oc and od and ans in ['A','B','C','D']:
                    q = Question(
                        subject=subject, question_text=qt,
                        option_a=oa, option_b=ob, option_c=oc, option_d=od,
                        correct_answer=ans, marks=1
                    )
                    db.session.add(q)
                    imported += 1
            db.session.commit()
            flash(f'✅ {imported} questions imported successfully!', 'success')
            return redirect(url_for('admin.questions'))

        # ── PARSE uploaded PDF ────────────────────────────────
        if 'pdf_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(url_for('admin.import_pdf'))

        pdf_file = request.files['pdf_file']
        if not pdf_file.filename.lower().endswith('.pdf'):
            flash('Please upload a PDF file.', 'danger')
            return redirect(url_for('admin.import_pdf'))

        subject = request.form.get('subject', 'General').strip()

        try:
            # Extract all text from PDF
            full_text = ''
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + '\n'

            parsed, errors = parse_mcq_from_text(full_text)
            if not parsed:
                flash('No MCQ questions detected. Check the PDF format.', 'warning')

        except Exception as e:
            flash(f'Error reading PDF: {e}', 'danger')

        return render_template('admin/import_pdf.html',
                               parsed=parsed, errors=errors,
                               subject=subject)

    return render_template('admin/import_pdf.html',
                           parsed=[], errors=[], subject='')


def parse_mcq_from_text(text):
    """
    Parse MCQ questions from text.
    Supports formats:
      1. Question text?
      A) Option A    B) Option B    C) Option C    D) Option D
      Answer: A

      Q1. Question text?
      (A) Option A   (B) Option B   ...
      Ans: B
    """
    parsed = []
    errors = []

    # Split into question blocks by numbered pattern
    blocks = re.split(r'\n(?=(?:Q?\d+[\.\)]\s))', text, flags=re.IGNORECASE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        try:
            # Extract question text (first line(s) before options)
            q_match = re.match(
                r'^(?:Q?\d+[\.\)]\s*)(.*?)(?=\n\s*(?:\(?[Aa]\)?[\.\)]|\(?[Aa1]\)?:))',
                block, re.DOTALL
            )
            if not q_match:
                continue
            question_text = q_match.group(1).strip().replace('\n', ' ')

            # Extract options A B C D
            opt_pattern = r'(?:\(?[Aa]\)?[\.\):])\s*(.+?)(?=\s*\(?[Bb]\)?[\.\):])'
            opt_a = re.search(r'\(?[Aa]\)?[\.\):]\s*(.+?)(?=\s*\(?[Bb]\)?[\.\):])', block, re.DOTALL)
            opt_b = re.search(r'\(?[Bb]\)?[\.\):]\s*(.+?)(?=\s*\(?[Cc]\)?[\.\):])', block, re.DOTALL)
            opt_c = re.search(r'\(?[Cc]\)?[\.\):]\s*(.+?)(?=\s*\(?[Dd]\)?[\.\):])', block, re.DOTALL)
            opt_d = re.search(r'\(?[Dd]\)?[\.\):]\s*(.+?)(?=\s*(?:Ans(?:wer)?s?:\s*|$))', block, re.DOTALL | re.IGNORECASE)

            # Extract answer
            ans_match = re.search(r'Ans(?:wer)?s?\s*[:\-]\s*([A-Da-d])', block, re.IGNORECASE)

            if opt_a and opt_b and opt_c and opt_d and ans_match:
                parsed.append({
                    'text': question_text,
                    'a': opt_a.group(1).strip().replace('\n', ' '),
                    'b': opt_b.group(1).strip().replace('\n', ' '),
                    'c': opt_c.group(1).strip().replace('\n', ' '),
                    'd': opt_d.group(1).strip().replace('\n', ' '),
                    'ans': ans_match.group(1).upper()
                })
            else:
                if question_text:
                    errors.append(f'Could not parse options/answer for: "{question_text[:60]}..."')

        except Exception as e:
            errors.append(f'Parse error in block: {str(e)}')

    return parsed, errors


# -------- EXAMS CRUD --------

@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    exams_list = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams_list)


@admin_bp.route('/exams/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_exam():
    subjects = _get_all_subjects()
    if request.method == 'POST':
        exam = Exam(
            title=request.form['title'],
            subject=request.form['subject'],
            duration_minutes=int(request.form['duration_minutes']),
            total_questions=int(request.form['total_questions']),
            created_by=current_user.id,
            is_active=request.form.get('is_active') == 'on'
        )
        db.session.add(exam)
        db.session.commit()
        flash('Exam created!', 'success')
        return redirect(url_for('admin.exams'))
    return render_template('admin/exam_form.html', exam=None, subjects=subjects, action='Create')


@admin_bp.route('/exams/toggle/<int:eid>', methods=['POST'])
@login_required
@admin_required
def toggle_exam(eid):
    exam = Exam.query.get_or_404(eid)
    exam.is_active = not exam.is_active
    db.session.commit()
    status = 'activated' if exam.is_active else 'deactivated'
    flash(f'Exam {status}.', 'info')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/delete/<int:eid>', methods=['POST'])
@login_required
@admin_required
def delete_exam(eid):
    exam = Exam.query.get_or_404(eid)
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted.', 'warning')
    return redirect(url_for('admin.exams'))


# -------- RESULTS & STUDENTS --------

@admin_bp.route('/results')
@login_required
@admin_required
def results():
    results_list = Result.query.options(
        joinedload(Result.student),
        joinedload(Result.exam)
    ).order_by(Result.submitted_at.desc()).all()
    return render_template('admin/results.html', results=results_list)


@admin_bp.route('/results/<int:rid>')
@login_required
@admin_required
def result_detail(rid):
    result = Result.query.options(
        joinedload(Result.student),
        joinedload(Result.exam),
        joinedload(Result.proctoring_logs)
    ).get_or_404(rid)
    logs = ProctoringLog.query.filter_by(result_id=rid).order_by(ProctoringLog.timestamp).all()
    try:
        answers = json.loads(result.answers) if result.answers else {}
    except (json.JSONDecodeError, TypeError):
        answers = {}
    try:
        question_ids = json.loads(result.questions) if result.questions else []
    except (json.JSONDecodeError, TypeError):
        question_ids = []
    questions = Question.query.filter(Question.id.in_(question_ids)).all() if question_ids else []
    return render_template('admin/result_detail.html',
                           result=result, logs=logs,
                           answers=answers, questions=questions)


@admin_bp.route('/students')
@login_required
@admin_required
def students():
    students_list = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    return render_template('admin/students.html', students=students_list)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email'].lower()
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
        else:
            u = User(name=name, email=email, role='student')
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash(f'Student {name} added!', 'success')
            return redirect(url_for('admin.students'))
    return render_template('admin/add_student.html')


@admin_bp.route('/students/delete/<int:uid>', methods=['POST'])
@login_required
@admin_required
def delete_student(uid):
    u = User.query.get_or_404(uid)
    if u.role == 'admin':
        flash('Cannot delete an admin.', 'danger')
    else:
        db.session.delete(u)
        db.session.commit()
        flash('Student deleted.', 'warning')
    return redirect(url_for('admin.students'))


# -------- SUBJECTS MANAGEMENT --------

from app.models import Subject  # ensure Subject is imported

@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    all_subjects = Subject.query.order_by(Subject.name).all()
    for s in all_subjects:
        s.q_count = Question.query.filter_by(subject=s.name).count()
        s.e_count = Exam.query.filter_by(subject=s.name).count()
    return render_template('admin/subjects.html', subjects=all_subjects)


@admin_bp.route('/subjects/add', methods=['POST'])
@login_required
@admin_required
def add_subject():
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    if not name:
        flash('Subject name is required.', 'danger')
        return redirect(url_for('admin.subjects'))
    if Subject.query.filter_by(name=name).first():
        flash(f'Subject "{name}" already exists.', 'warning')
        return redirect(url_for('admin.subjects'))
    s = Subject(name=name, description=desc)
    db.session.add(s)
    db.session.commit()
    flash(f'Subject "{name}" added!', 'success')
    return redirect(url_for('admin.subjects'))


@admin_bp.route('/subjects/edit/<int:sid>', methods=['POST'])
@login_required
@admin_required
def edit_subject(sid):
    s = Subject.query.get_or_404(sid)
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    if not name:
        flash('Subject name cannot be empty.', 'danger')
        return redirect(url_for('admin.subjects'))
    existing = Subject.query.filter_by(name=name).first()
    if existing and existing.id != sid:
        flash(f'Subject "{name}" already exists.', 'warning')
        return redirect(url_for('admin.subjects'))
    s.name = name
    s.description = desc
    db.session.commit()
    flash(f'Subject updated to "{name}".', 'success')
    return redirect(url_for('admin.subjects'))


@admin_bp.route('/subjects/delete/<int:sid>', methods=['POST'])
@login_required
@admin_required
def delete_subject(sid):
    s = Subject.query.get_or_404(sid)
    # Check if subject is in use
    in_questions = Question.query.filter_by(subject=s.name).count()
    in_exams     = Exam.query.filter_by(subject=s.name).count()
    if in_questions > 0 or in_exams > 0:
        flash(f'Cannot delete "{s.name}" — used in {in_questions} question(s) and {in_exams} exam(s).', 'danger')
        return redirect(url_for('admin.subjects'))
    db.session.delete(s)
    db.session.commit()
    flash(f'Subject "{s.name}" deleted.', 'warning')
    return redirect(url_for('admin.subjects'))
