# 🧠 AI Study Agent — Multi-Format RAG & Telegram Active Recall Engine

An intelligent, grounded AI study assistant built with **n8n Workflow Automation**, **Google Gemini API**, **Qdrant Vector Database**, and a **FastAPI Companion Engine** with an interactive Web Dashboard.

---

## 🌟 Key Features

| Capability | Description |
| :--- | :--- |
| 📁 **Multi-Format Ingestion** | Ingests **PDFs, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), Markdown (.md), Plain Text, Images (diagrams/OCR), and Audio/Video lecture recordings**. |
| 🔍 **Strict Document Retrieval (RAG)** | Chunks and embeds documents using **Google Gemini Embeddings (`models/text-embedding-004`)** into a local **Qdrant Vector DB**. Answers and quizzes cite your own notes directly instead of hallucinating general knowledge. |
| 📝 **Active Recall Quizzing** | Generates high-yield **Multiple Choice Questions (MCQs)** with 4 distinct options (`A`, `B`, `C`, `D`). Interactive Telegram inline buttons provide immediate feedback. |
| 💡 **Concept Explainer (ELI5)** | Breaks down difficult concepts using a 3-tier format: Everyday Analogy (for a 10-year-old), Real-World Application, and Note Citations. |
| 📖 **Chapter Summarization** | Produces structured executive summaries with key frameworks, formulas, and common exam traps. |
| 📇 **3D Active-Recall Flashcards** | Generates question/answer flashcard decks with memory hooks and key takeaways. |
| 📊 **Score & Mastery Tracking** | Logs every quiz question in a persistent **SQLite Database** (`study_tracker.db`), computing overall accuracy %, current streaks, and topic-by-topic mastery levels. |
| ⚠️ **Weak Topic Diagnostics** | Automatically flags topics with **<70% accuracy** and synthesizes a **15-Minute Targeted Revision Roadmap** tailored to the specific questions you missed. |

---

## 🏗️ Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │             Telegram Bot User                │
                               └──────────────────────┬───────────────────────┘
                                                      │ (Quiz / Ingest / Score)
                                                      ▼
┌──────────────────────┐                       ┌──────────────┐
│  Web Dashboard UI    │──────────────────────►│  n8n Engine  │ (Port 5678)
│ (http://localhost:   │                       │ (Workflow:   │
│         8000)        │                       │  AI Study    │
└──────────┬───────────┘                       │    Agent)    │
           │                                   └──────┬───────┘
           │ (REST / Webhook)                         │ (REST Webhooks)
           ▼                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Study Agent Service                 │
│  • Multi-Format Parser (PDF, DOCX, PPTX, XLSX, MD, Media)   │
│  • Google Gemini 2.0 / 1.5 Flash Reasoning Model            │
│  • SQLite Study Tracker (Scores, Weak Topics, Quizzes)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Embeddings / Cosine Search)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Qdrant Vector Database                      │
│            Collection: study_materials (768-dim)            │
│                 (http://localhost:6333)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites (Already Running on your Machine!)
- **n8n Container:** Running on `http://localhost:5678`
- **Qdrant Container:** Running on `http://localhost:6333`
- **Study Agent API & Web Dashboard:** Running on `http://localhost:8000`

### 2. Access the Interactive Web Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

From the dashboard you can:
- Take interactive quizzes with real-time feedback and document citations.
- Drag & drop study documents to automatically chunk and index them into Qdrant.
- Ask for ELI5 explanations and chapter summaries.
- Practice with 3D flip flashcards.
- View your topic mastery breakdown and generate targeted revision guides.

---

## 📱 Telegram Bot Commands

Your Telegram bot is wired through the imported n8n workflow (`AI Study Agent - Multi-Format RAG & Telegram Quiz`):

| Command | Action |
| :--- | :--- |
| `/start` or `/help` | Displays the interactive study menu with quick-action buttons. |
| `/quiz [topic]` | Starts an active recall quiz on a topic (e.g. `/quiz Agile` or just `/quiz` to practice your weakest topic). |
| `/summary [chapter]` | Generates an executive summary of a chapter or topic from your notes. |
| `/explain [concept]` | Explains a tough concept in simple language with real-world analogies. |
| `/flashcards [topic]`| Generates active recall flashcards from your uploaded materials. |
| `/score` | Shows total questions taken, overall accuracy %, and topic mastery breakdown. |
| `/revise` | Diagnoses topics with under 70% accuracy and outputs a targeted study guide. |
| *Send any file* | Ingests PDF, DOCX, PPTX, Excel, notes, or audio/video directly into your vector store. |

---

## 📂 Project Structure

```
ai-study-agent/
├── backend/
│   ├── main.py             # FastAPI REST endpoints & static server
│   ├── parsers.py          # Multi-format document parser & semantic chunker
│   ├── rag_engine.py       # Qdrant client & Gemini embeddings integration
│   ├── study_agent.py      # Core quiz, summary, explainer, & revision logic
│   ├── tracker.py          # SQLite score tracker & weak-topic analyzer
│   └── study_tracker.db    # SQLite database file
├── n8n_workflows/
│   └── ai_study_agent_workflow.json  # Importable n8n workflow definition
├── sample_data/
│   └── Agile_Product_Management.md   # Pre-indexed Product Management study notes
├── web_dashboard/
│   ├── index.html          # Interactive dark-mode glassmorphic dashboard
│   ├── style.css           # Premium HSL styling, gradients, and 3D transforms
│   └── app.js              # Client-side reactivity and API integrations
├── uploads/                # Directory for user-uploaded documents
├── start.ps1               # One-click startup script for PowerShell
└── README.md               # Documentation and reference guide
```

---

## 🧪 Example Walkthrough (Product Management Notes)

1. **Pre-indexed Materials:** The agent comes pre-loaded with `sample_data/Agile_Product_Management.md` covering the Scrum Framework, Sprints, Roles, ceremonies, and artifacts.
2. **Taking a Quiz:**
   - **Question:** *What is a Sprint in the Scrum framework?*
   - **Option A:** A long-term 5-year business strategy
   - **Option B:** A fixed timeboxed period (typically 1-4 weeks) in which a team completes planned tasks and delivers a shippable increment
   - **Option C:** A database synchronization cycle
   - **Option D:** A customer acquisition and marketing campaign
3. **Evaluating Answer:**
   - User selects **B**.
   - Agent responds:
     > ✅ **CORRECT!**
     > In Scrum, a Sprint is a fixed timeboxed event (usually 1-4 weeks) where a scrum team builds a working increment.
     > 📖 **Grounding Source:** `Agile_Product_Management.md (Chapter 2: The Scrum Framework)`
4. **Weak Area Revision:**
   - If a student answers incorrectly, accuracy on that topic drops below 70%.
   - Triggering `/revise` highlights the exact questions failed, retrieves the relevant study notes, and generates a focused 15-minute review roadmap.
