from flask_mail import Message
from app import mail
from flask import render_template_string


RESULT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f1a; margin: 0; padding: 20px; }
  .container { max-width: 600px; margin: 0 auto; background: #1a1a2e; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(102,126,234,0.3); }
  .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; }
  .header h1 { color: white; margin: 0; font-size: 28px; }
  .header p { color: rgba(255,255,255,0.8); margin: 8px 0 0; }
  .body { padding: 40px 30px; }
  .score-box { background: linear-gradient(135deg, rgba(102,126,234,0.2), rgba(118,75,162,0.2)); border: 2px solid rgba(102,126,234,0.4); border-radius: 12px; padding: 30px; text-align: center; margin: 20px 0; }
  .score-big { font-size: 64px; font-weight: 900; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1; }
  .score-label { color: #aaa; font-size: 14px; margin-top: 8px; }
  .stats { display: flex; gap: 16px; margin: 20px 0; }
  .stat { flex: 1; background: rgba(255,255,255,0.05); border-radius: 10px; padding: 16px; text-align: center; }
  .stat-value { font-size: 24px; font-weight: 700; color: #667eea; }
  .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
  .grade-badge { display: inline-block; padding: 8px 24px; border-radius: 50px; font-size: 18px; font-weight: 700; margin: 10px 0; }
  .grade-a { background: rgba(76,217,100,0.2); color: #4cd964; border: 2px solid #4cd964; }
  .grade-b { background: rgba(90,200,250,0.2); color: #5ac8fa; border: 2px solid #5ac8fa; }
  .grade-c { background: rgba(255,204,0,0.2); color: #ffcc00; border: 2px solid #ffcc00; }
  .grade-f { background: rgba(255,59,48,0.2); color: #ff3b30; border: 2px solid #ff3b30; }
  p { color: #ccc; line-height: 1.6; }
  .footer { background: rgba(255,255,255,0.03); padding: 20px 30px; text-align: center; color: #666; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🎓 Exam Result</h1>
    <p>{{ exam_title }}</p>
  </div>
  <div class="body">
    <p>Dear <strong style="color:#fff">{{ student_name }}</strong>,</p>
    <p>Your exam has been evaluated. Here are your results:</p>

    <div class="score-box">
      <div class="score-big">{{ percentage }}%</div>
      <div class="score-label">Overall Score</div>
      <span class="grade-badge {% if percentage >= 80 %}grade-a{% elif percentage >= 60 %}grade-b{% elif percentage >= 40 %}grade-c{% else %}grade-f{% endif %}">
        Grade: {% if percentage >= 80 %}A{% elif percentage >= 60 %}B{% elif percentage >= 40 %}C{% else %}F{% endif %}
      </span>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="stat-value">{{ score }}</div>
        <div class="stat-label">Marks Obtained</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ total }}</div>
        <div class="stat-label">Total Marks</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ correct }}</div>
        <div class="stat-label">Correct Answers</div>
      </div>
    </div>

    {% if disqualified %}
    <p style="color:#ff3b30;background:rgba(255,59,48,0.1);border-radius:8px;padding:12px;">
      ⚠️ <strong>Note:</strong> Your exam was flagged for integrity violations. Result may be subject to review.
    </p>
    {% endif %}

    <p>Thank you for taking the exam. Best of luck with your results!</p>
  </div>
  <div class="footer">
    © 2024 Online Examination System · This is an automated email, please do not reply.
  </div>
</div>
</body>
</html>
"""


def send_result_email(user, result, exam):
    """Send exam result email to the student."""
    from flask import current_app
    try:
        percentage = result.percentage or 0
        score = result.score or 0
        total = result.total_marks or 0

        html_content = render_template_string(
            RESULT_EMAIL_TEMPLATE,
            student_name=user.name,
            exam_title=exam.title,
            percentage=round(percentage, 1),
            score=score,
            total=total,
            correct=score,  # 1 mark per question
            disqualified=result.is_disqualified
        )

        msg = Message(
            subject=f'Exam Result: {exam.title}',
            recipients=[user.email],
            html=html_content
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False
