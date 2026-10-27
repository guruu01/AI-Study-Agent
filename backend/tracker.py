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
            # Profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    email TEXT,
                    full_name TEXT,
                    avatar_url TEXT,
                    education_level TEXT DEFAULT 'Undergraduate',
                    field_of_study TEXT DEFAULT 'Computer Science',
                    learning_goals TEXT DEFAULT 'Master core concepts through active recall',
                    preferred_theme TEXT DEFAULT 'dark',
                    preferred_language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Study Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    duration_seconds INTEGER DEFAULT 60,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Study Progress table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    status TEXT DEFAULT 'in_progress',
                    progress_pct INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
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
            # User Preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    theme TEXT DEFAULT 'dark',
                    auto_advance INTEGER DEFAULT 1,
                    daily_goal_minutes INTEGER DEFAULT 30,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # --- Profile Management ---
    def get_or_create_profile(self, user_id: str, email: Optional[str] = None, 
                               full_name: Optional[str] = None, avatar_url: Optional[str] = None) -> Dict[str, Any]:
        """Gets user profile or creates a default one if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM profiles WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                # Update email or avatar if newly provided from OAuth
                updates = []
                params = []
                if email and not profile.get("email"):
                    updates.append("email = ?")
                    params.append(email)
                if full_name and (not profile.get("full_name") or profile.get("full_name") == "Student"):
                    updates.append("full_name = ?")
                    params.append(full_name)
                if avatar_url and not profile.get("avatar_url"):
                    updates.append("avatar_url = ?")
                    params.append(avatar_url)
                if updates:
                    params.append(user_id)
                    cursor.execute(f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?", params)
                    conn.commit()
                    cursor.execute('SELECT * FROM profiles WHERE id = ?', (user_id,))
                    profile = dict(cursor.fetchone())
                return profile

            # Create new profile
            default_name = full_name or (email.split("@")[0].title() if email else user_id.capitalize())
            cursor.execute('''
                INSERT INTO profiles (id, email, full_name, avatar_url, education_level, field_of_study, learning_goals, preferred_theme, preferred_language)
                VALUES (?, ?, ?, ?, 'Undergraduate', 'Computer Science', 'Master core concepts through active recall & spaced repetition', 'dark', 'en')
            ''', (user_id, email or f"{user_id}@studyagent.ai", default_name, avatar_url or ""))
            conn.commit()

            cursor.execute('SELECT * FROM profiles WHERE id = ?', (user_id,))
            return dict(cursor.fetchone())

    def update_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates editable user profile fields."""
        allowed_fields = [
            "full_name", "avatar_url", "education_level", 
            "field_of_study", "learning_goals", "preferred_theme", "preferred_language"
        ]
        updates = []
        params = []
        for key in allowed_fields:
            if key in data and data[key] is not None:
                updates.append(f"{key} = ?")
                params.append(data[key])

        if not updates:
            return self.get_or_create_profile(user_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        return self.get_or_create_profile(user_id)

    # --- Study Sessions & Activity Tracking ---
    def log_study_session(self, user_id: str, session_type: str, topic: str, 
                          duration_seconds: int = 60, details: Optional[str] = None) -> Dict[str, Any]:
        """Logs a completed study session (e.g. quiz, flashcard review, ELI5 concept exploration)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO study_sessions (user_id, session_type, topic, duration_seconds, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, session_type, topic, duration_seconds, details or ""))
            conn.commit()
            session_id = cursor.lastrowid
            cursor.execute('SELECT * FROM study_sessions WHERE id = ?', (session_id,))
            return dict(cursor.fetchone())

    def record_study_progress(self, user_id: str, activity_type: str, topic: str, 
                              status: str = "completed", progress_pct: int = 100):
        """Records activity progress for dashboard tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO study_progress (user_id, activity_type, topic, status, progress_pct)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, activity_type, topic, status, progress_pct))
            conn.commit()

    def get_recent_activity(self, user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Returns unified timeline of recent user actions (quizzes, flashcards, readings)."""
        activity = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. From quiz_history
            cursor.execute('''
                SELECT 'quiz' as type, topic, 
                       CASE WHEN is_correct = 1 THEN 'Answered Correctly: ' || substr(question, 1, 60)
                            ELSE 'Needs Review: ' || substr(question, 1, 60) END as description,
                       is_correct, created_at
                FROM quiz_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            for r in cursor.fetchall():
                activity.append(dict(r))

            # 2. From study_sessions
            cursor.execute('''
                SELECT session_type as type, topic, 
                       CASE WHEN details != '' THEN details ELSE 'Completed ' || session_type || ' session' END as description,
                       1 as is_correct, created_at
                FROM study_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            for r in cursor.fetchall():
                activity.append(dict(r))

        # Sort combined activity by created_at desc
        activity.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return activity[:limit]

    def get_dashboard_overview(self, user_id: str) -> Dict[str, Any]:
        """Calculates personalized dashboard statistics for the authenticated user."""
        profile = self.get_or_create_profile(user_id)
        stats = self.get_user_stats(user_id)
        recent_activity = self.get_recent_activity(user_id, limit=6)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Total study sessions logged
            cursor.execute('SELECT COUNT(*) as session_count, SUM(duration_seconds) as total_duration FROM study_sessions WHERE user_id = ?', (user_id,))
            session_row = cursor.fetchone()
            session_count = session_row["session_count"] or 0
            session_seconds = session_row["total_duration"] or 0

            # If no manual sessions logged, estimate study time from quizzes (approx 90s per quiz)
            if session_seconds == 0 and stats["total_quizzes"] > 0:
                session_seconds = stats["total_quizzes"] * 90

            study_time_minutes = round(session_seconds / 60, 1)

            # Mastered topics count (accuracy >= 80% with at least 1 attempt)
            mastered_count = sum(1 for t in stats["topic_breakdown"] if t.get("status") == "Mastered")

            # Total study activities
            total_activities = stats["total_quizzes"] + session_count

        return {
            "profile": profile,
            "total_sessions": total_activities,
            "study_time_minutes": study_time_minutes,
            "total_quizzes": stats["total_quizzes"],
            "correct_answers": stats["correct_answers"],
            "accuracy_pct": stats["accuracy_pct"],
            "mastered_topics_count": mastered_count,
            "topic_breakdown": stats["topic_breakdown"],
            "recent_activity": recent_activity
        }


