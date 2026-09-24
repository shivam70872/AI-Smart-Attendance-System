CREATE DATABASE IF NOT EXISTS face_attendance_db;
USE face_attendance_db;

CREATE TABLE IF NOT EXISTS teachers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  teacher_name VARCHAR(100) NOT NULL,
  class_name VARCHAR(50) NOT NULL,
  department VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
  id INT AUTO_INCREMENT PRIMARY KEY,
  roll_no VARCHAR(30) NOT NULL,
  student_name VARCHAR(100) NOT NULL,
  class_name VARCHAR(50) NOT NULL,
  photo_path VARCHAR(255),
  UNIQUE KEY uq_class_roll (class_name, roll_no)
);

CREATE TABLE IF NOT EXISTS attendance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  roll_no VARCHAR(30) NOT NULL,
  name VARCHAR(100) NOT NULL,
  class_name VARCHAR(50) NOT NULL,
  teacher_name VARCHAR(100) NOT NULL,
  status ENUM('CHECK-IN','CHECK-OUT') NOT NULL,
  timestamp DATETIME NOT NULL,
  INDEX idx_day (class_name, timestamp),
  INDEX idx_student_day (roll_no, class_name, timestamp)
);
