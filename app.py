import sys, subprocess, importlib

def _ensure(pkg, import_as=None):
    try:
        importlib.import_module(import_as or pkg)
    except ImportError:
        print(f"  [AUTO-INSTALL] {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

print("\n" + "="*52)
print("  SMART CROWD PANIC DETECTION AI")
print("  REAL-TIME CROWD SAFETY & BEHAVIOR SYSTEM")
print("  Dev/Creator : Bade Hari Preetham")
print("="*52)
print("\n  [INIT] Checking dependencies...\n")
 
for pkg, imp in [
    ("ultralytics", "ultralytics"),
    ("opencv-python", "cv2"),
    ("numpy", "numpy"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("Pillow", "PIL"),
    ("supervision", "supervision"),
    ("flask",       "flask"),
]:
    _ensure(pkg, imp)

print("\n  Loading YOLO detection engine...")
print("  Initializing motion analysis system...")
print("  Starting crowd intelligence pipeline...")
print("  Activating panic detection module...\n")
print("="*52 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import os, time, math, argparse, datetime, collections, warnings
warnings.filterwarnings("ignore")

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from scipy.ndimage import gaussian_filter
import time as _time_mod
import csv as _csv
import pygame as _pygame
import smtplib as _smtplib
import ssl as _ssl
from email.mime.multipart import MIMEMultipart as _MIMEMultipart
from email.mime.text import MIMEText as _MIMEText
from email.mime.base import MIMEBase as _MIMEBase
from email import encoders as _encoders
import threading as _threading
import base64 as _base64
from flask import Flask as _Flask, Response as _Response, jsonify as _jsonify
import json as _json
_pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
_pygame.mixer.init()
# ─────────────────────────────────────────────────────────────────────────────
# PALETTE / CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
NEON_CYAN   = (0,   255, 255)
NEON_GREEN  = (57,  255,  20)
NEON_RED    = (255,  50,  50)
NEON_ORANGE = (255, 140,   0)
NEON_PINK   = (255,  20, 147)
NEON_BLUE   = ( 30, 144, 255)
NEON_YELLOW = (255, 255,   0)
NEON_PURPLE = (180,  50, 255)
PANEL_BG    = (6,   10,  18)
GRID_COLOR  = (0,   60, 100)

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL CONFIGURATION  ← fill in your details
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_CFG = {
    "enabled":           True,
    "sender_email":      "haripreetham.1111@gmail.com",
    "sender_password":   "zeorhhbaxatxbllk",
    "smtp_host":         "smtp.gmail.com",
    "smtp_port":         587,
    "recipients":        ["haripreethambade@gmail.com"],
    "alert_on":          ["MASS PANIC", "PANIC RISK"],
    "cooldown_sec":      60,
    "attach_screenshot": True,
}

# ─────────────────────────────────────────────────────────────────────────────
# FLASK WEB DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

_flask_app   = _Flask(__name__)
_state_lock  = _threading.Lock()
_frame_lock  = _threading.Lock()
_latest_jpeg = None

_shared = {
    "panic_score":  0.0,
    "panic_state":  "NORMAL",
    "gated_state":  "NORMAL",
    "crowd_count":  0,
    "fps":          0.0,
    "frame_idx":    0,
    "avg_speed":    0.0,
    "entropy":      0.0,
    "convergence":  0.0,
    "spike_ratio":  0.0,
    "dir_chaos":    0.0,
    "density_state":"LOW DENSITY",
    "alert_log":    [],
}

def _push_jpeg(frame):
    global _latest_jpeg
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if ok:
        with _frame_lock:
            _latest_jpeg = buf.tobytes()

def _update_shared(**kwargs):
    with _state_lock:
        _shared.update(kwargs)

def _gen_frames():
    while True:
        with _frame_lock:
            frame = _latest_jpeg
        if frame is None:
            _time_mod.sleep(0.05)
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

@_flask_app.route("/")
def _index():
    return _Response(open("crowd_dashboard.html").read(), mimetype="text/html")

@_flask_app.route("/video_feed")
def _video_feed():
    return _Response(_gen_frames(),
                     mimetype="multipart/x-mixed-replace; boundary=frame")

@_flask_app.route("/api/state")
def _api_state():
    with _state_lock:
        return _jsonify(dict(_shared))

@_flask_app.route("/api/alerts")
def _api_alerts():
    with _state_lock:
        return _jsonify(_shared["alert_log"][-50:])

def _start_dashboard(port=5001):
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    _flask_app.run(host="0.0.0.0", port=port,
                   threaded=True, use_reloader=False)

OUTPUT_FILE   = "output_crowd_panic_ai.mp4"
BEV_W, BEV_H  = 300, 400
TRAIL_LEN     = 24
PERSON_CLASS  = 0

# Thresholds
SPEED_SPIKE_THRESH    = 18.0   # px/frame → panic velocity
CHAOS_THRESH_WARN     = 0.45
CHAOS_THRESH_PANIC    = 0.70
DENSITY_MODERATE      = 8
DENSITY_HIGH          = 18
DENSITY_CRITICAL      = 35
CONVERGENCE_THRESH    = 0.60   # flow convergence → stampede risk


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTWEIGHT IoU TRACKER
# ─────────────────────────────────────────────────────────────────────────────

class PersonTrack:
    def __init__(self, tid, bbox):
        self.id      = tid
        self.bbox    = bbox
        self.hits    = 1
        self.misses  = 0
        self.history = collections.deque(maxlen=TRAIL_LEN)
        self.vel_history = collections.deque(maxlen=12)
        self.speed   = 0.0
        self.direction = 0.0   # radians
        cx, cy = self._center(bbox)
        self.history.append((cx, cy))

    @staticmethod
    def _center(b):
        return int((b[0]+b[2])/2), int((b[1]+b[3])/2)

    def update(self, bbox):
        px, py = self.history[-1]
        cx, cy = self._center(bbox)
        dx, dy = cx - px, cy - py
        spd = math.hypot(dx, dy)
        self.vel_history.append((dx, dy, spd))
        self.speed = spd
        self.direction = math.atan2(dy, dx)
        self.bbox = bbox
        self.history.append((cx, cy))
        self.hits  += 1
        self.misses = 0

    @property
    def avg_speed(self):
        if not self.vel_history: return 0.0
        return np.mean([v[2] for v in self.vel_history])

    @property
    def direction_variance(self):
        """How erratic are direction changes — key panic indicator."""
        if len(self.vel_history) < 3: return 0.0
        dirs = [math.atan2(v[1], v[0]) for v in self.vel_history if v[2] > 1]
        if len(dirs) < 2: return 0.0
        diffs = [abs(math.sin(dirs[i]-dirs[i-1])) for i in range(1, len(dirs))]
        return float(np.mean(diffs))


class IoUTracker:
    def __init__(self, iou_thresh=0.30, max_misses=6):
        self.tracks     = {}
        self.next_id    = 1
        self.iou_thresh = iou_thresh
        self.max_misses = max_misses

    @staticmethod
    def _iou(a, b):
        ix1 = max(a[0],b[0]); iy1 = max(a[1],b[1])
        ix2 = min(a[2],b[2]); iy2 = min(a[3],b[3])
        iw  = max(0, ix2-ix1); ih = max(0, iy2-iy1)
        inter = iw*ih
        ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
        return inter/ua if ua > 0 else 0

    def update(self, bboxes):
        matched_t, matched_d = set(), set()
        bboxes = list(bboxes)
        for tid, t in self.tracks.items():
            best_iou, best_di = 0, -1
            for di, bb in enumerate(bboxes):
                if di in matched_d: continue
                iou = self._iou(t.bbox, bb)
                if iou > best_iou:
                    best_iou, best_di = iou, di
            if best_iou >= self.iou_thresh:
                t.update(bboxes[best_di])
                matched_t.add(tid)
                matched_d.add(best_di)
        for tid in list(self.tracks):
            if tid not in matched_t:
                self.tracks[tid].misses += 1
        for di, bb in enumerate(bboxes):
            if di not in matched_d:
                self.tracks[self.next_id] = PersonTrack(self.next_id, bb)
                self.next_id += 1
        self.tracks = {t: v for t, v in self.tracks.items()
                       if v.misses <= self.max_misses}
        return self.tracks


# ─────────────────────────────────────────────────────────────────────────────
# OPTICAL FLOW ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class OpticalFlowEngine:
    def __init__(self):
        self.prev_gray = None
        self.flow      = None

    def update(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))
        if self.prev_gray is None:
            self.prev_gray = gray
            return None
        self.flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=12,
            iterations=3, poly_n=5, poly_sigma=1.1, flags=0
        )
        self.prev_gray = gray
        return self.flow

    def render_flow(self, frame, step=18):
        if self.flow is None: return
        h, w = frame.shape[:2]
        fh, fw = self.flow.shape[:2]
        sx, sy = w/fw, h/fh
        for y in range(0, fh, step):
            for x in range(0, fw, step):
                dx, dy = self.flow[y, x]
                mag = math.hypot(dx, dy)
                if mag < 0.5: continue
                ox, oy = int(x*sx), int(y*sy)
                ex = int(ox + dx*sx*2)
                ey = int(oy + dy*sy*2)
                alpha = min(1.0, mag/8.0)
                color = (
                    int(255*alpha),
                    int((1-alpha)*200),
                    int((1-alpha)*255)
                )
                cv2.arrowedLine(frame, (ox,oy), (ex,ey), color, 1,
                                tipLength=0.35, line_type=cv2.LINE_AA)

    def compute_convergence(self):
        """Flow convergence score → stampede indicator (0→1)."""
        if self.flow is None: return 0.0
        dx = self.flow[:,:,0]
        dy = self.flow[:,:,1]
        # divergence  ∂u/∂x + ∂v/∂y
        div_x = np.gradient(dx, axis=1)
        div_y = np.gradient(dy, axis=0)
        divergence = div_x + div_y
        # Strong negative divergence → convergent flow → stampede risk
        conv_score = float(np.clip(-np.mean(divergence) * 5, 0, 1))
        return conv_score

    def compute_motion_entropy(self):
        """How chaotic are motion directions? (0=uniform, 1=total chaos)"""
        if self.flow is None: return 0.0
        dx = self.flow[:,:,0].ravel()
        dy = self.flow[:,:,1].ravel()
        mag = np.hypot(dx, dy)
        mask = mag > 0.5
        if mask.sum() < 10: return 0.0
        angles = np.arctan2(dy[mask], dx[mask])
        hist, _ = np.histogram(angles, bins=16, range=(-np.pi, np.pi), density=True)
        hist += 1e-9
        entropy = -np.sum(hist * np.log(hist + 1e-9))
        return float(np.clip(entropy / math.log(16), 0, 1))


# ─────────────────────────────────────────────────────────────────────────────
# PANIC DETECTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class PanicDetector:
    def __init__(self):
        self.panic_history = collections.deque(maxlen=20)

    def analyze(self, tracks, flow_engine, crowd_count):
        """Returns (panic_state, panic_score, metrics_dict)"""

        # ── Velocity spike ratio ──
        speeds = [t.avg_speed for t in tracks.values()]
        if speeds:
            spike_ratio = sum(s > SPEED_SPIKE_THRESH for s in speeds) / len(speeds)
            avg_spd = np.mean(speeds)
        else:
            spike_ratio, avg_spd = 0.0, 0.0

        # ── Direction chaos ──
        dir_vars = [t.direction_variance for t in tracks.values()]
        dir_chaos = float(np.mean(dir_vars)) if dir_vars else 0.0

        # ── Optical flow metrics ──
        motion_entropy  = flow_engine.compute_motion_entropy()
        convergence     = flow_engine.compute_convergence()

        # ── Density pressure ──
        density_pressure = min(1.0, crowd_count / max(DENSITY_CRITICAL, 1))

        # ── Composite panic score ──
        panic_score = (
            spike_ratio     * 0.25 +
            dir_chaos       * 0.25 +
            motion_entropy  * 0.20 +
            convergence     * 0.15 +
            density_pressure* 0.15
        )
        panic_score = float(np.clip(panic_score, 0.0, 1.0))
        self.panic_history.append(panic_score)
        smoothed = float(np.mean(self.panic_history))

        # ── State classification ──
        if smoothed < 0.25:
            state = "NORMAL"
        elif smoothed < 0.50:
            state = "ALERT"
        elif smoothed < 0.72:
            state = "PANIC RISK"
        else:
            state = "MASS PANIC"

        metrics = dict(
            spike_ratio=spike_ratio,
            dir_chaos=dir_chaos,
            motion_entropy=motion_entropy,
            convergence=convergence,
            density_pressure=density_pressure,
            avg_speed=avg_spd,
        )
        return state, smoothed, metrics

# ─────────────────────────────────────────────────────────────────────────────
# SUSTAINED ALERT GATE
# ─────────────────────────────────────────────────────────────────────────────

class SustainedAlertGate:
    """
    Risk level must persist for sustain_sec seconds
    before it is passed through to alerts/sound/email.
    Prevents single-frame spikes from triggering alarms.
    """
    def __init__(self, sustain_sec=3.0):
        self._sustain    = sustain_sec
        self._first_seen = {}
        self._current    = "NORMAL"
        self._confirmed  = "NORMAL"

    def update(self, state):
        now = _time_mod.time()
        if state == "NORMAL":
            self._first_seen = {}
            self._current    = "NORMAL"
            self._confirmed  = "NORMAL"
            return "NORMAL"
        if state != self._current:
            self._first_seen = {state: now}
            self._current    = state
            return self._confirmed
        first = self._first_seen.get(state, now)
        if (now - first) >= self._sustain:
            self._confirmed = state
        return self._confirmed
    
# ─────────────────────────────────────────────────────────────────────────────
# SOUND ALARMER
# ─────────────────────────────────────────────────────────────────────────────

class SoundAlarmer:
    """Plays alarm sound on MASS PANIC or PANIC RISK state."""

    ALARM_STATES = ["MASS PANIC", "PANIC RISK"]
    COOLDOWN_SEC = 15
    ALARM_FILE   = "alarm.mp3"
    VOLUME       = 0.9

    def __init__(self):
        self._last_play = {}
        self._ready     = False
        try:
            if os.path.exists(self.ALARM_FILE):
                _pygame.mixer.music.load(self.ALARM_FILE)
                print(f"  [SOUND] Loaded {self.ALARM_FILE}")
            else:
                print(f"  [SOUND] alarm.mp3 not found — generating beep...")
                path = self._generate_beep()
                _pygame.mixer.music.load(path)
            _pygame.mixer.music.set_volume(self.VOLUME)
            self._ready = True
            print(f"  [SOUND] Alarm ready | triggers: {self.ALARM_STATES}")
        except Exception as e:
            print(f"  [SOUND] Init failed: {e}")

    def _generate_beep(self):
        import wave
        sr = 44100; dur = 0.8; freq = 880
        t  = np.linspace(0, dur, int(sr*dur), endpoint=False)
        w  = np.sin(2*np.pi*freq*t)
        env = np.ones(len(t))
        fade = int(sr*0.05)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        samples = (w * env * 32767).astype(np.int16)
        sil = np.zeros(int(sr*0.2), dtype=np.int16)
        full = np.concatenate([samples, sil, samples, sil, samples])
        path = "alarm_beep.wav"
        with wave.open(path, "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2)
            wf.setframerate(sr); wf.writeframes(full.tobytes())
        return path

    def notify(self, state):
        if not self._ready: return
        if state == "NORMAL":
            if _pygame.mixer.music.get_busy():
                _pygame.mixer.music.stop()
            return
        if state not in self.ALARM_STATES: return
        now = _time_mod.time()
        if now - self._last_play.get(state, 0) < self.COOLDOWN_SEC: return
        self._last_play[state] = now
        import threading
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        try:
            _pygame.mixer.music.play(loops=1)
            print("[SOUND] 🔊 Alarm playing...")
        except Exception as e:
            print(f"[SOUND] Play error: {e}")

    def close(self):
        try: _pygame.mixer.quit()
        except: pass


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL ALERTER
# ─────────────────────────────────────────────────────────────────────────────

class EmailAlerter:
    def __init__(self):
        self._enabled    = EMAIL_CFG["enabled"]
        self._last_sent  = {}
        self._lock       = _threading.Lock()
        if self._enabled:
            print(f"  [EMAIL] Alerts enabled → {EMAIL_CFG['recipients']}")
            print(f"  [EMAIL] Triggers on    : {EMAIL_CFG['alert_on']}")
            print(f"  [EMAIL] Cooldown       : {EMAIL_CFG['cooldown_sec']}s")
        else:
            print("  [EMAIL] Disabled.")

    def notify(self, state, panic_score, crowd_count,
               frame_idx, screenshot_path=None):
        if not self._enabled: return
        if state not in EMAIL_CFG["alert_on"]: return
        with self._lock:
            if _time_mod.time() - self._last_sent.get(state, 0) < EMAIL_CFG["cooldown_sec"]:
                return
            self._last_sent[state] = _time_mod.time()
        _threading.Thread(
            target=self._send,
            args=(state, panic_score, crowd_count, frame_idx, screenshot_path),
            daemon=True
        ).start()

    def _send(self, state, panic_score, crowd_count,
              frame_idx, screenshot_path):
        try:
            now_str  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subject  = f"[{state}] 🚨 Crowd Panic Alert — {now_str}"
            sc = {"MASS PANIC": "#ff2d2d", "PANIC RISK": "#ff8c00",
                  "ALERT": "#ffd400"}.get(state, "#ffffff")
            html = f"""
<html><body style="font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;">
<div style="max-width:520px;margin:0 auto;border:1px solid #30363d;border-radius:8px;overflow:hidden;">
  <div style="background:{sc}22;border-bottom:2px solid {sc};padding:18px 24px;">
    <h2 style="margin:0;color:{sc};font-size:20px;letter-spacing:2px;">
      🚨 {state} — CROWD HAZARD DETECTED
    </h2>
    <p style="margin:4px 0 0;color:#8b949e;font-size:12px;">{now_str}</p>
  </div>
  <div style="padding:20px 24px;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <tr style="border-bottom:1px solid #21262d;">
        <td style="padding:10px 0;color:#8b949e;">Alert State</td>
        <td style="padding:10px 0;color:{sc};font-weight:bold;">{state}</td>
      </tr>
      <tr style="border-bottom:1px solid #21262d;">
        <td style="padding:10px 0;color:#8b949e;">Panic Score</td>
        <td style="padding:10px 0;color:#ff2d2d;font-weight:bold;">{panic_score:.1%}</td>
      </tr>
      <tr style="border-bottom:1px solid #21262d;">
        <td style="padding:10px 0;color:#8b949e;">Crowd Count</td>
        <td style="padding:10px 0;">{crowd_count} people</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#8b949e;">Frame</td>
        <td style="padding:10px 0;">#{frame_idx:05d}</td>
      </tr>
    </table>
  </div>
  {"<div style='padding:0 24px 16px;color:#8b949e;font-size:12px;'>📎 Screenshot attached.</div>" if screenshot_path else ""}
  <div style="background:#161b22;padding:12px 24px;border-top:1px solid #21262d;">
    <p style="margin:0;color:#484f58;font-size:11px;">
      Smart Crowd Panic Detection AI &nbsp;|&nbsp; Bade Hari Preetham
    </p>
  </div>
</div>
</body></html>"""
            msg = _MIMEMultipart("alternative")
            msg["From"]    = EMAIL_CFG["sender_email"]
            msg["To"]      = ", ".join(EMAIL_CFG["recipients"])
            msg["Subject"] = subject
            msg.attach(_MIMEText(html, "html"))

            if EMAIL_CFG["attach_screenshot"] and screenshot_path and \
               os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    part = _MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    _encoders.encode_base64(part)
                    part.add_header("Content-Disposition",
                        f"attachment; filename={os.path.basename(screenshot_path)}")
                    msg.attach(part)

            ctx = _ssl.create_default_context()
            with _smtplib.SMTP(EMAIL_CFG["smtp_host"],
                               EMAIL_CFG["smtp_port"]) as srv:
                srv.ehlo(); srv.starttls(context=ctx)
                srv.login(EMAIL_CFG["sender_email"],
                          EMAIL_CFG["sender_password"])
                srv.sendmail(EMAIL_CFG["sender_email"],
                             EMAIL_CFG["recipients"], msg.as_string())
            print(f"  [EMAIL] ✅ Sent {state} alert")
        except _smtplib.SMTPAuthenticationError:
            print("  [EMAIL] ❌ Auth failed — check EMAIL_CFG credentials")
        except Exception as e:
            print(f"  [EMAIL] ❌ Error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# SESSION REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

class SessionReportGenerator:
    def __init__(self, log_dir="crowd_logs"):
        self._log_dir = log_dir

    def generate(self, frame_csv_path, alert_csv_path,
                 screenshot_dir, session_ts):
        frames = []; alerts = []
        try:
            with open(frame_csv_path, newline="") as f:
                frames = list(_csv.DictReader(f))
        except Exception as e:
            print(f"  [REPORT] Cannot read log: {e}"); return None
        try:
            with open(alert_csv_path, newline="") as f:
                alerts = list(_csv.DictReader(f))
        except: pass

        if not frames:
            print("  [REPORT] No data — skipped."); return None

        total_frames  = len(frames)
        panic_vals    = [float(r["panic_score"]) for r in frames]
        crowd_vals    = [int(r["crowd_count"])   for r in frames]
        max_panic     = max(panic_vals)  if panic_vals  else 0
        avg_panic     = sum(panic_vals)  / len(panic_vals) if panic_vals else 0
        max_crowd     = max(crowd_vals)  if crowd_vals  else 0
        avg_crowd     = sum(crowd_vals)  / len(crowd_vals) if crowd_vals else 0
        state_counts  = {"NORMAL":0,"ALERT":0,"PANIC RISK":0,"MASS PANIC":0}
        for r in frames:
            s = r.get("gated_state","NORMAL")
            state_counts[s] = state_counts.get(s, 0) + 1

        fps_vals = []
        for r in frames:
            try: fps_vals.append(float(r["fps"]))
            except: pass
        avg_fps = sum(fps_vals)/len(fps_vals) if fps_vals else 0

        total_alerts = len(alerts)
        a_mass  = sum(1 for a in alerts if a.get("gated_state")=="MASS PANIC")
        a_panic = sum(1 for a in alerts if a.get("gated_state")=="PANIC RISK")
        a_alert = sum(1 for a in alerts if a.get("gated_state")=="ALERT")

        step     = max(1, total_frames//200)
        sampled  = frames[::step]
        c_labels = [r["frame"]       for r in sampled]
        c_panic  = [round(float(r["panic_score"])*100, 1) for r in sampled]
        c_crowd  = [int(r["crowd_count"]) for r in sampled]

        # screenshots
        thumb_html = ""
        for a in alerts:
            shot = os.path.join(screenshot_dir,
                   f"{a.get('gated_state','').replace(' ','_')}_"
                   f"{a.get('timestamp','').replace(' ','_').replace(':','-')}"
                   f"_f{a.get('frame','00000').zfill(5)}.jpg")
        crit_shots = []
        if os.path.exists(screenshot_dir):
            for f in sorted(os.listdir(screenshot_dir)):
                if f.startswith("MASS_PANIC") or f.startswith("PANIC_RISK"):
                    crit_shots.append(os.path.join(screenshot_dir, f))
        for sp in crit_shots[-6:]:
            if os.path.exists(sp):
                with open(sp, "rb") as img_f:
                    b64 = _base64.b64encode(img_f.read()).decode()
                thumb_html += f'''<div class="thumb"><img src="data:image/jpeg;base64,{b64}"/><div class="thumb-label">{os.path.basename(sp)[:22]}</div></div>'''

        alert_rows = ""
        for a in reversed(alerts[-50:]):
            s   = a.get("gated_state","")
            col = {"MASS PANIC":"#ff2d2d","PANIC RISK":"#ff8c00","ALERT":"#ffd400"}.get(s,"#aaa")
            alert_rows += f"<tr><td>{a.get('timestamp','')}</td><td style='color:{col};font-weight:600'>{s}</td><td>{a.get('panic_score','')}</td><td>{a.get('crowd_count','')}</td></tr>"

        def pct(n): return round(n/total_frames*100,1) if total_frames else 0

        report_path = os.path.join(self._log_dir, f"report_{session_ts}.html")
        html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>Crowd Panic Report — {session_ts}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#080b10;color:#c9d1d9;padding:24px}}
h1{{font-size:1.1rem;letter-spacing:.12em;color:#ff2d2d;text-transform:uppercase;margin-bottom:4px}}
h2{{font-size:.7rem;letter-spacing:.1em;color:#4a5568;text-transform:uppercase;margin:28px 0 12px;border-bottom:1px solid #1c2230;padding-bottom:6px}}
.meta{{font-size:.72rem;color:#4a5568;font-family:monospace;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:8px}}
.card{{background:#0d1117;border:1px solid #1c2230;border-radius:6px;padding:14px}}
.card-label{{font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;color:#4a5568;margin-bottom:6px}}
.card-value{{font-size:1.5rem;font-weight:700;font-family:monospace}}
.red{{color:#ff2d2d}}.orange{{color:#ff8c00}}.yellow{{color:#ffd400}}
.green{{color:#00e676}}.cyan{{color:#00e5ff}}.smoke{{color:#a0aec0}}
.chart-wrap{{background:#0d1117;border:1px solid #1c2230;border-radius:6px;padding:16px;margin-bottom:8px}}
canvas{{max-height:220px}}
.risk-bar-wrap{{background:#0d1117;border:1px solid #1c2230;border-radius:6px;padding:16px}}
.risk-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:.72rem}}
.risk-row-label{{width:90px;font-family:monospace}}
.risk-track{{flex:1;background:#1c2230;border-radius:3px;height:8px;overflow:hidden}}
.risk-fill{{height:100%;border-radius:3px}}
.risk-pct{{width:38px;text-align:right;font-family:monospace;color:#4a5568}}
table{{width:100%;border-collapse:collapse;font-size:.72rem;font-family:monospace}}
th{{text-align:left;padding:7px 10px;color:#4a5568;border-bottom:1px solid #1c2230;font-size:.6rem;letter-spacing:.08em;text-transform:uppercase}}
td{{padding:6px 10px;border-bottom:1px solid #0d1117}}
.thumbs{{display:flex;flex-wrap:wrap;gap:10px;margin-top:4px}}
.thumb{{border:1px solid #1c2230;border-radius:4px;overflow:hidden;width:180px}}
.thumb img{{width:100%;display:block}}
.thumb-label{{font-size:.60rem;font-family:monospace;color:#4a5568;padding:4px 6px;background:#0d1117;text-align:center}}
footer{{margin-top:28px;font-size:.62rem;color:#1c2230;font-family:monospace;text-align:center}}
</style></head><body>
<h1>&#9632; Smart Crowd Panic Detection — Session Report</h1>
<div class="meta">Session: {session_ts} &nbsp;|&nbsp; Frames: {total_frames:,} &nbsp;|&nbsp; Dev: Bade Hari Preetham</div>
<h2>Session Overview</h2>
<div class="cards">
<div class="card"><div class="card-label">Total Frames</div><div class="card-value cyan">{total_frames:,}</div></div>
<div class="card"><div class="card-label">Avg FPS</div><div class="card-value cyan">{avg_fps:.1f}</div></div>
<div class="card"><div class="card-label">Total Alerts</div><div class="card-value {'red' if total_alerts else 'green'}">{total_alerts}</div></div>
<div class="card"><div class="card-label">Mass Panic</div><div class="card-value red">{a_mass}</div></div>
<div class="card"><div class="card-label">Panic Risk</div><div class="card-value orange">{a_panic}</div></div>
<div class="card"><div class="card-label">Alert</div><div class="card-value yellow">{a_alert}</div></div>
<div class="card"><div class="card-label">Max Panic</div><div class="card-value red">{max_panic:.0%}</div></div>
<div class="card"><div class="card-label">Avg Panic</div><div class="card-value orange">{avg_panic:.1%}</div></div>
<div class="card"><div class="card-label">Max Crowd</div><div class="card-value yellow">{max_crowd}</div></div>
<div class="card"><div class="card-label">Avg Crowd</div><div class="card-value smoke">{avg_crowd:.1f}</div></div>
</div>
<h2>Panic Score Trend</h2>
<div class="chart-wrap"><canvas id="trendChart"></canvas></div>
<h2>State Distribution</h2>
<div class="risk-bar-wrap">
<div class="risk-row"><span class="risk-row-label green">NORMAL</span><div class="risk-track"><div class="risk-fill" style="width:{pct(state_counts.get('NORMAL',0))}%;background:#00e676"></div></div><span class="risk-pct">{pct(state_counts.get('NORMAL',0))}%</span></div>
<div class="risk-row"><span class="risk-row-label yellow">ALERT</span><div class="risk-track"><div class="risk-fill" style="width:{pct(state_counts.get('ALERT',0))}%;background:#ffd400"></div></div><span class="risk-pct">{pct(state_counts.get('ALERT',0))}%</span></div>
<div class="risk-row"><span class="risk-row-label orange">PANIC RISK</span><div class="risk-track"><div class="risk-fill" style="width:{pct(state_counts.get('PANIC RISK',0))}%;background:#ff8c00"></div></div><span class="risk-pct">{pct(state_counts.get('PANIC RISK',0))}%</span></div>
<div class="risk-row"><span class="risk-row-label red">MASS PANIC</span><div class="risk-track"><div class="risk-fill" style="width:{pct(state_counts.get('MASS PANIC',0))}%;background:#ff2d2d"></div></div><span class="risk-pct">{pct(state_counts.get('MASS PANIC',0))}%</span></div>
</div>
{'<h2>Alert Screenshots</h2><div class="thumbs">'+thumb_html+'</div>' if thumb_html else ''}
<h2>Alert Log (last 50)</h2>
{'<p style="color:#4a5568;font-size:.72rem;font-family:monospace;padding:10px 0">No alerts this session.</p>' if not alerts else f'<table><thead><tr><th>Timestamp</th><th>State</th><th>Panic Score</th><th>Crowd Count</th></tr></thead><tbody>{alert_rows}</tbody></table>'}
<footer>Bade Hari Preetham &nbsp;|&nbsp; Smart Crowd Panic Detection AI &nbsp;|&nbsp; {session_ts}</footer>
<script>
const ctx=document.getElementById('trendChart').getContext('2d');
new Chart(ctx,{{type:'line',data:{{labels:{c_labels},datasets:[{{label:'Panic Score %',data:{c_panic},borderColor:'#ff2d2d',backgroundColor:'rgba(255,45,45,0.05)',borderWidth:1.5,pointRadius:0,tension:0.3,fill:true}},{{label:'Crowd Count',data:{c_crowd},borderColor:'#00e5ff',backgroundColor:'rgba(0,229,255,0.05)',borderWidth:1.5,pointRadius:0,tension:0.3,fill:true,yAxisID:'y2'}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#c9d1d9',font:{{size:11}}}}}},tooltip:{{mode:'index',intersect:false}}}},scales:{{x:{{ticks:{{color:'#4a5568',maxTicksLimit:10,font:{{size:10}}}},grid:{{color:'#1c2230'}}}},y:{{min:0,max:100,ticks:{{color:'#4a5568',font:{{size:10}},callback:v=>v+'%'}},grid:{{color:'#1c2230'}}}},y2:{{position:'right',ticks:{{color:'#00e5ff',font:{{size:10}}}},grid:{{drawOnChartArea:false}}}}}}}}}});
</script></body></html>"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [REPORT] ✅ Report saved: {report_path}")
        return report_path

# ─────────────────────────────────────────────────────────────────────────────
# DETECTION LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class DetectionLogger:
    """Logs every frame to CSV + alert events to a separate CSV."""

    FRAME_FIELDS = ["timestamp", "frame", "panic_score", "panic_state",
                    "gated_state", "crowd_count", "avg_speed", "entropy",
                    "convergence", "spike_ratio", "dir_chaos", "fps"]
    ALERT_FIELDS = ["timestamp", "frame", "gated_state",
                    "panic_score", "crowd_count"]
    ALERT_COOLDOWN = 3

    def __init__(self, log_dir="crowd_logs"):
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(os.path.join(log_dir, "screenshots"), exist_ok=True)
        self.log_dir       = log_dir
        self.screenshot_dir = os.path.join(log_dir, "screenshots")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_ts    = ts

        self._frame_path = os.path.join(log_dir, f"crowd_log_{ts}.csv")
        self._alert_path = os.path.join(log_dir, f"alert_log_{ts}.csv")

        self._ff = open(self._frame_path, "w", newline="")
        self._af = open(self._alert_path, "w", newline="")
        self._fw = _csv.DictWriter(self._ff, fieldnames=self.FRAME_FIELDS)
        self._aw = _csv.DictWriter(self._af, fieldnames=self.ALERT_FIELDS)
        self._fw.writeheader(); self._aw.writeheader()

        self._last_alert_time = 0.0
        self._last_state      = "NORMAL"
        self._total_frames    = 0
        self._max_panic       = 0.0
        self._max_crowd       = 0

        print(f"  [LOG] Frame log  : {self._frame_path}")
        print(f"  [LOG] Alert log  : {self._alert_path}")

    def log(self, frame_idx, panic_score, panic_state, gated_state,
            crowd_count, metrics, fps, canvas=None):
        self._total_frames += 1
        self._max_panic     = max(self._max_panic, panic_score)
        self._max_crowd     = max(self._max_crowd, crowd_count)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._fw.writerow({
            "timestamp":   ts,
            "frame":       frame_idx,
            "panic_score": f"{panic_score:.4f}",
            "panic_state": panic_state,
            "gated_state": gated_state,
            "crowd_count": crowd_count,
            "avg_speed":   f"{metrics.get('avg_speed', 0):.2f}",
            "entropy":     f"{metrics.get('motion_entropy', 0):.4f}",
            "convergence": f"{metrics.get('convergence', 0):.4f}",
            "spike_ratio": f"{metrics.get('spike_ratio', 0):.4f}",
            "dir_chaos":   f"{metrics.get('dir_chaos', 0):.4f}",
            "fps":         f"{fps:.1f}",
        })

        if gated_state not in ("NORMAL",):
            now = _time_mod.time()
            changed = (gated_state != self._last_state)
            cooled  = (now - self._last_alert_time) >= self.ALERT_COOLDOWN
            if changed or cooled:
                self._last_alert_time = now
                self._last_state      = gated_state
                self._aw.writerow({
                    "timestamp":   ts,
                    "frame":       frame_idx,
                    "gated_state": gated_state,
                    "panic_score": f"{panic_score:.2%}",
                    "crowd_count": crowd_count,
                })
                self._af.flush()
                sym = {"ALERT":"⚠","PANIC RISK":"🔶","MASS PANIC":"🔴"}.get(gated_state,"!")
                print(f"\n  [ALERT] {sym} {gated_state} — "
                      f"Panic:{panic_score:.0%}  People:{crowd_count}  Frame:{frame_idx:05d}")

                if canvas is not None:
                    shot = f"{gated_state.replace(' ','_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_f{frame_idx:05d}.jpg"
                    cv2.imwrite(os.path.join(self.screenshot_dir, shot), canvas)
        else:
            self._last_state = "NORMAL"

    def close(self):
        self._ff.flush(); self._af.flush()
        self._ff.close(); self._af.close()
        print(f"\n{'='*44}")
        print(f"  SESSION SUMMARY")
        print(f"{'='*44}")
        print(f"  Frames processed : {self._total_frames}")
        print(f"  Max panic score  : {self._max_panic:.1%}")
        print(f"  Max crowd count  : {self._max_crowd}")
        print(f"  Logs saved in    : {self.log_dir}/")
        print(f"{'='*44}")

# ─────────────────────────────────────────────────────────────────────────────
# HEATMAP ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class HeatmapEngine:
    def __init__(self, h, w):
        self.acc = np.zeros((h, w), dtype=np.float32)
        self.panic_acc = np.zeros((h, w), dtype=np.float32)

    def update(self, tracks, panic_score):
        for t in tracks.values():
            if not t.history: continue
            cx, cy = t.history[-1]
            if 0<=cy<self.acc.shape[0] and 0<=cx<self.acc.shape[1]:
                self.acc[cy, cx]       += 1.0
                self.panic_acc[cy, cx] += panic_score

        self.acc       *= 0.97
        self.panic_acc *= 0.95

    def render(self, frame, alpha=0.40):
        # Base density heatmap (blue-green)
        blurred = gaussian_filter(self.acc, sigma=22)
        mx = blurred.max()
        if mx > 1e-6:
            norm = np.clip(blurred/mx, 0, 1)
            heat8 = (norm*255).astype(np.uint8)
            colored = cv2.applyColorMap(heat8, cv2.COLORMAP_OCEAN)
            mask = (norm > 0.08).astype(np.float32)[:,:,None]
            frame[:] = (frame*(1-mask*alpha) + colored*mask*alpha).clip(0,255).astype(np.uint8)

        # Panic hotspot overlay (red-orange)
        pb = gaussian_filter(self.panic_acc, sigma=16)
        pmx = pb.max()
        if pmx > 1e-6:
            pnorm = np.clip(pb/pmx, 0, 1)
            ph8 = (pnorm*255).astype(np.uint8)
            pc = cv2.applyColorMap(ph8, cv2.COLORMAP_HOT)
            pmask = (pnorm > 0.15).astype(np.float32)[:,:,None]
            frame[:] = (frame*(1-pmask*0.3) + pc*pmask*0.3).clip(0,255).astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# BIRD'S-EYE VIEW PANEL
# ─────────────────────────────────────────────────────────────────────────────

class BirdsEyeView:
    def __init__(self, src_h, src_w):
        self.src_h = src_h
        self.src_w = src_w

    def _person_color(self, t, panic_score):
        if t.avg_speed > SPEED_SPIKE_THRESH:
            return NEON_RED
        if panic_score > 0.60:
            return NEON_ORANGE
        if panic_score > 0.35:
            return NEON_YELLOW
        return NEON_GREEN

    def render(self, tracks, panic_score, crowd_count):
        panel = np.full((BEV_H, BEV_W, 3), PANEL_BG, dtype=np.uint8)

        # Grid
        for y in range(0, BEV_H, 35):
            cv2.line(panel, (0,y), (BEV_W,y), GRID_COLOR, 1)
        for x in range(0, BEV_W, 35):
            cv2.line(panel, (x,0), (x,BEV_H), GRID_COLOR, 1)

        # Crowd dots
        for t in tracks.values():
            if not t.history: continue
            cx, cy = t.history[-1]
            bx = int(cx / self.src_w * BEV_W)
            by = int(cy / self.src_h * BEV_H)
            bx = max(3, min(BEV_W-3, bx))
            by = max(3, min(BEV_H-3, by))
            col = self._person_color(t, panic_score)

            # Glow
            cv2.circle(panel, (bx,by), 9, tuple(c//5 for c in col), -1)
            cv2.circle(panel, (bx,by), 5, col, -1)
            cv2.circle(panel, (bx,by), 2, (255,255,255), -1)

            # Velocity arrow
            if t.vel_history:
                dx, dy, _ = t.vel_history[-1]
                ex = int(bx + dx*2)
                ey = int(by + dy*2)
                cv2.arrowedLine(panel, (bx,by), (ex,ey), col, 1,
                                tipLength=0.4, line_type=cv2.LINE_AA)

        # Panic level ring
        ring_x, ring_y, ring_r = BEV_W//2, BEV_H-36, 18
        ring_col = _panic_color(panic_score)
        cv2.circle(panel, (ring_x,ring_y), ring_r, ring_col, 2)
        filled_angle = int(360 * panic_score)
        if filled_angle > 0:
            cv2.ellipse(panel, (ring_x,ring_y), (ring_r,ring_r),
                        -90, 0, filled_angle, ring_col, -1)
        glow_text(panel, f"{panic_score*100:.0f}%",
                  ring_x-12, ring_y+5, 0.35, (255,255,255))

        cv2.rectangle(panel, (0,0),(BEV_W-1,BEV_H-1), NEON_CYAN, 1)
        glow_text(panel, "CROWD MAP", 6, 14, 0.38, NEON_CYAN)
        glow_text(panel, f"N={crowd_count}", BEV_W-50, 14, 0.38, NEON_YELLOW)
        return panel


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def alpha_rect(frame, x1, y1, x2, y2, color, alpha=0.4):
    h, w = frame.shape[:2]
    x1,y1,x2,y2 = max(0,x1),max(0,y1),min(w,x2),min(h,y2)
    if x2<=x1 or y2<=y1: return
    roi = frame[y1:y2, x1:x2].astype(np.float32)
    roi = roi*(1-alpha) + np.array(color, np.float32)*alpha
    frame[y1:y2, x1:x2] = roi.clip(0,255).astype(np.uint8)

def glow_text(frame, text, x, y, fs=0.45, color=NEON_CYAN, thick=1):
    gc = tuple(int(c*0.35) for c in color)
    cv2.putText(frame, text, (x-1,y+1), cv2.FONT_HERSHEY_SIMPLEX, fs, gc, thick+2, cv2.LINE_AA)
    cv2.putText(frame, text, (x,y),   cv2.FONT_HERSHEY_SIMPLEX, fs, color, thick, cv2.LINE_AA)

def corner_box(frame, x1, y1, x2, y2, color, L=14, T=2):
    for px,py in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:
        dx = L if px==x1 else -L
        dy = L if py==y1 else -L
        cv2.line(frame,(px,py),(px+dx,py), color, T, cv2.LINE_AA)
        cv2.line(frame,(px,py),(px,py+dy), color, T, cv2.LINE_AA)

def draw_trail(frame, history, color):
    pts = list(history)
    for i in range(1, len(pts)):
        a = i/len(pts)
        c = tuple(int(ch*a) for ch in color)
        cv2.line(frame, pts[i-1], pts[i], c, max(1,int(2*a)), cv2.LINE_AA)

def _panic_color(score):
    if score < 0.25: return NEON_GREEN
    if score < 0.50: return NEON_YELLOW
    if score < 0.72: return NEON_ORANGE
    return NEON_RED

def _panic_state_color(state):
    return {
        "NORMAL":    NEON_GREEN,
        "ALERT":     NEON_YELLOW,
        "PANIC RISK":NEON_ORANGE,
        "MASS PANIC":NEON_RED,
    }.get(state, NEON_CYAN)

def _density_color(state):
    return {
        "LOW DENSITY":        NEON_GREEN,
        "MODERATE":           NEON_YELLOW,
        "HIGH DENSITY":       NEON_ORANGE,
        "CRITICAL OVERCROWD": NEON_RED,
    }.get(state, NEON_CYAN)

def _density_state(n):
    if n < DENSITY_MODERATE: return "LOW DENSITY"
    if n < DENSITY_HIGH:     return "MODERATE"
    if n < DENSITY_CRITICAL: return "HIGH DENSITY"
    return "CRITICAL OVERCROWD"


# ─────────────────────────────────────────────────────────────────────────────
# HUD RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def draw_hud(frame, stats, panic_score, panic_state):
    h, w = frame.shape[:2]

    # ── Left panel ──
    pw, ph = 268, 320
    alpha_rect(frame, 0, 0, pw, ph, PANEL_BG, alpha=0.85)
    cv2.rectangle(frame, (0,0),(pw,ph), NEON_CYAN, 1)
    cv2.line(frame, (0,22),(pw,22), NEON_CYAN, 1)
    glow_text(frame, "CROWD PANIC AI  v1.0", 7, 16, 0.46, NEON_PINK)

    rows = [
        ("FPS",         f"{stats['fps']:.1f}",               NEON_GREEN),
        ("LATENCY",     f"{stats['latency']*1000:.1f} ms",   NEON_CYAN),
        ("FRAME",       f"#{stats['frame']}",                NEON_CYAN),
        ("PEOPLE",      str(stats['count']),                  NEON_YELLOW),
        ("TRACKS",      str(stats['tracks']),                 NEON_CYAN),
        ("DENSITY",     stats['density_state'],               _density_color(stats['density_state'])),
        ("AVG SPEED",   f"{stats['avg_speed']:.1f} px/f",   NEON_ORANGE),
        ("ENTROPY",     f"{stats['entropy']:.2f}",           NEON_PURPLE),
        ("CONVERGENCE", f"{stats['convergence']:.2f}",       NEON_BLUE),
        ("PANIC SCORE", f"{panic_score*100:.1f}%",           _panic_color(panic_score)),
        ("PANIC STATE", panic_state,                          _panic_state_color(panic_state)),
        ("MODE",        stats['device'].upper(),              NEON_GREEN),
    ]
    for i, (lbl, val, col) in enumerate(rows):
        y = 36 + i*23
        glow_text(frame, f"{lbl:<12}", 7, y, 0.36, (100,120,140))
        glow_text(frame, val, 120, y, 0.40, col)

    # timestamp
    ts = datetime.datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
    glow_text(frame, ts, 7, ph-7, 0.34, NEON_CYAN)

    # ── Top accent bar ──
    alpha_rect(frame, 0, 0, w, 4, NEON_PINK, alpha=0.95)

    # ── Panic score bar (bottom) ──
    bar_y = h - 30
    alpha_rect(frame, 0, bar_y, w, h, PANEL_BG, alpha=0.75)
    bar_fill = int(w * panic_score)
    pcol = _panic_color(panic_score)
    cv2.rectangle(frame, (0, bar_y+4), (bar_fill, bar_y+14), pcol, -1)
    cv2.rectangle(frame, (0, bar_y+4), (w,        bar_y+14), NEON_CYAN, 1)
    glow_text(frame, f"PANIC INDEX  {panic_score*100:.1f}%",
              8, h-8, 0.42, pcol)
    glow_text(frame, panic_state,
              w//2-60, h-8, 0.50, _panic_state_color(panic_state))
    glow_text(frame, "Dev: Bade Hari Preetham",
          w-210, h-8, 0.30, (50, 80, 80))

    # ── Mass panic emergency flash ──
    fi = stats['frame']
    if panic_state == "MASS PANIC" and (fi//8) % 2 == 0:
        alpha_rect(frame, 0, 0, w, h, (120,0,0), alpha=0.10)
        alpha_rect(frame, w//2-200, 46, w//2+200, 84, (160,0,0), alpha=0.70)
        cv2.rectangle(frame, (w//2-200,46),(w//2+200,84), NEON_RED, 2)
        glow_text(frame, "⚠  MASS PANIC DETECTED — EMERGENCY  ⚠",
                  w//2-192, 74, 0.58, NEON_RED)
    elif panic_state == "PANIC RISK":
        alpha_rect(frame, w//2-170, 46, w//2+170, 78, (80,30,0), alpha=0.60)
        glow_text(frame, "⚠  CROWD PANIC RISK — MONITOR NOW",
                  w//2-162, 70, 0.50, NEON_ORANGE)
    elif panic_state == "ALERT":
        alpha_rect(frame, w//2-130, 46, w//2+130, 74, (50,40,0), alpha=0.55)
        glow_text(frame, "CROWD ALERT — ELEVATED MOTION",
                  w//2-122, 68, 0.46, NEON_YELLOW)

    # ── Convergence warning (stampede) ──
    if stats['convergence'] > CONVERGENCE_THRESH:
        glow_text(frame, "▲ STAMPEDE FLOW DETECTED",
                  w-240, h-50, 0.44, NEON_RED)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class CrowdPanicSystem:
    def __init__(self, source, model_path="yolov8n.pt"):
        self.source = source

        self.device  = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_fp16 = self.device == "cuda"
        print(f"  [DEVICE] {self.device.upper()}" + (" | FP16" if self.use_fp16 else ""))

        print("  [MODEL] Loading YOLOv8n...")
        self.model = YOLO(model_path)
        if self.use_fp16:
            self.model.model.half()

        src = int(source) if source.isdigit() else source
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open: {source}")

        self.W  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.H  = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.src_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30

        # Sub-systems
        self.tracker     = IoUTracker()
        self.flow_engine = OpticalFlowEngine()
        self.heatmap     = HeatmapEngine(self.H, self.W)
        self.panic_det   = PanicDetector()
        self.bev         = BirdsEyeView(self.H, self.W)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(OUTPUT_FILE, fourcc, self.src_fps,
                                       (self.W, self.H))

        self.frame_idx    = 0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.fps_buf      = collections.deque([self.src_fps]*8, maxlen=8)
        self.paused       = False
        self._last_frame  = None
        self._start_time  = None

        # ── Speed optimisation ──
        self.INFER_EVERY      = 2       # YOLO every N frames
        self.INFER_SIZE       = 416     # smaller inference res
        self.HEATMAP_EVERY    = 4       # heatmap gaussian every N frames
        self.FLOW_EVERY       = 2       # optical flow every N frames
        self._last_bboxes     = []
        self._cached_bev      = None
        self._cached_heat     = None
        self._scanline_mask   = None
        _empty_metrics = dict(avg_speed=0.0, motion_entropy=0.0, convergence=0.0,
                              spike_ratio=0.0, dir_chaos=0.0, density_pressure=0.0)
        self._last_panic      = (0.0, "NORMAL", _empty_metrics)
        self._last_metrics    = _empty_metrics
        self.alert_gate = SustainedAlertGate(sustain_sec=3.0)
        self.sound_alarmer = SoundAlarmer()
        self.det_logger       = DetectionLogger(log_dir="crowd_logs")
        self.email_alerter    = EmailAlerter()
        self.report_generator = SessionReportGenerator(log_dir="crowd_logs")

        # Start web dashboard
        dash = _threading.Thread(target=_start_dashboard, args=(5001,), daemon=True)
        dash.start()
        print("  [DASHBOARD] Running at http://localhost:5001")

    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        print(f"\n  [GO] Source: {self.source}")
        print(f"  [OUT] → {OUTPUT_FILE}")
        print("  [CTRL] Q=Quit  P=Pause  S=Screenshot\n")

        cv2.namedWindow("Crowd Panic AI", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Crowd Panic AI", min(1280,self.W), min(720,self.H))

        self._start_time = time.time()
        total = self.total_frames

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            if key == ord('p'): self.paused = not self.paused
            if key == ord('s') and self._last_frame is not None:
                fn = f"screenshot_{self.frame_idx}.png"
                cv2.imwrite(fn, self._last_frame)
                print(f"\n  [SAVE] {fn}")

            if self.paused:
                time.sleep(0.03)
                continue

            t0 = time.time()
            ret, frame = self.cap.read()
            if not ret: break

            self.frame_idx += 1
            out = self._process(frame, t0)
            self._last_frame = out.copy()
            self.writer.write(out)
            cv2.imshow("Crowd Panic AI", out)

            # ── Terminal progress bar ──
            fps_now = float(np.mean(self.fps_buf))
            elapsed = time.time() - self._start_time
            if total > 0:
                pct   = self.frame_idx / total * 100
                eta_s = (total - self.frame_idx) / max(fps_now, 0.1)
                eta_m, eta_s2 = divmod(int(eta_s), 60)
                bar_filled = int(pct / 5)
                bar = "█" * bar_filled + "░" * (20 - bar_filled)
                line = (f"\r  [PROCESSING]  [{bar}]  "
                        f"{pct:5.1f}%  |  "
                        f"Frame {self.frame_idx}/{total}  |  "
                        f"{fps_now:.1f} FPS  |  "
                        f"ETA {eta_m}m {eta_s2:02d}s   ")
            else:
                line = (f"\r  [PROCESSING]  Frame {self.frame_idx}  |  "
                        f"{fps_now:.1f} FPS  |  "
                        f"Elapsed {int(elapsed)}s   ")
            sys.stdout.write(line)
            sys.stdout.flush()

        self.cap.release()
        self.writer.release()
        cv2.destroyAllWindows()
        self.sound_alarmer.close()
        self.det_logger.close()
        self.sound_alarmer.close()
        self.report_generator.generate(
            frame_csv_path = self.det_logger._frame_path,
            alert_csv_path = self.det_logger._alert_path,
            screenshot_dir = self.det_logger.screenshot_dir,
            session_ts     = self.det_logger.session_ts,
        )
        print(f"\n\n  [DONE] Saved → {OUTPUT_FILE}")

    # ─────────────────────────────────────────────────────────────────────────
    def _process(self, frame, t0):
        do_infer   = (self.frame_idx % self.INFER_EVERY   == 0)
        do_heatmap = (self.frame_idx % self.HEATMAP_EVERY == 0)
        do_bev     = (self.frame_idx % 3 == 0)
        do_flow    = (self.frame_idx % self.FLOW_EVERY    == 0)

        # ── Optical flow (every 2 frames) ──
        if do_flow:
            self.flow_engine.update(frame)

        # ── YOLO (every 2 frames, on downscaled image) ──
        if do_infer:
            small = cv2.resize(frame, (self.INFER_SIZE, self.INFER_SIZE))
            results = self.model(small, verbose=False, device=self.device,
                                  half=self.use_fp16, conf=0.30, iou=0.45,
                                  classes=[PERSON_CLASS])
            sx = self.W / self.INFER_SIZE
            sy = self.H / self.INFER_SIZE
            bboxes = []
            for r in results:
                if r.boxes is None: continue
                for box in r.boxes:
                    x1,y1,x2,y2 = box.xyxy[0].tolist()
                    bboxes.append((int(x1*sx),int(y1*sy),int(x2*sx),int(y2*sy)))
            self._last_bboxes = bboxes
        else:
            bboxes = self._last_bboxes

        # ── Track ──
        tracks      = self.tracker.update(bboxes)
        crowd_count = len(tracks)

        # ── Panic analysis (every 2 frames) ──
        if do_infer:
            panic_state, panic_score, metrics = self.panic_det.analyze(
                tracks, self.flow_engine, crowd_count)
            self._last_panic   = (panic_score, panic_state, metrics)
            self._last_metrics = metrics
        else:
            panic_score, panic_state, metrics = self._last_panic
        gated_state = self.alert_gate.update(panic_state)
        self.sound_alarmer.notify(gated_state)

        # Push to dashboard
        _push_jpeg(frame)
        _update_shared(
            panic_score   = panic_score,
            panic_state   = panic_state,
            gated_state   = gated_state,
            crowd_count   = crowd_count,
            fps           = float(np.mean(self.fps_buf)),
            frame_idx     = self.frame_idx,
            avg_speed     = metrics.get("avg_speed", 0.0),
            entropy       = metrics.get("motion_entropy", 0.0),
            convergence   = metrics.get("convergence", 0.0),
            spike_ratio   = metrics.get("spike_ratio", 0.0),
            dir_chaos     = metrics.get("dir_chaos", 0.0),
            density_state = _density_state(crowd_count),
        )
        if gated_state != "NORMAL":
            with _state_lock:
                _shared["alert_log"].append({
                    "time":  datetime.datetime.now().strftime("%H:%M:%S"),
                    "state": gated_state,
                    "score": f"{panic_score:.0%}",
                    "count": crowd_count,
                })
                if len(_shared["alert_log"]) > 200:
                    _shared["alert_log"] = _shared["alert_log"][-200:]
        self.det_logger.log(
            frame_idx   = self.frame_idx,
            panic_score = panic_score,
            panic_state = panic_state,
            gated_state = gated_state,
            crowd_count = crowd_count,
            metrics     = metrics,
            fps         = float(np.mean(self.fps_buf)),
            canvas      = frame,
        )
        # ── Email alert ───────────────────────────────────────────────────────
        shot_name = (
            f"{gated_state.replace(' ','_')}_"
            f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f"_f{self.frame_idx:05d}.jpg"
        )
        shot_path = os.path.join("crowd_logs", "screenshots", shot_name)
        self.email_alerter.notify(
            state          = gated_state,
            panic_score    = panic_score,
            crowd_count    = crowd_count,
            frame_idx      = self.frame_idx,
            screenshot_path= shot_path if os.path.exists(shot_path) else None,
        )
        # ── Heatmap ──
        self.heatmap.update(tracks, panic_score)
        if do_heatmap:
            heat_copy = frame.copy()
            self.heatmap.render(heat_copy)
            self._cached_heat = heat_copy
        if self._cached_heat is not None:
            np.copyto(frame, self._cached_heat)

        # ── Optical flow overlay (every 2 frames) ──
        if do_flow:
            self.flow_engine.render_flow(frame, step=24)

        # ── Draw people ──
        self._draw_tracks(frame, tracks, panic_score)

        # ── BEV (every 3 frames) ──
        if do_bev or self._cached_bev is None:
            self._cached_bev = self.bev.render(tracks, panic_score, crowd_count)

        # ── Timing ──
        latency = time.time() - t0
        fps_now = 1.0 / max(latency, 1e-6)
        self.fps_buf.append(fps_now)
        fps = float(np.mean(self.fps_buf))

        density_state = _density_state(crowd_count)
        stats = dict(
            fps=fps, latency=latency, frame=self.frame_idx,
            count=crowd_count, tracks=len(tracks),
            density_state=density_state,
            avg_speed=metrics['avg_speed'],
            entropy=metrics['motion_entropy'],
            convergence=metrics['convergence'],
            device=self.device,
        )

        draw_hud(frame, stats, panic_score, panic_state)

        # ── Embed BEV (bottom-right) ──
        bx = self.W - BEV_W - 8
        by = self.H - BEV_H - 36
        if by > 0 and bx > 0:
            frame[by:by+BEV_H, bx:bx+BEV_W] = self._cached_bev

        # ── Scanlines (pre-built, zero alloc) ──
        if self._scanline_mask is None:
            self._scanline_mask = np.zeros((self.H, self.W, 3), dtype=np.uint8)
            self._scanline_mask[::3, :] = 8
        cv2.subtract(frame, self._scanline_mask, frame)

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_tracks(self, frame, tracks, panic_score):
        for t in tracks.values():
            spd = t.avg_speed
            if spd > SPEED_SPIKE_THRESH:
                color = NEON_RED
            elif panic_score > 0.60:
                color = NEON_ORANGE
            elif panic_score > 0.35:
                color = NEON_YELLOW
            else:
                color = NEON_GREEN

            draw_trail(frame, list(t.history), color)

            x1,y1,x2,y2 = t.bbox
            corner_box(frame, x1,y1,x2,y2, color, L=12, T=2)
            alpha_rect(frame, x1,y1,x2,y2, color, alpha=0.05)

            lbl = f"#{t.id}  {spd:.1f}px/f"
            (tw,th),_ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
            alpha_rect(frame, x1, y1-th-8, x1+tw+8, y1, PANEL_BG, alpha=0.80)
            glow_text(frame, lbl, x1+4, y1-5, 0.36, color)

            # Direction arrow from center
            if t.vel_history:
                dx, dy, _ = t.vel_history[-1]
                cx = (x1+x2)//2; cy_c = (y1+y2)//2
                ex = int(cx + dx*3); ey = int(cy_c + dy*3)
                cv2.arrowedLine(frame, (cx,cy_c), (ex,ey), color, 1,
                                tipLength=0.35, line_type=cv2.LINE_AA)

            # Panic ring on high-speed individuals
            if spd > SPEED_SPIKE_THRESH:
                cx = (x1+x2)//2; cy_c = (y1+y2)//2
                r  = max(30, (y2-y1)//2 + 12)
                cv2.circle(frame, (cx,cy_c), r, NEON_RED, 1, cv2.LINE_AA)
                glow_text(frame, "PANIC", cx-20, y2+14, 0.34, NEON_RED)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart Crowd Panic Detection AI")
    parser.add_argument("source", nargs="?", default="0",
                        help="Video file, camera index, or RTSP URL")
    args = parser.parse_args()

    print(f"\n  [SYSTEM] Crowd Panic AI starting...")
    print(f"  [SOURCE] {args.source}\n")

    system = CrowdPanicSystem(args.source)
    system.run()


if __name__ == "__main__":
    main()