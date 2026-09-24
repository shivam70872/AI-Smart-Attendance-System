"""Face encoding and matching. Known faces are cached per class and reloaded on demand."""
import os
import threading

import face_recognition
import numpy as np
import cv2

from db import cursor

PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_photos")
TOLERANCE = float(os.getenv("FACE_TOLERANCE", "0.5"))  # lower = stricter (library default is 0.6)
MAX_WIDTH = 640

_cache = {}
_lock = threading.Lock()


def _load_known(class_name):
    with cursor() as cur:
        cur.execute(
            "SELECT roll_no, student_name, photo_path FROM students WHERE class_name=%s",
            (class_name,),
        )
        rows = cur.fetchall()
    rolls, names, encodings = [], [], []
    for row in rows:
        path = os.path.join(PHOTO_DIR, row["photo_path"] or "")
        if not os.path.isfile(path):
            continue
        found = face_recognition.face_encodings(face_recognition.load_image_file(path))
        if found:
            rolls.append(row["roll_no"])
            names.append(row["student_name"])
            encodings.append(found[0])
    return rolls, names, np.array(encodings)


def get_known(class_name):
    with _lock:
        if class_name not in _cache:
            _cache[class_name] = _load_known(class_name)
        return _cache[class_name]


def invalidate(class_name):
    with _lock:
        _cache.pop(class_name, None)


def recognize(class_name, frame_bgr):
    """Return one dict per detected face: normalised box + matched student (or None)."""
    rolls, names, known = get_known(class_name)

    h, w = frame_bgr.shape[:2]
    if w > MAX_WIDTH:
        scale = MAX_WIDTH / w
        frame_bgr = cv2.resize(frame_bgr, (MAX_WIDTH, int(h * scale)))
    sh, sw = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)

    faces = []
    for (top, right, bottom, left), enc in zip(locations, encodings):
        face = {
            "box": {"x": left / sw, "y": top / sh, "w": (right - left) / sw, "h": (bottom - top) / sh},
            "roll_no": None,
            "name": None,
            "confidence": None,
        }
        if len(known):  # guards against an empty class (the old code crashed here)
            distances = face_recognition.face_distance(known, enc)
            best = int(np.argmin(distances))
            if distances[best] <= TOLERANCE:
                face["roll_no"] = rolls[best]
                face["name"] = names[best]
                face["confidence"] = round((1 - float(distances[best])) * 100, 1)
        faces.append(face)
    return faces
