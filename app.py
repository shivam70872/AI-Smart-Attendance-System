
import base64
import io
import os
import re
from datetime import date, datetime
from functools import wraps

import cv2
import face_recognition
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

import face_service as fs  
from db import cursor  

BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.abspath(os.path.join(BASE, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY") or os.urandom(24),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

ALLOWED_EXT = {".jpg", ".jpeg", ".png"}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "teacher" not in session:
            return jsonify(error="Please log in first."), 401
        return fn(*args, **kwargs)

    return wrapper


def day_from_query():
    try:
        return datetime.strptime(request.args.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def decode_image(data_url):
    try:
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        arr = np.frombuffer(base64.b64decode(b64), np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def log_attendance(teacher, roll_no, name, mode):
    """Insert a CHECK-IN / CHECK-OUT row if the day's sequence allows it."""
    now = datetime.now()
    with cursor(commit=True) as cur:
        cur.execute(
            "SELECT status FROM attendance WHERE roll_no=%s AND class_name=%s AND DATE(timestamp)=%s "
            "ORDER BY timestamp DESC, id DESC LIMIT 1",
            (roll_no, teacher["class_name"], now.date()),
        )
        row = cur.fetchone()
        last = row["status"] if row else None
        if mode == "CHECK-IN" and last == "CHECK-IN":
            return False, "Already checked in"
        if mode == "CHECK-OUT" and last != "CHECK-IN":
            return False, "Not checked in yet"
        cur.execute(
            "INSERT INTO attendance (roll_no, name, class_name, teacher_name, status, timestamp) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (roll_no, name, teacher["class_name"], teacher["name"], mode, now),
        )
    return True, "Checked in" if mode == "CHECK-IN" else "Checked out"


# ---------------------------------------------------------------- pages
@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


# ---------------------------------------------------------------- auth
@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    with cursor() as cur:
        cur.execute("SELECT * FROM teachers WHERE username=%s", (username,))
        teacher = cur.fetchone()
    if not teacher or not check_password_hash(teacher["password_hash"], password):
        return jsonify(error="Wrong username or password."), 401
    session["teacher"] = {
        "username": teacher["username"],
        "name": teacher["teacher_name"],
        "class_name": teacher["class_name"],
        "department": teacher["department"],
    }
    return jsonify(teacher=session["teacher"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    return jsonify(teacher=session.get("teacher"))


# ---------------------------------------------------------------- students
@app.get("/api/students")
@login_required
def list_students():
    with cursor() as cur:
        cur.execute(
            "SELECT roll_no, student_name FROM students WHERE class_name=%s ORDER BY roll_no",
            (session["teacher"]["class_name"],),
        )
        return jsonify(students=cur.fetchall())


@app.post("/api/students")
@login_required
def add_student():
    class_name = session["teacher"]["class_name"]
    roll_no = (request.form.get("roll_no") or "").strip()
    name = (request.form.get("name") or "").strip()
    photo = request.files.get("photo")

    if not roll_no or not name or not photo:
        return jsonify(error="Roll number, name and a photo are all required."), 400
    ext = os.path.splitext(photo.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error="Photo must be a JPG or PNG file."), 400

    filename = secure_filename(f"{class_name}_{roll_no}{ext}")
    path = os.path.join(fs.PHOTO_DIR, filename)
    photo.save(path)

    def reject(message, code):
        if os.path.isfile(path):
            os.remove(path)
        return jsonify(error=message), code

    faces = face_recognition.face_locations(face_recognition.load_image_file(path))
    if len(faces) != 1:
        return reject(f"The photo must show exactly one face (found {len(faces)}).", 400)

    try:
        with cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO students (roll_no, student_name, class_name, photo_path) VALUES (%s, %s, %s, %s)",
                (roll_no, name, class_name, filename),
            )
    except IntegrityError:
        return reject("That roll number is already registered in this class.", 409)

    fs.invalidate(class_name)
    return jsonify(ok=True), 201


# ---------------------------------------------------------------- recognition
@app.post("/api/recognize")
@login_required
def recognize():
    teacher = session["teacher"]
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    if mode not in ("CHECK-IN", "CHECK-OUT"):
        return jsonify(error="Mode must be CHECK-IN or CHECK-OUT."), 400
    frame = decode_image(data.get("image") or "")
    if frame is None:
        return jsonify(error="Could not read the camera frame."), 400

    faces = fs.recognize(teacher["class_name"], frame)
    for face in faces:
        if face["roll_no"]:
            face["logged"], face["message"] = log_attendance(teacher, face["roll_no"], face["name"], mode)
        else:
            face["logged"], face["message"] = False, "Not recognised in this class"
    return jsonify(faces=faces)


# ---------------------------------------------------------------- records
def fetch_records(class_name, day):
    with cursor() as cur:
        cur.execute(
            "SELECT roll_no, name, status, timestamp FROM attendance "
            "WHERE class_name=%s AND DATE(timestamp)=%s ORDER BY timestamp DESC, id DESC",
            (class_name, day),
        )
        return cur.fetchall()


@app.get("/api/attendance")
@login_required
def attendance():
    class_name = session["teacher"]["class_name"]
    day = day_from_query()
    rows = fetch_records(class_name, day)
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM students WHERE class_name=%s", (class_name,))
        total = cur.fetchone()["n"]
    present = len({r["roll_no"] for r in rows if r["status"] == "CHECK-IN"})
    records = [
        {"roll_no": r["roll_no"], "name": r["name"], "status": r["status"], "time": r["timestamp"].strftime("%H:%M:%S")}
        for r in rows
    ]
    return jsonify(records=records, total_students=total, present=present, date=day.isoformat())


@app.get("/api/export")
@login_required
def export():
    teacher = session["teacher"]
    day = day_from_query()
    rows = fetch_records(teacher["class_name"], day)
    if not rows:
        return jsonify(error="No attendance records for that date."), 404
    df = pd.DataFrame(rows)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.insert(2, "class_name", teacher["class_name"])
    df.insert(3, "teacher_name", teacher["name"])
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    safe_class = re.sub(r"[^A-Za-z0-9_-]", "_", teacher["class_name"])
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{safe_class}_Attendance_{day.isoformat()}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File is too large (6 MB max)."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
