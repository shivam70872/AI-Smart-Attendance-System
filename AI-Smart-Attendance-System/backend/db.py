"""MySQL helper. Credentials come from environment variables (.env), never from code."""
import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "face_attendance_db"),
    )


@contextmanager
def cursor(commit=False):
    """Open a connection, yield a dict cursor, always close both."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        yield cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()
