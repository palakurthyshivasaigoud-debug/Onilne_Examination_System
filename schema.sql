-- Online Examination System - MySQL Schema
-- Run this in phpMyAdmin or MySQL CLI

CREATE DATABASE IF NOT EXISTS exam_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE exam_system;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role ENUM('admin', 'student') DEFAULT 'student' NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Questions Table
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    option_a VARCHAR(300) NOT NULL,
    option_b VARCHAR(300) NOT NULL,
    option_c VARCHAR(300) NOT NULL,
    option_d VARCHAR(300) NOT NULL,
    correct_answer ENUM('A', 'B', 'C', 'D') NOT NULL,
    marks INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Exams Table
CREATE TABLE IF NOT EXISTS exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    duration_minutes INT DEFAULT 30,
    total_questions INT DEFAULT 10,
    created_by INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Results Table
CREATE TABLE IF NOT EXISTS results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    exam_id INT NOT NULL,
    score INT DEFAULT 0,
    total_marks INT DEFAULT 0,
    percentage FLOAT DEFAULT 0.0,
    answers TEXT,
    questions TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    submitted_at DATETIME,
    is_disqualified BOOLEAN DEFAULT FALSE,
    disqualify_reason VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

-- Proctoring Logs Table
CREATE TABLE IF NOT EXISTS proctoring_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    result_id INT NOT NULL,
    event_type VARCHAR(50),
    message VARCHAR(200),
    screenshot_path VARCHAR(300),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES results(id)
);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Default Admin (password: Admin@123)
INSERT INTO users (name, email, password_hash, role) VALUES
('Administrator', 'admin@exam.com', 'scrypt:32768:8:1$kWhJLaTtMBcJFYSk$c93f15b4aff62bd3c1f5bd4c76bc7c8d4e9ecbf7c8bb5b3c5c8e9e9ebcbe1c2eb3f3cd8c8e3b3e3d8c3d8c3d8c3d8c3d8c3d8c3d8c3d8c3', 'admin');

-- Sample Students (password: Student@123)
INSERT INTO users (name, email, password_hash, role) VALUES
('Alice Johnson', 'alice@student.com', 'scrypt:32768:8:1$kWhJLaTtMBcJFYSk$c93f15b4aff62bd3c1f5bd4c76bc7c8d4e9ecbf7c8bb5b3c5c8e9e9ebcbe1c2eb3f3cd8c8e3b3e3d8c3d8c3d8c3d8c3d8c3d8c3d8c3d8c3', 'student'),
('Bob Smith', 'bob@student.com', 'scrypt:32768:8:1$kWhJLaTtMBcJFYSk$c93f15b4aff62bd3c1f5bd4c76bc7c8d4e9ecbf7c8bb5b3c5c8e9e9ebcbe1c2eb3f3cd8c8e3b3e3d8c3d8c3d8c3d8c3d8c3d8c3d8c3d8c3', 'student');

-- Sample Questions - Computer Science
INSERT INTO questions (subject, question_text, option_a, option_b, option_c, option_d, correct_answer, marks) VALUES
('Computer Science', 'What does CPU stand for?', 'Central Processing Unit', 'Computer Personal Unit', 'Central Processor Utility', 'Core Processing Unit', 'A', 1),
('Computer Science', 'Which data structure uses LIFO principle?', 'Queue', 'Stack', 'Array', 'Linked List', 'B', 1),
('Computer Science', 'What is the time complexity of Binary Search?', 'O(n)', 'O(n²)', 'O(log n)', 'O(1)', 'C', 1),
('Computer Science', 'Which language is primarily used for web styling?', 'JavaScript', 'Python', 'CSS', 'HTML', 'C', 1),
('Computer Science', 'What does HTML stand for?', 'Hyper Text Markup Language', 'High Text Machine Level', 'Hyper Transfer Markup Logic', 'Home Tool Markup Language', 'A', 1),
('Computer Science', 'Which operator is used for integer division in Python?', '/', '//', '%', '**', 'B', 1),
('Computer Science', 'What is RAM?', 'Read Access Memory', 'Random Access Memory', 'Rapid Array Memory', 'Run-time Access Module', 'B', 1),
('Computer Science', 'Which of the following is an OOP concept?', 'Recursion', 'Compilation', 'Inheritance', 'Looping', 'C', 1),
('Computer Science', 'What is the base of hexadecimal number system?', '2', '8', '10', '16', 'D', 1),
('Computer Science', 'What does SQL stand for?', 'Structured Query Language', 'Simple Query Logic', 'Serial Queue Loop', 'Structured Quick Link', 'A', 1),
-- Mathematics
('Mathematics', 'What is the value of π (pi) approximately?', '3.14159', '2.71828', '1.61803', '1.41421', 'A', 1),
('Mathematics', 'What is the derivative of x²?', 'x', '2x', '2', 'x²', 'B', 1),
('Mathematics', 'What is 15% of 200?', '25', '30', '35', '40', 'B', 1),
('Mathematics', 'How many sides does a hexagon have?', '5', '6', '7', '8', 'B', 1),
('Mathematics', 'What is the square root of 144?', '10', '11', '12', '13', 'C', 1),
('Mathematics', 'What is 2 to the power of 10?', '512', '1024', '2048', '256', 'B', 1),
('Mathematics', 'The sum of angles in a triangle is?', '90°', '180°', '270°', '360°', 'B', 1),
('Mathematics', 'What is the area of a circle with radius 7? (Use π=22/7)', '154', '144', '164', '174', 'A', 1),
('Mathematics', 'Solve: 3x + 6 = 21. Find x.', '3', '4', '5', '6', 'C', 1),
('Mathematics', 'What is the LCM of 4 and 6?', '6', '12', '24', '8', 'B', 1),
-- General Knowledge
('General Knowledge', 'Who invented the telephone?', 'Thomas Edison', 'Nikola Tesla', 'Alexander Graham Bell', 'Guglielmo Marconi', 'C', 1),
('General Knowledge', 'What is the capital of France?', 'London', 'Berlin', 'Paris', 'Madrid', 'C', 1),
('General Knowledge', 'Which planet is known as the Red Planet?', 'Venus', 'Jupiter', 'Mars', 'Saturn', 'C', 1),
('General Knowledge', 'What is the chemical symbol for Gold?', 'Go', 'Gd', 'Au', 'Ag', 'C', 1),
('General Knowledge', 'How many continents are there on Earth?', '5', '6', '7', '8', 'C', 1);

-- Sample Exams
INSERT INTO exams (title, subject, duration_minutes, total_questions, created_by, is_active) VALUES
('Computer Science Fundamentals', 'Computer Science', 30, 10, 1, TRUE),
('Mathematics Assessment', 'Mathematics', 25, 10, 1, TRUE),
('General Knowledge Quiz', 'General Knowledge', 20, 5, 1, TRUE);

-- NOTE: Default passwords use Werkzeug's generate_password_hash
-- The hashes above may not work directly. Use the init_db script to create proper users.
-- Run: python init_db.py after setting up your .env file
