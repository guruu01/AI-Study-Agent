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

class FlashcardRequest(BaseModel):
    topic: str
    count: int = 5

class TextIngestRequest(BaseModel):
    title: str
    text: str

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
def list_topics():
    return rag_engine.get_all_topics()

@app.post("/api/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """
    Accepts PDFs, .md, .docx, .pptx, Excel, images, audio/video notes.
    Extracts text, creates chunks, and indexes into Qdrant for RAG.
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

        # Chunk text
        chunks = chunk_text(text, filename=safe_filename)
        indexed_count = rag_engine.index_chunks(chunks)

        detected_topics = list(set(c["topic"] for c in chunks))
        return {
            "status": "success",
            "filename": safe_filename,
            "chunks_indexed": indexed_count,
            "detected_topics": detected_topics,
            "message": f"Successfully ingested {safe_filename} into study vector store!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/text")
def ingest_text(req: TextIngestRequest):
    chunks = chunk_text(req.text, filename=f"{req.title}.md")
    indexed_count = rag_engine.index_chunks(chunks)
    return {
        "status": "success",
        "title": req.title,
        "chunks_indexed": indexed_count,
        "topics": list(set(c["topic"] for c in chunks))
    }

@app.post("/api/quiz")
def generate_quiz(req: QuizRequest):
    """Generates an MCQ quiz question grounded in user's materials."""
    return agent.generate_quiz(user_id=req.user_id, topic=req.topic)

@app.post("/api/answer")
def evaluate_answer(req: AnswerRequest):
    """Evaluates selected answer, records score in SQLite, returns explanation + citations."""
    return agent.evaluate_answer(
        quiz_id=req.quiz_id,
        user_id=req.user_id,
        selected_option=req.selected_option
    )

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
    return agent.summarize_chapter(req.topic_or_chapter)

@app.post("/api/explain")
def explain_concept(req: ExplainRequest):
    """Explains a concept simply (ELI5 + Analogy + Study Note Reference)."""
    return agent.explain_concept(req.concept)

@app.post("/api/flashcards")
def get_flashcards(req: FlashcardRequest):
    """Generates active-recall flashcard deck."""
    return agent.generate_flashcards(topic=req.topic, count=req.count)

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
