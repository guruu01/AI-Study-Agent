let currentQuiz = null;
let currentFlashcards = [];
let currentFlashcardIndex = 0;
const currentUserId = "masai_student_1";

document.addEventListener("DOMContentLoaded", () => {
    loadHealthAndStats();
    loadTopics();
    loadNewQuiz();
    initDropzone();
});

// Tab Switcher
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(`tab-${tabId}`);
    const targetBtn = document.getElementById(`tab-btn-${tabId}`);
    if (targetTab) targetTab.classList.add("active");
    if (targetBtn) targetBtn.classList.add("active");

    if (tabId === "flashcards") loadFlashcards();
    if (tabId === "revise") loadRevisionData();
}

// Health & Stats
async function loadHealthAndStats() {
    try {
        const statsRes = await fetch(`/api/progress?user_id=${currentUserId}`);
        const stats = await statsRes.json();
        
        document.getElementById("stat-total-quizzes").innerText = stats.total_quizzes || 0;
        document.getElementById("stat-accuracy").innerText = `${stats.accuracy_pct || 0}%`;

        // Check weak topics
        const weakCount = (stats.topic_breakdown || []).filter(t => t.accuracy < 70).length;
        document.getElementById("stat-weak-count").innerText = weakCount;
    } catch (e) {
        console.error("Stats loading error:", e);
    }
}

// Load Topics
async function loadTopics() {
    try {
        const res = await fetch("/api/topics");
        const topics = await res.json();
        document.getElementById("stat-topics-count").innerText = topics.length;

        const selectQuiz = document.getElementById("select-quiz-topic");
        const selectFlashcard = document.getElementById("select-flashcard-topic");
        const topicList = document.getElementById("topic-list");

        selectQuiz.innerHTML = '<option value="">🎯 Auto-Pick Topic</option>';
        selectFlashcard.innerHTML = '';
        topicList.innerHTML = '';

        topics.forEach(t => {
            const shortTitle = t.topic.length > 25 ? t.topic.slice(0, 23) + '...' : t.topic;
            // Select dropdown options
            const opt1 = document.createElement("option");
            opt1.value = t.topic;
            opt1.innerText = shortTitle;
            opt1.title = t.topic;
            selectQuiz.appendChild(opt1);

            const opt2 = document.createElement("option");
            opt2.value = t.topic;
            opt2.innerText = shortTitle;
            opt2.title = t.topic;
            selectFlashcard.appendChild(opt2);


            // Vault list card
            const item = document.createElement("div");
            item.className = "topic-item";
            item.innerHTML = `
                <div>
                    <div class="topic-name">📌 ${t.topic}</div>
                    <div class="topic-meta">Sources: ${t.files.join(", ")}</div>
                </div>
                <span class="badge">${t.chunk_count} chunks indexed</span>
            `;
            topicList.appendChild(item);
        });
    } catch (e) {
        console.error("Error loading topics:", e);
    }
}

// QUIZ LOGIC
async function loadNewQuiz() {
    const feedbackBox = document.getElementById("feedback-box");
    feedbackBox.classList.add("hidden");

    const topicSelect = document.getElementById("select-quiz-topic").value;
    const stem = document.getElementById("question-stem");
    const optionsGrid = document.getElementById("options-grid");
    stem.innerText = "⚡ Formulating grounded question from your study materials...";
    optionsGrid.innerHTML = "";

    try {
        const res = await fetch("/api/quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUserId, topic: topicSelect || null })
        });
        currentQuiz = await res.json();

        document.getElementById("quiz-topic-badge").innerText = `Topic: ${currentQuiz.topic}`;
        stem.innerText = currentQuiz.question;

        // Render options A, B, C, D
        const letters = ["A", "B", "C", "D"];
        letters.forEach(letter => {
            const text = currentQuiz.options[letter];
            if (!text) return;

            const btn = document.createElement("button");
            btn.className = "option-btn";
            btn.id = `option-btn-${letter}`;
            btn.onclick = () => submitAnswer(letter);
            btn.innerHTML = `
                <div class="option-letter">${letter}</div>
                <div class="option-text">${text}</div>
            `;
            optionsGrid.appendChild(btn);
        });
    } catch (e) {
        stem.innerText = "Error loading question. Please check backend connection.";
    }
}

async function submitAnswer(selectedLetter) {
    if (!currentQuiz) return;

    // Disable all options
    document.querySelectorAll(".option-btn").forEach(b => b.disabled = true);

    try {
        const res = await fetch("/api/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                quiz_id: currentQuiz.quiz_id,
                user_id: currentUserId,
                selected_option: selectedLetter
            })
        });
        const evalResult = await res.json();

        // Highlight options
        const selectedBtn = document.getElementById(`option-btn-${selectedLetter}`);
        const correctBtn = document.getElementById(`option-btn-${evalResult.correct_option}`);

        if (evalResult.is_correct) {
            selectedBtn.classList.add("correct");
        } else {
            selectedBtn.classList.add("incorrect");
            if (correctBtn) correctBtn.classList.add("correct");
        }

        // Show feedback box
        const feedbackBox = document.getElementById("feedback-box");
        const feedbackBadge = document.getElementById("feedback-badge");
        const citationBadge = document.getElementById("citation-badge");
        const explanationText = document.getElementById("feedback-explanation");

        feedbackBadge.className = `feedback-badge ${evalResult.is_correct ? 'correct' : 'incorrect'}`;
        feedbackBadge.innerText = evalResult.is_correct ? "✅ Correct! Well done." : `❌ Incorrect! Correct option was ${evalResult.correct_option}`;

        citationBadge.innerText = `📖 Grounded in: ${evalResult.source_citation || "Study Notes"}`;
        explanationText.innerText = evalResult.explanation;

        feedbackBox.classList.remove("hidden");
        loadHealthAndStats();
    } catch (e) {
        console.error("Evaluation error:", e);
    }
}

// DRAG & DROP UPLOAD
function initDropzone() {
    const dropzone = document.getElementById("dropzone");
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "#6366f1";
            dropzone.style.background = "rgba(99, 102, 241, 0.15)";
        }, false);
    });
    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "rgba(99, 102, 241, 0.35)";
            dropzone.style.background = "rgba(99, 102, 241, 0.03)";
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) uploadFile(files[0]);
    });
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) uploadFile(file);
}

async function uploadFile(file) {
    const progressContainer = document.getElementById("upload-progress-container");
    const progressFill = document.getElementById("upload-progress-fill");
    const statusText = document.getElementById("upload-status-text");

    progressContainer.classList.remove("hidden");
    progressFill.style.width = "40%";
    statusText.innerText = `Ingesting ${file.name}... parsing chunks`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/ingest", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        progressFill.style.width = "100%";
        statusText.innerText = `✅ Ingested ${data.chunks_indexed} chunks! Topics: ${data.detected_topics.join(", ")}`;
        
        setTimeout(() => {
            loadTopics();
            loadHealthAndStats();
            progressContainer.classList.add("hidden");
        }, 2000);
    } catch (e) {
        statusText.innerText = "❌ Ingestion error. Check format.";
    }
}

async function handleTextIngest() {
    const title = document.getElementById("paste-title").value.trim() || "Study Note";
    const text = document.getElementById("paste-content").value.trim();
    if (!text) return alert("Please enter note text");

    const res = await fetch("/api/ingest/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, text })
    });
    const data = await res.json();
    alert(`✅ Ingested note with ${data.chunks_indexed} chunks!`);
    document.getElementById("paste-title").value = "";
    document.getElementById("paste-content").value = "";
    loadTopics();
}

// EXPLAINER & SUMMARIZER
async function explainConcept() {
    const concept = document.getElementById("input-concept").value.trim();
    if (!concept) return alert("Please type a concept to explain.");

    const resultBox = document.getElementById("explain-result");
    const badge = document.getElementById("explain-badge");
    const sources = document.getElementById("explain-sources");
    const output = document.getElementById("explain-output");

    resultBox.classList.remove("hidden");
    badge.innerText = `Explaining: ${concept}`;
    output.innerHTML = "<em>Retrieving study notes and formulating ELI5 analogy...</em>";

    try {
        const res = await fetch("/api/explain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ concept })
        });
        const data = await res.json();
        sources.innerText = `Sources Cited: ${data.sources.join(", ")}`;
        output.innerText = data.explanation;
    } catch (e) {
        output.innerText = "Error explaining concept.";
    }
}

async function summarizeChapter() {
    const topic = document.getElementById("input-concept").value.trim() || "Agile Methodology";
    const resultBox = document.getElementById("explain-result");
    const badge = document.getElementById("explain-badge");
    const sources = document.getElementById("explain-sources");
    const output = document.getElementById("explain-output");

    resultBox.classList.remove("hidden");
    badge.innerText = `Summary: ${topic}`;
    output.innerHTML = "<em>Synthesizing chapter summary from your study documents...</em>";

    try {
        const res = await fetch("/api/summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic_or_chapter: topic })
        });
        const data = await res.json();
        sources.innerText = `Sources Cited: ${data.sources.join(", ")}`;
        output.innerText = data.summary;
    } catch (e) {
        output.innerText = "Error generating summary.";
    }
}

// 3D FLASHCARDS
async function loadFlashcards() {
    const topic = document.getElementById("select-flashcard-topic").value || "Agile Methodology";
    try {
        const res = await fetch("/api/flashcards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic, count: 5 })
        });
        const data = await res.json();
        currentFlashcards = data.flashcards || [];
        currentFlashcardIndex = 0;
        renderFlashcard();
    } catch (e) {
        console.error("Flashcards error:", e);
    }
}

function renderFlashcard() {
    if (!currentFlashcards.length) return;
    const card = currentFlashcards[currentFlashcardIndex];
    document.getElementById("flashcard-card").classList.remove("is-flipped");
    document.getElementById("card-front-text").innerText = card.front;
    document.getElementById("card-back-text").innerText = card.back;
    document.getElementById("card-takeaway-text").innerText = `💡 ${card.key_takeaway || card.source || "High-yield concept"}`;
    document.getElementById("flashcard-index").innerText = `Card ${currentFlashcardIndex + 1} of ${currentFlashcards.length}`;
}

function flipCard() {
    document.getElementById("flashcard-card").classList.toggle("is-flipped");
}

function nextFlashcard() {
    if (currentFlashcardIndex < currentFlashcards.length - 1) {
        currentFlashcardIndex++;
        renderFlashcard();
    }
}

function prevFlashcard() {
    if (currentFlashcardIndex > 0) {
        currentFlashcardIndex--;
        renderFlashcard();
    }
}

// REVISION ROADMAP & MASTERY
async function loadRevisionData() {
    try {
        const statsRes = await fetch(`/api/progress?user_id=${currentUserId}`);
        const stats = await statsRes.json();
        const container = document.getElementById("mastery-bars-list");
        container.innerHTML = "";

        if (!stats.topic_breakdown || stats.topic_breakdown.length === 0) {
            container.innerHTML = "<p class='placeholder-text'>No quizzes completed yet. Take a quiz to populate mastery breakdown!</p>";
            return;
        }

        stats.topic_breakdown.forEach(t => {
            const colorClass = t.accuracy >= 80 ? 'bar-green' : (t.accuracy >= 60 ? 'bar-yellow' : 'bar-red');
            const item = document.createElement("div");
            item.className = "mastery-item";
            item.innerHTML = `
                <div class="mastery-header">
                    <span class="mastery-topic">${t.topic}</span>
                    <span class="mastery-pct">${t.accuracy}% (${t.correct}/${t.attempts} correct) — <strong>${t.status}</strong></span>
                </div>
                <div class="mastery-bar-bg">
                    <div class="mastery-bar-fill ${colorClass}" style="width: ${Math.max(t.accuracy, 5)}%"></div>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (e) {
        console.error("Revision loading error:", e);
    }
}

async function generateRevisionRoadmap() {
    const output = document.getElementById("revision-plan-output");
    output.innerHTML = "<em>Analyzing weak concepts and synthesizing targeted 15-minute revision plan...</em>";

    try {
        const res = await fetch(`/api/revise?user_id=${currentUserId}`);
        const data = await res.json();
        if (data.status === "all_good") {
            output.innerText = data.message;
        } else {
            output.innerText = data.revision_plan;
        }
    } catch (e) {
        output.innerText = "Error generating revision plan.";
    }
}
