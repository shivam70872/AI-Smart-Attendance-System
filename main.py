
import cv2
import numpy as np
import face_recognition
import os

from datetime import datetime

import mysql.connector
from mysql.connector import Error


# ================================================
# DATABASE CONFIG
# ================================================

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'shivam123',
    'database': 'face_attendance_db'
}


# ================================================
# DATABASE CONNECTION
# ================================================


def create_db_connection():

    try:

        conn = mysql.connector.connect(**DB_CONFIG)

        if conn.is_connected():
            return conn

    except Error as e:

        print("Database Error:", e)

        return None


# ================================================
# LOAD IMAGES
# ================================================

images = []
classNames = []
encodeListKnown = []

base_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base_dir, "ImagesAttendance")

if not os.path.exists(path):

    print("ImagesAttendance folder not found")

else:

    myList = os.listdir(path)

    for cl in myList:

        img_path = os.path.join(path, cl)

        curImg = cv2.imread(img_path)

        if curImg is not None:

            images.append(curImg)

            classNames.append(
                os.path.splitext(cl)[0].upper()
            )


# ================================================
# ENCODINGS
# ================================================


def findEncodings(images_list):

    encodeList = []

    for img in images_list:

        img_rgb = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )

        encodes = face_recognition.face_encodings(img_rgb)

        if encodes:
            encodeList.append(encodes[0])

    return encodeList


encodeListKnown = findEncodings(images)

print("System Ready")


# ================================================
# ATTENDANCE LOGIC
# ================================================


def log_attendance(
    name,
    status_to_log,
    teacher_name,
    teacher_class
):

    now = datetime.now()

    conn = create_db_connection()

    if conn is None:
        return False

    cursor = conn.cursor(dictionary=True)

    dtString = now.strftime('%Y-%m-%d %H:%M:%S')

    today_date = now.strftime('%Y-%m-%d')

    try:

        # ==========================================
        # GET STUDENT DETAILS
        # ==========================================

        cursor.execute(
            """
            SELECT * FROM students
            WHERE UPPER(student_name)=%s
            """,
            (name,)
        )

        student = cursor.fetchone()

        if not student:
            return False

        # ==========================================
        # VALIDATE CLASS
        # ==========================================

        if student['class_name'] != teacher_class:
            return False

        roll_no = student['roll_no']

        class_name = student['class_name']

        # ==========================================
        # GET LAST STATUS
        # ==========================================

        cursor.execute(
            """
            SELECT status
            FROM attendance
            WHERE roll_no=%s
            AND DATE(timestamp)=%s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (roll_no, today_date)
        )

        result = cursor.fetchone()

        last_status = result['status'] if result else None

        # ==========================================
        # CHECK-IN LOGIC
        # ==========================================

        if status_to_log == "CHECK-IN":

            if last_status == "CHECK-IN":
                return False

        # ==========================================
        # CHECK-OUT LOGIC
        # ==========================================

        elif status_to_log == "CHECK-OUT":

            if last_status is None:
                return False

            if last_status == "CHECK-OUT":
                return False

        # ==========================================
        # INSERT ATTENDANCE
        # ==========================================

        cursor.execute(
            """
            INSERT INTO attendance
            (
                roll_no,
                name,
                class_name,
                teacher_name,
                status,
                timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                roll_no,
                name,
                class_name,
                teacher_name,
                status_to_log,
                dtString
            )
        )

        conn.commit()

        print(f"{name} -> {status_to_log}")

        return True

    except Exception as e:

        print("Attendance Error:", e)

        return False

    finally:

        cursor.close()
        conn.close()


# ================================================
# FACE RECOGNITION
# ================================================


def recognize_faces(
    frame,
    current_mode,
    teacher_name,
    teacher_class
):

    small_frame = cv2.resize(
        frame,
        (0, 0),
        None,
        0.25,
        0.25
    )

    rgb_small_frame = cv2.cvtColor(
        small_frame,
        cv2.COLOR_BGR2RGB
    )

    facesCurFrame = face_recognition.face_locations(
        rgb_small_frame
    )

    encodesCurFrame = face_recognition.face_encodings(
        rgb_small_frame,
        facesCurFrame
    )

    detected_name = "UNKNOWN"
    confidence = 0

    cv2.putText(
        frame,
        f"MODE: {current_mode}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 255),
        2
    )

    for encodeFace, faceLoc in zip(
        encodesCurFrame,
        facesCurFrame
    ):

        matches = face_recognition.compare_faces(
            encodeListKnown,
            encodeFace
        )

        faceDis = face_recognition.face_distance(
            encodeListKnown,
            encodeFace
        )

        matchIndex = np.argmin(faceDis)

        y1, x2, y2, x1 = faceLoc

        y1, x2, y2, x1 = (
            y1 * 4,
            x2 * 4,
            y2 * 4,
            x1 * 4
        )

        if matches[matchIndex]:

            name = classNames[matchIndex]

            confidence = round(
                (1 - faceDis[matchIndex]) * 100,
                2
            )

            detected_name = name

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.rectangle(
                frame,
                (x1, y2 - 35),
                (x2, y2),
                (0, 255, 0),
                cv2.FILLED
            )

            cv2.putText(
                frame,
                f"{name} {confidence}%",
                (x1 + 6, y2 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            attendance_logged = log_attendance(
                name,
                current_mode,
                teacher_name,
                teacher_class
            )

            if attendance_logged:

                cv2.putText(
                    frame,
                    f"{current_mode} SUCCESS",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

        else:

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                "UNKNOWN",
                (x1 + 6, y2 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

    return frame, detected_name, confidence

