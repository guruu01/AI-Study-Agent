import sys
import os
import uuid
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from backend.main import app

class TestStudyToolsIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_id = f"student_{uuid.uuid4().hex[:6]}"

    def test_01_quiz_and_answer_session_logging(self):
        # 1. Generate Quiz
        res = self.client.post("/api/quiz", json={"user_id": self.user_id})
        self.assertEqual(res.status_code, 200)
        quiz = res.json()
        self.assertIn("quiz_id", quiz)
        self.assertIn("question", quiz)
        self.assertIn("options", quiz)
        self.assertEqual(len(quiz["options"]), 4)

        # 2. Answer Quiz
        selected = list(quiz["options"].values())[0] if isinstance(quiz["options"], dict) else quiz["options"][0]
        ans_res = self.client.post("/api/answer", json={
            "quiz_id": quiz["quiz_id"],
            "user_id": self.user_id,
            "selected_option": selected
        })
        self.assertEqual(ans_res.status_code, 200)
        ans_data = ans_res.json()
        self.assertIn("is_correct", ans_data)
        self.assertIn("explanation", ans_data)

        # 3. Check that study session was logged in Dashboard Overview
        dash_res = self.client.get(f"/api/dashboard/overview?user_id={self.user_id}")
        self.assertEqual(dash_res.status_code, 200)
        dash_data = dash_res.json()
        self.assertGreaterEqual(dash_data["total_sessions"], 1)
        self.assertEqual(dash_data["total_quizzes"], 1)
        self.assertGreater(len(dash_data["recent_activity"]), 0)
        print("[PASS] Quiz generation, answer evaluation, and automatic study session logging verified.")

    def test_02_concept_explainer_and_flashcards(self):
        # 1. Explain Concept
        exp_res = self.client.post("/api/explain", json={"concept": "Sprint Retrospective", "user_id": self.user_id})
        self.assertEqual(exp_res.status_code, 200)
        exp_data = exp_res.json()
        self.assertIn("explanation", exp_data)

        # 2. Flashcards
        fc_res = self.client.post("/api/flashcards", json={"topic": "Agile Methodology", "count": 3, "user_id": self.user_id})
        self.assertEqual(fc_res.status_code, 200)
        fc_data = fc_res.json()
        self.assertIn("flashcards", fc_data)
        self.assertGreaterEqual(len(fc_data["flashcards"]), 1)
        print("[PASS] Concept Explainer (ELI5) and 3D Flashcards deck generation verified.")

    def test_03_text_ingest_and_revision(self):
        # 1. Text Ingestion to Private Vault
        ingest_res = self.client.post("/api/ingest/text", json={
            "title": "Machine Learning Fundamentals",
            "text": "Supervised learning trains models on labeled datasets with inputs and targets.",
            "user_id": self.user_id
        })
        self.assertEqual(ingest_res.status_code, 200)

        # 2. Vault documents check
        vault_res = self.client.get(f"/api/vault/documents?user_id={self.user_id}")
        self.assertEqual(vault_res.status_code, 200)
        docs = vault_res.json()
        found = any(d["filename"] == "Machine Learning Fundamentals.md" for d in docs)
        self.assertTrue(found)

        # 3. Revision diagnostic
        rev_res = self.client.get(f"/api/revise?user_id={self.user_id}")
        self.assertEqual(rev_res.status_code, 200)
        print("[PASS] Document Vault text ingestion and Revision diagnostic roadmap verified.")

if __name__ == "__main__":
    unittest.main()
