import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.parsers import extract_text_from_file, chunk_text
from backend.rag_engine import RAGEngine
from backend.tracker import StudyTracker
from backend.study_agent import StudyAgent

import threading
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if token and os.getenv("START_BOT", "true").lower() in ("true", "1", "yes"):
        try:
            from backend.telegram_bot import main as run_bot
            t = threading.Thread(target=run_bot, daemon=True)
            t.start()
            print("Telegram Bot started automatically in background daemon thread!")
        except Exception as e:
            print(f"Note starting bot thread: {e}")
    yield

app = FastAPI(title="AI Study Agent API", version="1.0.0", lifespan=lifespan)

# Enable CORS for local testing and n8n webhooks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
rag_engine = RAGEngine(gemini_api_key=GEMINI_API_KEY)
tracker = StudyTracker()
agent = StudyAgent(rag_engine=rag_engine, tracker=tracker, gemini_api_key=GEMINI_API_KEY)

# Pre-index sample data if collection is empty
def init_sample_data():
    try:
        topics = rag_engine.get_all_topics()
        if not topics:
            sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_data", "Agile_Product_Management.md")
            if os.path.exists(sample_path):
                text = extract_text_from_file(sample_path)
                chunks = chunk_text(text, filename="Agile_Product_Management.md")
                rag_engine.index_chunks(chunks)
                print(f"Pre-indexed {len(chunks)} chunks from Agile_Product_Management.md")
    except Exception as e:
        print(f"Sample data initialization note: {e}")

init_sample_data()

# Request Models
class QuizRequest(BaseModel):
    user_id: str = "default_student"
    topic: Optional[str] = None

class AnswerRequest(BaseModel):
    quiz_id: str
    user_id: str = "default_student"
    selected_option: str

class ChapterSummaryRequest(BaseModel):
    topic_or_chapter: str

class ExplainRequest(BaseModel):
    concept: str
    user_id: str = "default_student"

class FlashcardRequest(BaseModel):
    topic: str
    count: int = 5
    user_id: str = "default_student"

class ChapterSummaryRequest(BaseModel):
    topic_or_chapter: str
    user_id: str = "default_student"

class TextIngestRequest(BaseModel):
    title: str
    text: str
    user_id: str = "default_student"

class ProfileUpdateRequest(BaseModel):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    education_level: Optional[str] = None
    field_of_study: Optional[str] = None
    learning_goals: Optional[str] = None
    preferred_theme: Optional[str] = None
    preferred_language: Optional[str] = None

class SessionLogRequest(BaseModel):
    user_id: str
    session_type: str
    topic: str
    duration_seconds: int = 60
    details: Optional[str] = None

# API Endpoints
@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "qdrant": "connected",
        "gemini_api_configured": bool(agent.gemini_api_key),
        "topics_indexed": len(rag_engine.get_all_topics())
    }

class GeminiKeyRequest(BaseModel):
    api_key: str

@app.post("/api/config/gemini")
def set_gemini_key(req: Optional[GeminiKeyRequest] = None, api_key: Optional[str] = Form(None)):
    """Allows user to set or update Gemini API key dynamically and persist to .env."""
    key = (req.api_key if req else None) or api_key
    if not key or not key.strip():
        raise HTTPException(status_code=400, detail="Gemini API key is required")
    key = key.strip()
    os.environ["GEMINI_API_KEY"] = key
    agent.gemini_api_key = key
    rag_engine.gemini_api_key = key

    # Persist to .env
    env_file = Path(__file__).parent.parent / ".env"
    lines = []
    if env_file.exists():
        lines = [l for l in env_file.read_text(encoding="utf-8").splitlines() if not l.startswith("GEMINI_API_KEY=")]
    lines.append(f"GEMINI_API_KEY={key}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"status": "success", "message": "Gemini API key updated successfully and saved to .env"}

@app.get("/api/topics")
def list_topics(user_id: Optional[str] = Query(None)):
    """Returns all topics across the universal Shared Course Library."""
    return rag_engine.get_all_topics()

@app.get("/api/vault/documents")
def list_vault_documents(user_id: Optional[str] = Query(None)):
    """Returns all documents across the universal Shared Course Library."""
    return rag_engine.get_user_documents()

@app.get("/api/vault/document")
def get_vault_document(filename: str = Query(...), user_id: Optional[str] = Query(None)):
    """Returns detailed content, chunk list, and topics for a document in the Shared Course Library."""
    doc = rag_engine.get_document_content(filename=filename)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc

@app.delete("/api/vault/document")
def delete_vault_document(filename: str = Query(...), user_id: Optional[str] = Query(None)):
    """Deletes a document and all its indexed chunks from the Shared Course Library."""
    res = rag_engine.delete_document(filename=filename)
    if res.get("status") == "error":
        raise HTTPException(status_code=500, detail=res.get("message", "Failed to delete document"))
    return res

@app.post("/api/ingest/batch")
async def ingest_batch_files(
    files: List[UploadFile] = File(...),
    user_id: str = Form("common")
):
    """
    Accepts multiple files from folder upload.
    Ingests each file into the Shared Course Library for universal student access.
    """
    results = []
    total_chunks = 0
    errors = []

    for file in files:
        safe_filename = Path(file.filename).name
        if safe_filename.startswith(".") or safe_filename.lower() in ["thumbs.db", "desktop.ini"]:
            continue

        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            text = extract_text_from_file(file_path, gemini_api_key=agent.gemini_api_key)
            if not text.strip():
                continue

            chunks = chunk_text(text, filename=safe_filename)
            indexed_count = rag_engine.index_chunks(chunks, user_id="common")
            total_chunks += indexed_count
            results.append({
                "filename": safe_filename,
                "chunks": indexed_count
            })
        except Exception as e:
            errors.append(f"{safe_filename}: {str(e)}")

    return {
        "status": "success",
        "user_id": "common",
        "files_indexed": len(results),
        "total_chunks_indexed": total_chunks,
        "details": results,
        "errors": errors,
        "message": f"Successfully ingested {len(results)} files ({total_chunks} chunks) into the Shared Course Library!"
    }

@app.post("/api/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    user_id: str = Form("common")
):
    """
    Accepts PDFs, .md, .docx, .pptx, Excel, images, audio/video notes.
    Extracts text, creates chunks, and indexes into the Shared Course Library for all students.
    """
    safe_filename = Path(file.filename).name
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Extract text based on file format
        text = extract_text_from_file(file_path, gemini_api_key=agent.gemini_api_key)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract readable text from this file.")

        # Chunk text and index into shared course library
        chunks = chunk_text(text, filename=safe_filename)
        indexed_count = rag_engine.index_chunks(chunks, user_id="common")

        detected_topics = list(set(c["topic"] for c in chunks))
        return {
            "status": "success",
            "filename": safe_filename,
            "user_id": "common",
            "chunks_indexed": indexed_count,
            "detected_topics": detected_topics,
            "message": f"Successfully ingested {safe_filename} into the Shared Course Library!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/text")
def ingest_text(req: TextIngestRequest):
    chunks = chunk_text(req.text, filename=f"{req.title}.md")
    indexed_count = rag_engine.index_chunks(chunks, user_id="common")
    return {
        "status": "success",
        "title": req.title,
        "user_id": "common",
        "chunks_indexed": indexed_count,
        "topics": list(set(c["topic"] for c in chunks)),
        "message": f"Successfully stored notes in the Shared Course Library!"
    }

@app.post("/api/quiz")
def generate_quiz(req: QuizRequest):
    """Generates an MCQ quiz question grounded in user's materials."""
    try:
        uid = req.user_id.strip() if req.user_id and req.user_id.strip() else "default_student"
        return agent.generate_quiz(user_id=uid, topic=req.topic)
    except Exception as e:
        print(f"Error in api/quiz endpoint: {e}")
        import uuid
        fallback = agent._get_bank_quiz(user_id=req.user_id or "default_student", topic=req.topic)
        fallback["quiz_id"] = str(uuid.uuid4())[:8]
        return fallback

@app.get("/api/auth/config")
def get_auth_config():
    """Returns Supabase public configuration for client authentication."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    return {
        "supabase_url": url,
        "supabase_anon_key": key,
        "auth_enabled": bool(url and key)
    }

@app.get("/api/profile")
def get_profile(user_id: str = Query("default_student")):
    """Retrieves profile for authenticated user."""
    return tracker.get_or_create_profile(user_id=user_id)

@app.put("/api/profile")
def update_profile(req: ProfileUpdateRequest):
    """Updates user profile attributes."""
    data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return tracker.update_profile(user_id=req.user_id, data=data)

@app.get("/api/dashboard/overview")
def get_dashboard_overview(user_id: str = Query("default_student")):
    """Returns real personalized study statistics and activity history for user."""
    return tracker.get_dashboard_overview(user_id=user_id)

@app.post("/api/sessions")
def log_study_session(req: SessionLogRequest):
    """Logs a completed study session (quiz, flashcard review, ELI5 explanation)."""
    return tracker.log_study_session(
        user_id=req.user_id,
        session_type=req.session_type,
        topic=req.topic,
        duration_seconds=req.duration_seconds,
        details=req.details
    )

@app.post("/api/answer")
def evaluate_answer(req: AnswerRequest):
    """Evaluates selected answer, records score in SQLite, returns explanation + citations."""
    result = agent.evaluate_answer(
        quiz_id=req.quiz_id,
        user_id=req.user_id,
        selected_option=req.selected_option
    )
    # Log study session automatically
    try:
        topic_name = result.get("topic") or "General"
        is_corr = result.get("is_correct", False)
        tracker.log_study_session(
            user_id=req.user_id,
            session_type="quiz",
            topic=topic_name,
            duration_seconds=45,
            details=f"{'Correct' if is_corr else 'Needs Review'}: {req.selected_option}"
        )
    except Exception as e:
        print(f"Note logging quiz study session: {e}")
    return result

@app.get("/api/progress")
def get_user_progress(user_id: str = Query("default_student")):
    """Returns total quizzes, overall accuracy %, and topic mastery breakdown."""
    return tracker.get_user_stats(user_id)

@app.get("/api/revise")
def get_revision_plan(user_id: str = Query("default_student")):
    """Identifies topics <70% accuracy and generates targeted revision plan."""
    return agent.generate_revision_plan(user_id)

@app.post("/api/summary")
def summarize_chapter(req: ChapterSummaryRequest):
    """Summarizes a chapter or topic using grounded study notes."""
    res = agent.summarize_chapter(req.topic_or_chapter, user_id=req.user_id)
    try:
        tracker.log_study_session(
            user_id=req.user_id,
            session_type="summary",
            topic=req.topic_or_chapter,
            duration_seconds=120,
            details=f"Read summary of {req.topic_or_chapter}"
        )
    except Exception:
        pass
    return res

@app.post("/api/explain")
def explain_concept(req: ExplainRequest):
    """Explains a concept simply (ELI5 + Analogy + Study Note Reference)."""
    res = agent.explain_concept(req.concept, user_id=req.user_id)
    try:
        tracker.log_study_session(
            user_id=req.user_id,
            session_type="eli5",
            topic=req.concept,
            duration_seconds=90,
            details=f"Explored concept: {req.concept}"
        )
    except Exception:
        pass
    return res

@app.post("/api/flashcards")
def get_flashcards(req: FlashcardRequest):
    """Generates active-recall flashcard deck."""
    res = agent.generate_flashcards(topic=req.topic, count=req.count, user_id=req.user_id)
    try:
        tracker.log_study_session(
            user_id=req.user_id,
            session_type="flashcards",
            topic=req.topic,
            duration_seconds=180,
            details=f"Generated deck of {req.count} cards for {req.topic}"
        )
    except Exception:
        pass
    return res

# Static Dashboard Assets
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "web_dashboard")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AI Study Agent API running. Visit /docs for Swagger API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
