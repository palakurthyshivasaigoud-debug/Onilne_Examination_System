/* =====================================================
   exam.js — Fixed version:
   - Tab switch: INSTANT termination (first switch)
   - Fullscreen: request only (no termination on exit)
   - MCQ selection: reliable click handler
   - Submit: clean flow
   ===================================================== */

'use strict';

// ── State ─────────────────────────────────────────────
let timerInterval = null;
let snapshotInterval = null;
let webcamStream = null;
let screenStream = null;
let tabSwitchCount = 0;
let snapCount = 0;
let alertCount = 0;
let answers = {};
let examTerminated = false;
let examStarted = false; // guard: don't terminate before exam loads

// ── Anti Cheat: Disable right-click ──────────────────
document.addEventListener('contextmenu', e => e.preventDefault());

// ── Anti Cheat: Disable keyboard shortcuts ───────────
document.addEventListener('keydown', e => {
    const blocked = [
        e.ctrlKey && ['c', 'v', 'x', 'a', 'u', 's', 'p'].includes(e.key.toLowerCase()),
        e.key === 'F12',
        e.key === 'PrintScreen',
        e.ctrlKey && e.shiftKey && ['i', 'j', 'c', 'k'].includes(e.key.toLowerCase())
    ];
    if (blocked.some(Boolean)) {
        e.preventDefault();
        return false;
    }
});

// ── INSTANT Tab Switch Termination ───────────────────
// Only fires AFTER exam has started (examStarted flag prevents premature termination)
document.addEventListener('visibilitychange', () => {
    if (!examStarted || examTerminated) return;
    if (document.hidden) {
        tabSwitchCount++;
        logEvent('tab_switch', `Tab switched — TERMINATED (count: ${tabSwitchCount})`);
        terminateExam('⚠ Tab Switch Detected!',
            'You switched tabs or minimized the window. Your exam has been automatically terminated and submitted.');
    }
});

// ── Fullscreen: request only, no forced termination ──
function requestFullscreen() {
    const el = document.documentElement;
    try {
        if (el.requestFullscreen) el.requestFullscreen();
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    } catch (e) { /* silently ignore — fullscreen may not be available */ }
}

// ── Timer ─────────────────────────────────────────────
function startTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        timeLeft--;
        updateTimerDisplay();
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            forceSubmit(false, true); // auto-submit when time ends
        }
    }, 1000);
}

function updateTimerDisplay() {
    const mins = Math.floor(timeLeft / 60).toString().padStart(2, '0');
    const secs = (timeLeft % 60).toString().padStart(2, '0');
    const el = document.getElementById('timer');
    if (!el) return;
    el.textContent = `${mins}:${secs}`;
    el.className = 'timer-display';
    if (timeLeft <= 60) el.classList.add('danger');
    else if (timeLeft <= 300) el.classList.add('warning');
}

// ── Question Navigation ───────────────────────────────
function goToQuestion(idx) {
    document.querySelectorAll('.q-card').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.q-nav-btn').forEach(b => b.classList.remove('current'));
    const card = document.getElementById(`q-${idx}`);
    const nav = document.getElementById(`nav-${idx}`);
    if (card) card.classList.add('active');
    if (nav) nav.classList.add('current');
}

// ── MCQ Answer Selection ──────────────────────────────
function selectAnswer(qid, option, qIdx) {
    // Store answer
    answers[String(qid)] = option;

    // Mark the radio button as checked
    const radio = document.querySelector(`#q-${qIdx} input[name="q-${qid}"][value="${option}"]`);
    if (radio) radio.checked = true;

    // Visual: highlight selected option label
    const card = document.getElementById(`q-${qIdx}`);
    if (card) {
        card.querySelectorAll('.option-label').forEach(lbl => lbl.classList.remove('selected'));
        const selectedLabel = document.getElementById(`opt-${qid}-${option}`);
        if (selectedLabel) selectedLabel.classList.add('selected');
    }

    // Update nav button
    const navBtn = document.getElementById(`nav-${qIdx}`);
    if (navBtn) navBtn.classList.add('answered');

    // Update progress counter
    const prog = document.getElementById('progress-label');
    if (prog) prog.textContent = `${Object.keys(answers).length} / ${TOTAL_QUESTIONS}`;
}

// ── Submit ────────────────────────────────────────────
function confirmSubmit() {
    const answered = Object.keys(answers).length;
    const remaining = TOTAL_QUESTIONS - answered;
    if (remaining > 0) {
        if (!confirm(`You have ${remaining} unanswered question(s). Submit anyway?`)) return;
    }
    forceSubmit(false, false);
}

function terminateExam(title, message) {
    if (examTerminated) return;
    examTerminated = true;
    clearInterval(timerInterval);
    clearInterval(snapshotInterval);

    const overlay = document.getElementById('terminateOverlay');
    const titEl = document.getElementById('terminateTitle');
    const msgEl = document.getElementById('terminateMsg');
    if (overlay) overlay.style.display = 'flex';
    if (titEl) titEl.textContent = title || 'Exam Terminated';
    if (msgEl) msgEl.textContent = message || 'Your exam has been terminated.';

    setTimeout(() => forceSubmit(true, false), 3000);
}

function forceSubmit(terminated = false, autoSubmit = false) {
    clearInterval(timerInterval);
    clearInterval(snapshotInterval);
    if (webcamStream) webcamStream.getTracks().forEach(t => t.stop());
    if (screenStream) screenStream.getTracks().forEach(t => t.stop());

    const payload = {
        result_id: RESULT_ID,
        answers: answers,
        auto_submit: autoSubmit,
        terminated: terminated
    };

    fetch(SUBMIT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => {
            if (data.redirect) window.location.href = data.redirect;
        })
        .catch(() => { window.location.href = '/student/dashboard'; });
}

// ── Webcam Proctoring ─────────────────────────────────
async function initWebcam() {
    const video = document.getElementById('webcam');
    const status = document.getElementById('camStatus');
    const errorBox = document.getElementById('camRequired');
    const dot = document.getElementById('camDot');

    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 320, height: 240, facingMode: 'user' },
            audio: false
        });
        video.srcObject = webcamStream;
        if (status) status.textContent = '🟢 Camera Active';
        if (dot) dot.style.background = '#4cd964';
        if (errorBox) errorBox.style.display = 'none';
        startSnapshotCapture();
        return true;
    } catch (err) {
        console.warn('Camera not available:', err);
        if (status) status.textContent = '⚠ Camera unavailable';
        if (dot) dot.style.background = '#ff9500';
        // Log but don't terminate — allow exam without webcam
        logEvent('camera_denied', 'Student camera access denied or unavailable');
        return false;
    }
}

// ── Screen Share ─────────────────────────────────────
async function initScreenShare() {
    const statusEl = document.getElementById('screenShareStatus');
    const placeholder = document.getElementById('screenPlaceholder');
    try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: 'always' },
            audio: false
        });
        const screenVid = document.getElementById('screenPreview');
        if (screenVid) {
            screenVid.srcObject = screenStream;
            screenVid.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
        if (statusEl) { statusEl.textContent = '🟢 Screen Shared'; statusEl.style.color = '#4cd964'; }

        screenStream.getVideoTracks()[0].addEventListener('ended', () => {
            if (!examTerminated) {
                logEvent('screen_share_stopped', 'Student stopped screen sharing');
                if (statusEl) { statusEl.textContent = '⚠ Screen share stopped'; statusEl.style.color = '#ff3b30'; }
            }
        });
    } catch (err) {
        console.warn('Screen share not available:', err);
        if (statusEl) { statusEl.textContent = '⚠ Screen share declined'; statusEl.style.color = '#ff9500'; }
        logEvent('screen_share_denied', 'Student declined screen share');
    }
}

// ── Snapshot Capture ──────────────────────────────────
function captureSnapshot() {
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('camCanvas');
    if (!webcamStream || !video || video.videoWidth === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const dataURL = canvas.toDataURL('image/jpeg', 0.6);

    snapCount++;
    const sc = document.getElementById('snapCount');
    if (sc) sc.textContent = snapCount;

    fetch(SNAPSHOT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ result_id: RESULT_ID, image: dataURL })
    })
        .then(r => r.json())
        .then(data => {
            const camAlert = document.getElementById('camAlert');
            const dot = document.getElementById('camDot');
            if (data.alert === 'no_face') {
                showCamAlert('alert-no-face', '😶 No Face Detected!');
                if (dot) dot.style.background = '#ff3b30';
                alertCount++;
            } else if (data.alert === 'multi_face') {
                showCamAlert('alert-multi-face', '👥 Multiple Faces Detected!');
                if (dot) dot.style.background = '#ff9500';
                alertCount++;
            } else {
                if (camAlert) camAlert.style.display = 'none';
                if (dot) dot.style.background = '#4cd964';
            }
            const ac = document.getElementById('alertCount');
            if (ac) ac.textContent = alertCount;
        })
        .catch(() => { });
}

function showCamAlert(cls, msg) {
    const el = document.getElementById('camAlert');
    if (!el) return;
    el.className = 'cam-alert ' + cls;
    el.textContent = msg;
    el.style.display = 'block';
}

function startSnapshotCapture() {
    captureSnapshot();
    snapshotInterval = setInterval(captureSnapshot, 5000);
}

// ── Log Event ─────────────────────────────────────────
function logEvent(type, message) {
    fetch(LOG_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ result_id: RESULT_ID, event_type: type, message })
    }).catch(() => { });
}

// ── Prevent accidental page leave ─────────────────────
window.addEventListener('beforeunload', e => {
    if (!examTerminated) {
        e.preventDefault();
        e.returnValue = 'Leaving will auto-submit your exam!';
    }
});

// ── INIT ──────────────────────────────────────────────
window.addEventListener('load', async () => {
    // Set first question active and current
    goToQuestion(0);

    // Request fullscreen (best effort)
    requestFullscreen();

    // Start camera and screen share
    await initWebcam();
    await initScreenShare();

    // Start exam timer
    startTimer();

    // IMPORTANT: Only enable tab-switch detection AFTER exam is fully set up
    setTimeout(() => {
        examStarted = true;
        console.log('Exam started — tab switch detection active');
    }, 1500);
});
