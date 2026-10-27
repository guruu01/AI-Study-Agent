import os
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load env variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

print("Starting Telegram Study Bot...")
print(f"Backend API: {API_BASE_URL}")

def send_telegram_request(endpoint: str, payload: dict) -> dict:
    try:
        res = requests.post(f"{TELEGRAM_API}/{endpoint}", json=payload, timeout=15)
        return res.json()
    except Exception as e:
        print(f"Telegram API error ({endpoint}): {e}")
        return {}

def send_message(chat_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_telegram_request("sendMessage", payload)

def answer_callback_query(callback_query_id: str, text: str = ""):
    return send_telegram_request("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text
    })

def handle_start(chat_id: int):
    msg = (
        "👋 *Welcome to your AI Study Agent!*\n\n"
        "I turn your uploaded study materials into active recall tools and quiz you directly here.\n\n"
        "📚 *What I Can Do:*\n"
        "• 📝 `/quiz [topic]` - Take a grounded multiple-choice quiz\n"
        "• 📖 `/summary [chapter]` - Executive chapter summary\n"
        "• 💡 `/explain [concept]` - ELI5 simple concept explanation with analogies\n"
        "• 📇 `/flashcards [topic]` - Active recall flashcards\n"
        "• 📊 `/score` - Track your accuracy and progress\n"
        "• 🔍 `/revise` - Diagnose weak topics and generate a revision plan\n\n"
        "📁 *Drop any study document (PDF, Word, PPT, Excel, image, or audio note) here to index it!*"
    )
    markup = {
        "inline_keyboard": [
            [
                {"text": "🎯 Start Agile Quiz", "callback_data": "cmd:quiz:Agile Methodology"},
                {"text": "📊 My Scorecard", "callback_data": "cmd:score"}
            ],
            [
                {"text": "💡 Explain 'Sprint'", "callback_data": "cmd:explain:Sprint"},
                {"text": "🔍 Revision Plan", "callback_data": "cmd:revise"}
            ]
        ]
    }
    send_message(chat_id, msg, markup)

def handle_quiz(chat_id: int, user_id: str, topic: str = None):
    send_message(chat_id, "⚡ *Retrieving your notes and generating active-recall question...*")
    try:
        res = requests.post(f"{API_BASE_URL}/api/quiz", json={
            "user_id": str(user_id),
            "topic": topic if topic else None
        }, timeout=20)
        quiz = res.json()

        options = quiz.get("options", {})
        q_text = (
            f"🎯 *Topic: {quiz.get('topic', 'General')}*\n\n"
            f"❓ *Question:* {quiz.get('question', '')}\n\n"
            f"🅰️ *A.* {options.get('A', '')}\n\n"
            f"🅱️ *B.* {options.get('B', '')}\n\n"
            f"🅲 *C.* {options.get('C', '')}\n\n"
            f"🅳 *D.* {options.get('D', '')}\n\n"
            f"_Tap your answer below:_ 👇"
        )
        quiz_id = quiz.get("quiz_id", "")
        markup = {
            "inline_keyboard": [
                [
                    {"text": "🅰️ Option A", "callback_data": f"ans:{quiz_id}:A"},
                    {"text": "🅱️ Option B", "callback_data": f"ans:{quiz_id}:B"}
                ],
                [
                    {"text": "🅲 Option C", "callback_data": f"ans:{quiz_id}:C"},
                    {"text": "🅳 Option D", "callback_data": f"ans:{quiz_id}:D"}
                ]
            ]
        }
        send_message(chat_id, q_text, markup)
    except Exception as e:
        send_message(chat_id, f"❌ Error generating quiz: {e}")

def handle_answer_callback(chat_id: int, user_id: str, quiz_id: str, selected_option: str, cb_id: str):
    answer_callback_query(cb_id, f"You selected Option {selected_option}")
    try:
        res = requests.post(f"{API_BASE_URL}/api/answer", json={
            "quiz_id": quiz_id,
            "user_id": str(user_id),
            "selected_option": selected_option
        }, timeout=15)
        eval_res = res.json()

        is_corr = eval_res.get("is_correct", False)
        status_line = "🎉 *CORRECT!* Well done! ✅" if is_corr else f"❌ *INCORRECT!* The correct answer is *Option {eval_res.get('correct_option')}* 📌"

        stats = eval_res.get("user_stats", {})
        acc = stats.get("accuracy_pct", 0)
        correct_cnt = stats.get("correct_answers", 0)
        total_cnt = stats.get("total_quizzes", 0)

        feedback_msg = (
            f"{status_line}\n\n"
            f"💡 *Explanation:*\n{eval_res.get('explanation', '')}\n\n"
            f"📖 *Grounded in Your Notes:*\n_{eval_res.get('source_citation', 'Study Notes')}_\n\n"
            f"───────────────\n"
            f"📊 *Your Score:* {acc}% ({correct_cnt}/{total_cnt} correct)"
        )
        markup = {
            "inline_keyboard": [
                [
                    {"text": "Next Question ➡️", "callback_data": "cmd:quiz"},
                    {"text": "Revision Plan 🔍", "callback_data": "cmd:revise"}
                ]
            ]
        }
        send_message(chat_id, feedback_msg, markup)
    except Exception as e:
        send_message(chat_id, f"Error evaluating answer: {e}")

def handle_score(chat_id: int, user_id: str):
    try:
        res = requests.get(f"{API_BASE_URL}/api/progress?user_id={user_id}", timeout=10)
        stats = res.json()

        breakdown = stats.get("topic_breakdown", [])
        bd_text = "\n".join([
            f"• *{t['topic']}:* {t['accuracy']}% ({t['correct']}/{t['attempts']}) — {t['status']}"
            for t in breakdown
        ]) if breakdown else "No quizzes completed yet!"

        msg = (
            f"📊 *YOUR STUDY SCORECARD*\n\n"
            f"🎯 *Total Questions:* {stats.get('total_quizzes', 0)}\n"
            f"✅ *Correct Answers:* {stats.get('correct_answers', 0)}\n"
            f"📈 *Overall Accuracy:* {stats.get('accuracy_pct', 0)}%\n\n"
            f"📌 *Topic Breakdown:*\n{bd_text}\n\n"
            f"Use `/quiz` to practice or `/revise` to review weak spots! 🚀"
        )
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error fetching progress: {e}")

def handle_revise(chat_id: int, user_id: str):
    send_message(chat_id, "🔍 *Diagnosing weak topics and building your revision roadmap...*")
    try:
        res = requests.get(f"{API_BASE_URL}/api/revise?user_id={user_id}", timeout=20)
        plan = res.json()

        plan_text = plan.get("revision_plan") or plan.get("message", "All topics mastered!")
        msg = f"🎯 *TARGETED REVISION ROADMAP*\n\n{plan_text}\n\n───────────────\n_Tip: Re-test yourself with `/quiz`!_"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error generating revision plan: {e}")

def handle_explain(chat_id: int, concept: str):
    send_message(chat_id, f"💡 *Formulating ELI5 explanation for '{concept}'...*")
    try:
        res = requests.post(f"{API_BASE_URL}/api/explain", json={"concept": concept}, timeout=20)
        data = res.json()
        sources = ", ".join(data.get("sources", ["Notes"]))
        msg = (
            f"💡 *EXPLAINING: {data.get('concept', concept)}*\n\n"
            f"{data.get('explanation', '')}\n\n"
            f"📚 *Grounded Sources:* {sources}"
        )
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error explaining concept: {e}")

def handle_summary(chat_id: int, topic: str):
    send_message(chat_id, f"📖 *Synthesizing chapter summary for '{topic}'...*")
    try:
        res = requests.post(f"{API_BASE_URL}/api/summary", json={"topic_or_chapter": topic}, timeout=20)
        data = res.json()
        sources = ", ".join(data.get("sources", ["Notes"]))
        msg = (
            f"📖 *CHAPTER SUMMARY: {data.get('topic', topic)}*\n\n"
            f"{data.get('summary', '')}\n\n"
            f"📚 *Sources Cited:* {sources}"
        )
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error generating summary: {e}")

def handle_document_upload(chat_id: int, file_id: str, file_name: str):
    send_message(chat_id, f"📥 *Downloading and parsing `{file_name}` into your vector vault...*")
    try:
        # Get file path from Telegram
        f_info = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}").json()
        file_path_on_server = f_info.get("result", {}).get("file_path")
        
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path_on_server}"
        file_bytes = requests.get(file_url).content

        # Upload to FastAPI /api/ingest
        files = {"file": (file_name, file_bytes)}
        res = requests.post(f"{API_BASE_URL}/api/ingest", files=files, timeout=40)
        data = res.json()

        topics = ", ".join(data.get("detected_topics", []))
        msg = (
            f"✅ *Document Ingested & Grounded!*\n\n"
            f"📄 *File:* `{file_name}`\n"
            f"📦 *Chunks Indexed:* {data.get('chunks_indexed', 0)}\n"
            f"You can now take a quiz with `/quiz` or get a summary with `/summary`! 🚀"
        )
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error ingesting document: {e}")

def handle_set_key(chat_id: int, key: str):
    key = key.strip()
    if not key or not key.startswith("AIza"):
        send_message(chat_id, "⚠️ *Invalid Key Format!*\nGoogle Gemini API keys typically start with `AIzaSy...`\n\nUsage: `/key YOUR_API_KEY`\nGet your free key at: https://aistudio.google.com/app/apikey")
        return
    try:
        res = requests.post(f"{API_BASE_URL}/api/config/gemini", json={"api_key": key}, timeout=10)
        if res.status_code == 200:
            send_message(
                chat_id,
                "🎉 *Google Gemini API Key Configured!*\n\n"
                "Gemini 1.5/2.0 Flash is now active for:\n"
                "• Dynamic multimodal document parsing (PDF, DOCX, PPTX, Images, Audio)\n"
                "• Real-time grounded active-recall question generation\n"
                "• Chapter summaries & ELI5 concept explanations\n\n"
                "Try sending `/quiz`, `/summary`, or `/explain` now! 🚀"
            )
        else:
            send_message(chat_id, f"❌ Failed to set key: {res.text}")
    except Exception as e:
        send_message(chat_id, f"❌ Error communicating with backend: {e}")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    # Delete any dangling webhook so getUpdates polling works cleanly
    requests.get(f"{TELEGRAM_API}/deleteWebhook")

    bot_info = requests.get(f"{TELEGRAM_API}/getMe").json()
    username = bot_info.get("result", {}).get("username", "UnknownBot")
    print(f"✅ Bot Connected: @{username}")
    print("🚀 Polling Telegram for messages and quizzes...")

    offset = 0
    while True:
        try:
            updates_res = requests.get(f"{TELEGRAM_API}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25)
            updates = updates_res.json().get("result", [])

            for u in updates:
                offset = u["update_id"] + 1

                # 1. Handle Inline Button Callback Query
                if "callback_query" in u:
                    cb = u["callback_query"]
                    cb_id = cb["id"]
                    user_id = str(cb["from"]["id"])
                    chat_id = cb["message"]["chat"]["id"]
                    data = cb.get("data", "")

                    if data.startswith("ans:"):
                        parts = data.split(":")
                        handle_answer_callback(chat_id, user_id, parts[1], parts[2], cb_id)
                    elif data.startswith("cmd:"):
                        answer_callback_query(cb_id)
                        parts = data.split(":")
                        cmd = parts[1]
                        arg = parts[2] if len(parts) > 2 else None
                        if cmd == "quiz":
                            handle_quiz(chat_id, user_id, arg)
                        elif cmd == "score":
                            handle_score(chat_id, user_id)
                        elif cmd == "revise":
                            handle_revise(chat_id, user_id)
                        elif cmd == "explain":
                            handle_explain(chat_id, arg or "Agile")
                    continue

                # 2. Handle Regular Messages
                if "message" in u:
                    msg = u["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = str(msg["from"]["id"])
                    text = msg.get("text", "").strip()

                    # Handle Document Uploads
                    if "document" in msg:
                        doc = msg["document"]
                        handle_document_upload(chat_id, doc["file_id"], doc.get("file_name", "document.pdf"))
                        continue

                    # Handle Photo Uploads
                    if "photo" in msg:
                        photo = msg["photo"][-1]
                        handle_document_upload(chat_id, photo["file_id"], "study_photo.jpg")
                        continue

                    # Handle Voice / Audio Notes
                    if "voice" in msg or "audio" in msg:
                        audio = msg.get("voice") or msg.get("audio")
                        handle_document_upload(chat_id, audio["file_id"], "lecture_audio.mp3")
                        continue

                    # Handle Commands
                    if text.startswith("/start") or text.startswith("/help"):
                        handle_start(chat_id)
                    elif text.startswith("/quiz"):
                        topic = text.replace("/quiz", "").strip() or None
                        handle_quiz(chat_id, user_id, topic)
                    elif text.startswith("/score") or text.startswith("/progress"):
                        handle_score(chat_id, user_id)
                    elif text.startswith("/revise") or text.startswith("/weak"):
                        handle_revise(chat_id, user_id)
                    elif text.startswith("/explain"):
                        concept = text.replace("/explain", "").strip() or "Sprint"
                        handle_explain(chat_id, concept)
                    elif text.startswith("/summary"):
                        topic = text.replace("/summary", "").strip() or "The Scrum Framework"
                        handle_summary(chat_id, topic)
                    elif text.startswith("/key") or text.startswith("/setkey"):
                        parts = text.split(" ", 1)
                        if len(parts) > 1 and parts[1].strip():
                            handle_set_key(chat_id, parts[1].strip())
                        else:
                            send_message(
                                chat_id,
                                "🔑 *How to Set Your Gemini API Key:*\n\n"
                                "1. Get your free key at: https://aistudio.google.com/app/apikey\n"
                                "2. Send it here as: `/key AIzaSy...`\n\n"
                                "Or set it in the Web Dashboard at: http://localhost:8000"
                            )
                    else:
                        # Fallback conversational response
                        handle_start(chat_id)

        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    main()
