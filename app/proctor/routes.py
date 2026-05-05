from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ProctoringLog
from app import db
from datetime import datetime
import base64
import os
import uuid
import numpy as np

proctor_bp = Blueprint('proctor', __name__)

# Try to import OpenCV — graceful fallback if not available
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def detect_faces(image_data_b64):
    """Detect faces in a base64-encoded image. Returns (face_count, img_path)."""
    if not OPENCV_AVAILABLE:
        return -1, None  # -1 = unknown

    try:
        # Decode base64 image
        img_bytes = base64.b64decode(image_data_b64.split(',')[-1])
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return -1, None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Load Haar cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )

        # Draw rectangles and save screenshot
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

        screenshot_dir = 'static/screenshots'
        os.makedirs(screenshot_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(screenshot_dir, filename)
        cv2.imwrite(filepath, img)

        return len(faces), filepath

    except Exception as e:
        print(f"Face detection error: {e}")
        return -1, None


@proctor_bp.route('/snapshot', methods=['POST'])
@login_required
def snapshot():
    data = request.get_json()
    result_id = data.get('result_id')
    image_b64 = data.get('image')

    if not result_id or not image_b64:
        return jsonify({'error': 'Missing data'}), 400

    face_count, screenshot_path = detect_faces(image_b64)

    alert = None
    event_type = None
    message = None

    if face_count == -1:
        # OpenCV not available or error — just log the snapshot
        event_type = 'snapshot'
        message = 'Periodic snapshot captured'
    elif face_count == 0:
        alert = 'no_face'
        event_type = 'no_face'
        message = 'No face detected in frame'
    elif face_count > 1:
        alert = 'multi_face'
        event_type = 'multi_face'
        message = f'{face_count} faces detected in frame'
    else:
        # Normal — 1 face detected
        event_type = 'snapshot'
        message = 'Face detected - OK'

    # Log significant events
    if event_type in ['no_face', 'multi_face']:
        log = ProctoringLog(
            result_id=result_id,
            event_type=event_type,
            message=message,
            screenshot_path=screenshot_path,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

    return jsonify({
        'face_count': face_count,
        'alert': alert,
        'message': message
    })


@proctor_bp.route('/log_event', methods=['POST'])
@login_required
def log_event():
    """Log tab switches and other non-visual events."""
    data = request.get_json()
    result_id = data.get('result_id')
    event_type = data.get('event_type', 'tab_switch')
    message = data.get('message', 'Event logged')

    if not result_id:
        return jsonify({'error': 'Missing result_id'}), 400

    log = ProctoringLog(
        result_id=result_id,
        event_type=event_type,
        message=message,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'status': 'logged'})
