# AI Smart Attendance System

A web app that marks class attendance by face recognition. Teachers log in, point a webcam at students, and check-ins and check-outs are saved to MySQL. Records can be filtered by date and exported to Excel.

**Frontend:** HTML, CSS, JavaScript (`frontend/`), which uses the browser webcam.
**Backend:** Python, Flask, `face_recognition` (dlib), OpenCV, MySQL (`backend/`).
Both live in this one repository. Flask serves the frontend, so there is a single server to run.

## How it works

1. The browser captures a webcam frame every 1.5 seconds and sends it to `POST /api/recognize`.
2. The backend detects faces, compares each one against the registered photos of the logged-in teacher's class (strict tolerance 0.5), and applies the check-in / check-out rules.
3. The browser draws boxes around faces and updates the records table.

Rules: a student can't check in twice in a row, and can only check out after checking in.

## Setup

Requirements: Python 3.10+, MySQL 8, a webcam. Installing `dlib` needs CMake (`pip install cmake`) and a C++ compiler.

```bash
git clone https://github.com/shivam70872/AI-Smart-Attendance-System.git
cd AI-Smart-Attendance-System/backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

mysql -u root -p < schema.sql
cp .env.example .env                                  # then edit .env with your DB password and a random SECRET_KEY
python seed.py --username asha --password "choose-a-password" --name "Asha Verma" --class "CSE-A" --department "Computer Science"
python app.py
```

Open http://localhost:5000, log in, click **Add a student** (roll number, name, one clear face photo), then face the camera.
The camera only works on `localhost` or HTTPS.

## API

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/login`, `/api/logout` | Session login (hashed passwords) |
| GET | `/api/me` | Current teacher |
| GET / POST | `/api/students` | List / register a student with a photo |
| POST | `/api/recognize` | Recognise faces in a frame and log attendance |
| GET | `/api/attendance?date=YYYY-MM-DD` | Records and counts for a day |
| GET | `/api/export?date=YYYY-MM-DD` | Excel report |

## Security notes

- Credentials live in `.env` (git-ignored), never in code.
- Teacher passwords are hashed; all SQL is parameterised; the UI renders names with `textContent`.
- Student photos are git-ignored so no faces are published.
- Known limitation: no liveness detection, so a printed photo could fool it.

## Project structure

```
backend/   app.py  face_service.py  db.py  seed.py  schema.sql  requirements.txt  .env.example
frontend/  index.html  style.css  app.js
```
