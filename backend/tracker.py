import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "study_tracker.db")

class StudyTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Quizzes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    selected_option TEXT NOT NULL,
                    correct_option TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    source_doc TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Active Quiz Session table (for Telegram callback handling)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_quizzes (
                    quiz_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_option TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    source_citation TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_active_quiz(self, quiz_id: str, user_id: str, topic: str, question: str, 
                         options_json: str, correct_option: str, explanation: str, source_citation: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO active_quizzes 
                (quiz_id, user_id, topic, question, options_json, correct_option, explanation, source_citation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (quiz_id, user_id, topic, question, options_json, correct_option, explanation, source_citation))
            conn.commit()

    def get_active_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM active_quizzes WHERE quiz_id = ?', (quiz_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_quiz_result(self, user_id: str, topic: str, question: str, 
                           selected_option: str, correct_option: str, is_correct: bool,
                           source_doc: str = "") -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quiz_history 
                (user_id, topic, question, selected_option, correct_option, is_correct, source_doc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, topic, question, selected_option, correct_option, 1 if is_correct else 0, source_doc))
            conn.commit()
        return self.get_user_stats(user_id)

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Overall totals
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(is_correct) as correct_count
                FROM quiz_history
                WHERE user_id = ?
            ''', (user_id,))
            overall = cursor.fetchone()
            total = overall["total_attempts"] or 0
            correct = overall["correct_count"] or 0
            accuracy = round((correct / total * 100), 1) if total > 0 else 0.0

            # Topic-wise breakdown
            cursor.execute('''
                SELECT 
                    topic,
                    COUNT(*) as attempts,
                    SUM(is_correct) as correct
                FROM quiz_history
                WHERE user_id = ?
                GROUP BY topic
                ORDER BY (CAST(SUM(is_correct) AS FLOAT) / COUNT(*)) ASC
            ''', (user_id,))
            topics = []
            for row in cursor.fetchall():
                t_attempts = row["attempts"]
                t_correct = row["correct"] or 0
                t_acc = round((t_correct / t_attempts * 100), 1)
                
                status = "Mastered" if t_acc >= 80 else ("Reviewing" if t_acc >= 60 else "Needs Revision")
                topics.append({
                    "topic": row["topic"],
                    "attempts": t_attempts,
                    "correct": t_correct,
                    "accuracy": t_acc,
                    "status": status
                })

            return {
                "user_id": user_id,
                "total_quizzes": total,
                "correct_answers": correct,
                "accuracy_pct": accuracy,
                "topic_breakdown": topics
            }

    def get_revision_topics(self, user_id: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        Identifies topics where user accuracy is below threshold.
        """
        stats = self.get_user_stats(user_id)
        weak_topics = []
        for t in stats["topic_breakdown"]:
            if t["accuracy"] < threshold:
                # Fetch recent failed questions for this topic
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT question, selected_option, correct_option, source_doc, created_at
                        FROM quiz_history
                        WHERE user_id = ? AND topic = ? AND is_correct = 0
                        ORDER BY created_at DESC
                        LIMIT 3
                    ''', (user_id, t["topic"]))
                    failed_questions = [dict(r) for r in cursor.fetchall()]

                weak_topics.append({
                    "topic": t["topic"],
                    "accuracy": t["accuracy"],
                    "attempts": t["attempts"],
                    "failed_questions": failed_questions
                })
        return weak_topics

    def get_recent_questions(self, user_id: str, limit: int = 15) -> List[str]:
        """Returns the text of recently answered or generated questions to avoid repeats."""
        questions = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. From active_quizzes (questions generated recently)
            cursor.execute('''
                SELECT question FROM active_quizzes
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            for row in cursor.fetchall():
                q = row["question"].strip() if row["question"] else ""
                if q and q not in questions:
                    questions.append(q)

            # 2. From quiz_history (questions answered)
            cursor.execute('''
                SELECT question FROM quiz_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            ''', (user_id, limit))
            for row in cursor.fetchall():
                q = row["question"].strip() if row["question"] else ""
                if q and q not in questions:
                    questions.append(q)

        return questions[:limit]

