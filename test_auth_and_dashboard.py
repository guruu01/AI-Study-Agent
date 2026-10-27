import sys
import os
import uuid
import unittest
from fastapi.testclient import TestClient

# Ensure current dir is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import app
from backend.tracker import StudyTracker

class TestAuthAndDashboard(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.tracker = StudyTracker()
        self.test_user = f"test_user_{uuid.uuid4().hex[:8]}"

    def test_01_health_and_auth_config(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

        auth_cfg = self.client.get("/api/auth/config")
        self.assertEqual(auth_cfg.status_code, 200)
        data = auth_cfg.json()
        self.assertIn("supabase_url", data)
        self.assertIn("supabase_anon_key", data)
        self.assertIn("auth_enabled", data)
        print("[PASS] Health & Auth config endpoints verified.")
    def test_02_profile_lifecycle(self):
        # 1. Fetch initial profile
        res = self.client.get(f"/api/profile?user_id={self.test_user}")
        self.assertEqual(res.status_code, 200)
        p = res.json()
        self.assertEqual(p["id"], self.test_user)
        self.assertEqual(p["preferred_theme"], "dark")

        # 2. Update profile
        update_payload = {
            "user_id": self.test_user,
            "full_name": "Dr. Marie Curie",
            "education_level": "Doctorate",
            "field_of_study": "Nuclear Physics",
            "learning_goals": "Master radiation decay formulas",
            "preferred_theme": "light",
            "preferred_language": "fr"
        }
        put_res = self.client.put("/api/profile", json=update_payload)
        self.assertEqual(put_res.status_code, 200)
        updated = put_res.json()
        self.assertEqual(updated["full_name"], "Dr. Marie Curie")
        self.assertEqual(updated["field_of_study"], "Nuclear Physics")
        self.assertEqual(updated["preferred_theme"], "light")
        self.assertEqual(updated["preferred_language"], "fr")

        # 3. Retrieve updated profile
        verify_res = self.client.get(f"/api/profile?user_id={self.test_user}")
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.json()["full_name"], "Dr. Marie Curie")
        print("[PASS] Profile creation, update, and retrieval persistence verified.")

    def test_03_dashboard_overview_empty_and_populated(self):
        fresh_user = f"brand_new_{uuid.uuid4().hex[:8]}"
        # 1. Clean empty state for new user
        res = self.client.get(f"/api/dashboard/overview?user_id={fresh_user}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_sessions"], 0)
        self.assertEqual(data["study_time_minutes"], 0.0)
        self.assertEqual(data["accuracy_pct"], 0.0)
        self.assertEqual(data["mastered_topics_count"], 0)
        self.assertEqual(len(data["recent_activity"]), 0)

        # 2. Log a study session
        session_payload = {
            "user_id": fresh_user,
            "session_type": "flashcards",
            "topic": "Quantum Mechanics",
            "duration_seconds": 300,
            "details": "Reviewed 10 flashcards"
        }
        s_res = self.client.post("/api/sessions", json=session_payload)
        self.assertEqual(s_res.status_code, 200)

        # 3. Re-check dashboard overview
        res2 = self.client.get(f"/api/dashboard/overview?user_id={fresh_user}")
        data2 = res2.json()
        self.assertEqual(data2["total_sessions"], 1)
        self.assertEqual(data2["study_time_minutes"], 5.0)
        self.assertEqual(len(data2["recent_activity"]), 1)
        self.assertEqual(data2["recent_activity"][0]["type"], "flashcards")
        print("[PASS] Dashboard overview real metrics & activity timeline verified.")

    def test_04_static_assets_serving(self):
        # 1. Landing HTML
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("Your Personal AI-Powered Learning Companion", html)
        self.assertIn("Continue with Google", html)
        self.assertIn("modal-otp-verify", html)
        self.assertIn("modal-profile", html)

        # 2. CSS Styles
        css_res = self.client.get("/static/style.css")
        self.assertEqual(css_res.status_code, 200)
        self.assertIn('[data-theme="light"]', css_res.text)
        self.assertIn('.btn-google-oauth', css_res.text)

        # 3. JS App
        js_res = self.client.get("/static/app.js")
        self.assertEqual(js_res.status_code, 200)
        self.assertIn("signInWithOAuth", js_res.text)
        self.assertIn("signInWithOtp", js_res.text)
        self.assertIn("verifyOtp", js_res.text)
        print("[PASS] Static landing page, CSS theme tokens, and JS authentication bundle verified.")

if __name__ == "__main__":
    unittest.main()
