"""Create or update a teacher account:
   python seed.py --username asha --password 'choose-a-password' --name "Asha Verma" --class "CSE-A" --department "Computer Science"
"""
import argparse

from werkzeug.security import generate_password_hash

from db import cursor

p = argparse.ArgumentParser()
p.add_argument("--username", required=True)
p.add_argument("--password", required=True)
p.add_argument("--name", required=True)
p.add_argument("--class", dest="class_name", required=True)
p.add_argument("--department", required=True)
a = p.parse_args()

with cursor(commit=True) as cur:
    cur.execute(
        "INSERT INTO teachers (username, password_hash, teacher_name, class_name, department) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), teacher_name=VALUES(teacher_name), "
        "class_name=VALUES(class_name), department=VALUES(department)",
        (a.username, generate_password_hash(a.password), a.name, a.class_name, a.department),
    )
print(f"Teacher '{a.username}' saved for class {a.class_name}.")
