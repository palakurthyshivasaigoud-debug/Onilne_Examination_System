from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from functools import wraps
from app.models import User, Question, Exam, Result, ProctoringLog
from app import db
from app.email_service import send_result_email
from datetime import datetime, timedelta
import json
import random

student_bp = Blueprint('student', __name__)


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    exams = Exam.query.filter_by(is_active=True).all()
    my_results = Result.query.filter_by(user_id=current_user.id).order_by(
        Result.submitted_at.desc()
    ).all()
    return render_template('student/dashboard.html', exams=exams, results=my_results)


@student_bp.route('/exam/<int:exam_id>/start', methods=['GET', 'POST'])
@login_required
@student_required
def start_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_active:
        flash('This exam is not currently active.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Check if already attempted (no re-attempts)
    existing = Result.query.filter_by(
        user_id=current_user.id,
        exam_id=exam_id
    ).filter(Result.submitted_at.isnot(None)).first()
    if existing:
        flash('You have already completed this exam.', 'info')
        return redirect(url_for('student.result', result_id=existing.id))

    # Pick random questions from subject
    available = Question.query.filter_by(subject=exam.subject).all()
    n = min(exam.total_questions, len(available))
    if n == 0:
        flash('No questions available for this exam subject.', 'danger')
        return redirect(url_for('student.dashboard'))

    selected = random.sample(available, n)
    question_ids = [q.id for q in selected]

    # Create result entry (in progress)
    started_at = datetime.utcnow()
    result = Result(
        user_id=current_user.id,
        exam_id=exam_id,
        total_marks=sum(q.marks for q in selected),
        questions=json.dumps(question_ids),
        started_at=started_at
    )
    db.session.add(result)
    db.session.commit()

    return render_template('student/exam.html',
                           exam=exam,
                           questions=selected,
                           result_id=result.id,
                           duration_seconds=exam.duration_minutes * 60)


@student_bp.route('/exam/submit', methods=['POST'])
@login_required
@student_required
def submit_exam():
    data = request.get_json()
    result_id = data.get('result_id')
    answers = data.get('answers', {})
    auto_submit = data.get('auto_submit', False)
    terminated = data.get('terminated', False)

    result = Result.query.get_or_404(result_id)

    if result.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if result.submitted_at:
        return jsonify({'redirect': url_for('student.result', result_id=result.id)})

    try:
        question_ids = json.loads(result.questions) if result.questions else []
    except (json.JSONDecodeError, TypeError):
        question_ids = []
    questions = Question.query.filter(Question.id.in_(question_ids)).all()

    score = 0
    for q in questions:
        chosen = answers.get(str(q.id), '').upper()
        if chosen == q.correct_answer:
            score += q.marks

    total = result.total_marks or sum(q.marks for q in questions)
    percentage = round((score / total) * 100, 2) if total else 0

    result.score = score
    result.total_marks = total
    result.percentage = percentage
    result.answers = json.dumps(answers)
    result.submitted_at = datetime.utcnow()

    if terminated:
        result.is_disqualified = True
        result.disqualify_reason = 'Exam terminated: tab switch detected'

    db.session.commit()

    # Send email (best effort)
    try:
        send_result_email(current_user, result, result.exam)
    except Exception as e:
        print(f"Email failed: {e}")

    return jsonify({
        'redirect': url_for('student.result', result_id=result.id)
    })


@student_bp.route('/result/<int:result_id>')
@login_required
@student_required
def result(result_id):
    r = Result.query.get_or_404(result_id)
    if r.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    if not r.submitted_at:
        flash('Exam still in progress.', 'info')
        return redirect(url_for('student.dashboard'))

    # ── Results locked until exam duration has elapsed ──────────────────
    unlocked_at = None
    seconds_remaining = 0
    results_locked = False

    if r.started_at and r.exam:
        exam_end_time = r.started_at + timedelta(minutes=r.exam.duration_minutes)
        now = datetime.utcnow()
        if now < exam_end_time:
            results_locked = True
            seconds_remaining = int((exam_end_time - now).total_seconds())
            unlocked_at = exam_end_time

    try:
        answers = json.loads(r.answers) if r.answers else {}
    except (json.JSONDecodeError, TypeError):
        answers = {}
    try:
        question_ids = json.loads(r.questions) if r.questions else []
    except (json.JSONDecodeError, TypeError):
        question_ids = []

    questions = Question.query.filter(Question.id.in_(question_ids)).all() if question_ids else []
    logs = ProctoringLog.query.filter_by(result_id=result_id).count()

    return render_template('student/result.html',
                           result=r,
                           questions=questions,
                           answers=answers,
                           proctor_alerts=logs,
                           results_locked=results_locked,
                           seconds_remaining=seconds_remaining,
                           unlocked_at=unlocked_at)


@student_bp.route('/results')
@login_required
@student_required
def my_results():
    results = Result.query.filter_by(user_id=current_user.id).order_by(
        Result.submitted_at.desc()
    ).all()
    return render_template('student/my_results.html', results=results)
