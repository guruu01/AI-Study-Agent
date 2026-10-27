import os
import json
import uuid
import re
import random
from typing import Dict, Any, List, Optional
from backend.rag_engine import RAGEngine
from backend.tracker import StudyTracker

QUESTION_BANK = [
    {
        "topic": "What is a Sprint?",
        "question": "What is the defining characteristic of a Sprint in the Scrum framework?",
        "correct": "A fixed timeboxed period (typically 1 to 4 weeks) where a team works to complete planned tasks and deliver a potentially shippable increment",
        "distractors": [
            "A flexible 6-month product release milestone that expands as scope grows",
            "A continuous delivery pipeline without timeboxes or planned task lists",
            "An annual performance review cycle for evaluating developers"
        ],
        "explanation": "In Scrum, a Sprint is a fixed timebox of 1 to 4 weeks during which the team produces a working product increment. Sprints have consistent durations, and sprint goals are protected from mid-sprint disruption.",
        "grounding_source": "Agile_Product_Management.md (Chapter 2: The Scrum Framework)"
    },
    {
        "topic": "Scrum Roles:",
        "question": "What is the primary responsibility of the Product Owner in Scrum?",
        "correct": "Defining the product vision, managing the Product Backlog, and prioritizing features based on business value",
        "distractors": [
            "Coaching the team on Scrum ceremonies and removing daily blockers",
            "Writing production code, unit tests, and designing database schemas",
            "Managing developer salaries, clock-in times, and annual bonuses"
        ],
        "explanation": "The Product Owner is the single individual responsible for maximizing the value of the product and managing the Product Backlog. Coaching and removing blockers is the Scrum Master's role.",
        "grounding_source": "Agile_Product_Management.md (Chapter 2: The Scrum Framework)"
    },
    {
        "topic": "Scrum Roles:",
        "question": "How is the Scrum Master defined in the Agile methodology?",
        "correct": "A servant-leader who coaches the team, facilitates ceremonies, and removes impediments (blockers)",
        "distractors": [
            "A hierarchical manager with command-and-control authority over software developers",
            "The corporate sales liaison who signs commercial contracts with customers",
            "A dedicated QA lead responsible for finding code defects before release"
        ],
        "explanation": "The Scrum Master is a servant-leader for the Scrum Team. They do not manage developers hierarchically; instead, they coach the team on Scrum theory and clear impediments hindering progress.",
        "grounding_source": "Agile_Product_Management.md (Chapter 2: The Scrum Framework)"
    },
    {
        "topic": "Scrum Roles:",
        "question": "In Scrum, who is responsible for deciding HOW to turn selected Product Backlog items into increments of value?",
        "correct": "The Developers (Development Team), because they are self-managing and cross-functional",
        "distractors": [
            "The Project Management Office (PMO) through daily task assignments",
            "External stakeholders and customers during the daily standup",
            "The Scrum Master acting as the technical software architect"
        ],
        "explanation": "No one tells the Developers how to turn Product Backlog items into Increments of value. They are self-managing, meaning they internally decide who does what, when, and how.",
        "grounding_source": "Agile_Product_Management.md (Chapter 2: The Scrum Framework)"
    },
    {
        "topic": "2. Daily Scrum (Standup)",
        "question": "Which three questions are addressed by each team member during the 15-minute Daily Scrum?",
        "correct": "What did I accomplish yesterday? What will I work on today? Are there any blockers in my way?",
        "distractors": [
            "What is the company profit? Who is falling behind schedule? When is the next demo?",
            "How many story points did I complete? Who caused the latest bug? What is my task rating?",
            "What is the 5-year strategy? Are stakeholders satisfied? When will our team expand?"
        ],
        "explanation": "The Daily Scrum is a 15-minute timeboxed daily meeting for the developers to synchronize activities, inspect progress toward the Sprint Goal, and identify blockers.",
        "grounding_source": "Agile_Product_Management.md (Chapter 3: Scrum Ceremonies)"
    },
    {
        "topic": "Chapter 3: Scrum Ceremonies (Events)",
        "question": "What is the key difference between a Sprint Review and a Sprint Retrospective?",
        "correct": "The Sprint Review inspects the shippable increment with stakeholders, while the Retrospective inspects team processes, relationships, and internal improvements",
        "distractors": [
            "The Review is for engineers only, while the Retrospective is for external customers",
            "The Review plans the next sprint, while the Retrospective estimates story points",
            "There is no difference; they are duplicate terms for the same event"
        ],
        "explanation": "Sprint Review focuses on the product (demonstrating working software to stakeholders and getting feedback). Sprint Retrospective focuses on the team itself (inspecting people, relationships, processes, and tools).",
        "grounding_source": "Agile_Product_Management.md (Chapter 3: Scrum Ceremonies)"
    },
    {
        "topic": "Chapter 3: Scrum Ceremonies (Events)",
        "question": "What is the primary output and purpose of Sprint Planning?",
        "correct": "To establish a clear Sprint Goal and determine which Product Backlog items the team commits to deliver in the Sprint Backlog",
        "distractors": [
            "To negotiate developer salaries and assign individual daily performance scores",
            "To complete all testing and deployment for the entire year's release roadmap",
            "To write the complete marketing press release and commercial invoice"
        ],
        "explanation": "Sprint Planning initiates the Sprint by laying out the work to be performed. The collaborative result is the Sprint Goal and the agreed Sprint Backlog.",
        "grounding_source": "Agile_Product_Management.md (Chapter 3: Scrum Ceremonies)"
    },
    {
        "topic": "Product Backlog vs. Sprint Backlog",
        "question": "How does the Sprint Backlog differ from the Product Backlog?",
        "correct": "The Product Backlog is the master emergent list of all desired features, while the Sprint Backlog is the subset of items committed for the current Sprint",
        "distractors": [
            "The Sprint Backlog belongs to marketing, while the Product Backlog belongs to customers",
            "The Sprint Backlog lasts for several years, while the Product Backlog changes hourly",
            "The Product Backlog only lists bugs, while the Sprint Backlog lists new features"
        ],
        "explanation": "The Product Backlog is the emergent, ordered single source of requirements for any product changes. The Sprint Backlog is the set of items selected for execution in the current sprint, plus the delivery plan.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "Definition of Done (DoD)",
        "question": "In Scrum, what is the crucial distinction between the 'Definition of Done' (DoD) and 'Acceptance Criteria'?",
        "correct": "DoD applies universally across all product backlog items to guarantee quality standards, while Acceptance Criteria are specific to an individual user story",
        "distractors": [
            "DoD is written by the customer, while Acceptance Criteria are written by the CEO",
            "DoD only applies to bug fixes, while Acceptance Criteria only apply to greenfield features",
            "There is no distinction; both phrases refer to unit test code coverage"
        ],
        "explanation": "The Definition of Done is a shared formal definition of quality that every product backlog item must satisfy to become a shippable increment. In contrast, Acceptance Criteria define unique scenario requirements specific to an individual user story.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "User Stories & The INVEST Criteria",
        "question": "In the INVEST framework for quality User Stories, what does the letter 'I' stand for?",
        "correct": "Independent (the story can be developed and delivered without tight coupling to others)",
        "distractors": [
            "Immediate (must be completed within 24 hours)",
            "Immutable (cannot be changed once written)",
            "Intricate (contains complex technical algorithms)"
        ],
        "explanation": "In the INVEST acronym (Independent, Negotiable, Valuable, Estimable, Small, Testable), 'I' stands for Independent. Avoiding tight coupling makes planning, prioritization, and release independent.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "User Stories & The INVEST Criteria",
        "question": "In the INVEST criteria, why must a User Story be 'Negotiable'?",
        "correct": "Because it is an invitation for conversation between the Product Owner and developers, not a rigid specification",
        "distractors": [
            "Because the price of the software can be bargained with customers",
            "Because team members can choose to skip testing if they disagree",
            "Because it allows developers to rewrite the feature without Product Owner approval"
        ],
        "explanation": "A user story is not a rigid contract. It is negotiable because the team and the PO collaborate to discuss implementation details and refine acceptance criteria as work progresses.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "Estimation & Velocity",
        "question": "What are Story Points primarily used for by Agile teams?",
        "correct": "To relatively estimate the effort, complexity, and uncertainty of a user story, rather than tracking exact calendar hours",
        "distractors": [
            "To calculate developer hourly bonuses and salary deductions",
            "To measure the exact number of lines of code written",
            "To calculate the retail dollar price of a software feature"
        ],
        "explanation": "Story Points represent relative size and complexity. Teams use them to estimate effort without getting bogged down in calendar hours, helping calculate team Velocity across sprints.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "Estimation & Velocity",
        "question": "What is the primary function of a Sprint Burndown Chart?",
        "correct": "To visually represent work remaining versus time, showing if the team is on track to achieve the Sprint Goal",
        "distractors": [
            "To show individual developer clock-in and clock-out times",
            "To track server cloud compute costs per day",
            "To log customer support ticket resolution times"
        ],
        "explanation": "A Burndown Chart plots remaining work (story points or tasks) on the Y-axis against time (sprint days) on the X-axis. A downward trend toward zero shows the sprint is progressing on schedule.",
        "grounding_source": "Agile_Product_Management.md (Chapter 4: Agile Artifacts and Estimation)"
    },
    {
        "topic": "Chapter 5: Scrum vs. Kanban",
        "question": "What is a major structural difference between Scrum and Kanban?",
        "correct": "Scrum operates on fixed timeboxed sprints with prescribed roles, whereas Kanban operates on continuous flow with WIP limits and no prescribed roles",
        "distractors": [
            "Scrum uses sticky notes while Kanban only uses spreadsheets",
            "Kanban requires a Scrum Master while Scrum prohibits having one",
            "Scrum is only for hardware manufacturing, while Kanban is only for design"
        ],
        "explanation": "Scrum uses timeboxed sprints (1-4 weeks), prescribed roles (PO, Scrum Master, Dev Team), and ceremonies. Kanban has continuous delivery without fixed sprint boundaries, limiting Work In Progress (WIP) at each stage.",
        "grounding_source": "Agile_Product_Management.md (Chapter 5: Scrum vs. Kanban)"
    },
    {
        "topic": "The 4 Agile Values:",
        "question": "Which statement accurately represents one of the 4 Core Values of the Agile Manifesto?",
        "correct": "Responding to change over following a plan",
        "distractors": [
            "Comprehensive documentation over working software",
            "Contract negotiation over customer collaboration",
            "Processes and tools over individuals and interactions"
        ],
        "explanation": "The 4 Agile values are: Individuals and interactions over processes and tools; Working software over comprehensive documentation; Customer collaboration over contract negotiation; and Responding to change over following a plan.",
        "grounding_source": "Agile_Product_Management.md (Chapter 1: Introduction to Agile Methodology)"
    },
    {
        "topic": "The 4 Agile Values:",
        "question": "According to the Agile Manifesto, why is 'Customer collaboration over contract negotiation' emphasized?",
        "correct": "Because continuous feedback and shared understanding deliver more valuable products than rigid legal specifications",
        "distractors": [
            "Because contracts should be eliminated entirely from all commercial businesses",
            "Because customers should write all the code and database queries themselves",
            "Because development teams should never charge customers for changes in scope"
        ],
        "explanation": "Traditional project management relies on rigid upfront contracts that make changes difficult. Agile values ongoing collaboration with customers to discover true user needs and adjust the product iteratively.",
        "grounding_source": "Agile_Product_Management.md (Chapter 1: Introduction to Agile Methodology)"
    }
]

FLASHCARD_BANK = [
    {
        "topic": "Agile Methodology",
        "front": "What is a Sprint in Scrum?",
        "back": "A fixed timebox of 1 to 4 weeks during which the team builds a usable, potentially shippable product increment.",
        "key_takeaway": "Consistent duration, protected sprint goal, no mid-sprint scope changes.",
        "source": "Agile_Product_Management.md (Chapter 2)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What are the 3 core roles in Scrum?",
        "back": "1. Product Owner (owns backlog & maximizes value)\n2. Scrum Master (servant-leader & impediment remover)\n3. Developers (self-organizing, cross-functional builders).",
        "key_takeaway": "No traditional project managers or hierarchies on the Scrum Team.",
        "source": "Agile_Product_Management.md (Chapter 2)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What does the INVEST criteria stand for in User Stories?",
        "back": "Independent, Negotiable, Valuable, Estimable, Small, and Testable.",
        "key_takeaway": "Checklist to ensure user stories can be planned, built, and verified without dependencies.",
        "source": "Agile_Product_Management.md (Chapter 4)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What is the Definition of Done (DoD)?",
        "back": "A formal, shared standard of quality criteria that every Product Backlog item must satisfy before becoming a releasable increment.",
        "key_takeaway": "Universal across all backlog items (e.g., code reviewed, unit tested, passing CI/CD).",
        "source": "Agile_Product_Management.md (Chapter 4)"
    },
    {
        "topic": "Agile Methodology",
        "front": "How does Sprint Review differ from Sprint Retrospective?",
        "back": "Sprint Review demoes working product features to stakeholders for feedback; Sprint Retrospective focuses on internal team process and tool improvements.",
        "key_takeaway": "Review = Product inspection; Retrospective = People, process, and tools inspection.",
        "source": "Agile_Product_Management.md (Chapter 3)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What are the 3 questions asked during the Daily Scrum?",
        "back": "1. What did I achieve yesterday?\n2. What will I work on today?\n3. Are there any impediments or blockers in my way?",
        "key_takeaway": "15-minute timebox for developers to synchronize, not a status report to management.",
        "source": "Agile_Product_Management.md (Chapter 3)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What is Velocity in Agile estimation?",
        "back": "The average amount of story points a team completes and marks as Done during a single Sprint.",
        "key_takeaway": "Capacity metric used for forecasting releases, never for comparing different teams.",
        "source": "Agile_Product_Management.md (Chapter 4)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What is the difference between Product Backlog and Sprint Backlog?",
        "back": "Product Backlog is the master emergent list of all desired features; Sprint Backlog is the subset selected and planned for the active Sprint.",
        "key_takeaway": "Product Backlog is owned by the PO; Sprint Backlog is owned and managed by Developers.",
        "source": "Agile_Product_Management.md (Chapter 4)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What is a WIP Limit in Kanban?",
        "back": "Work-In-Progress limit: a maximum cap on the number of task cards allowed in any specific workflow column at one time.",
        "key_takeaway": "Stop starting, start finishing. WIP limits expose bottlenecks and smooth flow.",
        "source": "Agile_Product_Management.md (Chapter 5)"
    },
    {
        "topic": "Agile Methodology",
        "front": "What are the 4 Core Values of the Agile Manifesto?",
        "back": "1. Individuals & interactions over processes/tools\n2. Working software over documentation\n3. Customer collaboration over contract\n4. Responding to change over following a plan.",
        "key_takeaway": "While there is value in the items on the right, Agile values items on the left more.",
        "source": "Agile_Product_Management.md (Chapter 1)"
    }
]

class StudyAgent:
    def __init__(self, rag_engine: RAGEngine, tracker: StudyTracker, gemini_api_key: Optional[str] = None):
        self.rag = rag_engine
        self.tracker = tracker
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = "gemini-1.5-flash"

    def _call_gemini(self, prompt: str, system_instruction: str = "", temperature: float = 0.3) -> str:
        # 1. Groq Cloud API (Free Llama 3.3 70B - Blazing fast 500+ tok/s for 24/7 cloud hosting)
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_instruction or "You are an expert AI Study Agent helping students learn with high-retention active recall, grounded strictly in their own study materials."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=2048
                )
                return completion.choices[0].message.content
            except Exception as e:
                print(f"Groq Cloud API note: {e}")

        # 2. Try Gemini API if key is provided
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction or "You are an expert AI Study Agent helping students learn with high-retention active recall, grounded strictly in their own study materials."
                )
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": temperature}
                )
                return response.text
            except Exception as e:
                print(f"Gemini API generation error: {e}")

        # 3. Free with NO LIMITS: Local Ollama (llama3.1:8b) on GPU
        try:
            import requests
            full_prompt = f"System: {system_instruction}\n\n{prompt}" if system_instruction else prompt
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.1:8b",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature
                    }
                },
                timeout=30
            )
            if res.status_code == 200:
                text = res.json().get("response", "").strip()
                if text:
                    return text
        except Exception as e:
            print(f"Ollama local call note: {e}")

        # 4. Grounded deterministic fallback (if Ollama offline / no API key)
        return self._local_fallback_generation(prompt)

    def _get_bank_quiz(self, user_id: str, topic: Optional[str] = None, recent_questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Picks an unasked question from QUESTION_BANK, dynamically shuffles options A/B/C/D,
        and guarantees no repeat questions.
        """
        if recent_questions is None:
            recent_questions = self.tracker.get_recent_questions(user_id, limit=15)

        recent_set = set(q.strip().lower() for q in recent_questions if q)

        # Filter by topic if specified
        candidates = []
        if topic:
            t_clean = topic.strip().lower()
            candidates = [
                q for q in QUESTION_BANK 
                if t_clean in q["topic"].lower() or q["topic"].lower() in t_clean or t_clean in q["question"].lower()
            ]

        # If no specific matches or no topic given, use the full bank
        if not candidates:
            candidates = list(QUESTION_BANK)

        # Filter out questions that have been asked recently
        unasked = [q for q in candidates if q["question"].strip().lower() not in recent_set]

        # If all matching candidates were asked, search the entire question bank for unasked questions
        if not unasked:
            unasked = [q for q in QUESTION_BANK if q["question"].strip().lower() not in recent_set]

        # If all 16 questions in the bank were asked, pick any question that is not the most recent one
        if not unasked:
            last_q = recent_questions[0].strip().lower() if recent_questions else ""
            not_last = [q for q in QUESTION_BANK if q["question"].strip().lower() != last_q]
            selected = random.choice(not_last if not_last else QUESTION_BANK)
        else:
            selected = random.choice(unasked)

        # Dynamically shuffle options so the correct answer is randomly distributed among A, B, C, D
        all_opts = [selected["correct"]] + list(selected["distractors"])
        random.shuffle(all_opts)
        letters = ["A", "B", "C", "D"]
        options_dict = {letters[i]: all_opts[i] for i in range(4)}
        correct_letter = letters[all_opts.index(selected["correct"])]

        return {
            "topic": selected["topic"],
            "question": selected["question"],
            "options": options_dict,
            "correct_option": correct_letter,
            "explanation": selected["explanation"],
            "grounding_source": selected["grounding_source"]
        }

    def _local_fallback_generation(self, prompt: str) -> str:
        """Fallback grounded response parser when offline or testing without key."""
        # 1. Multiple Choice Question Fallback
        if "generate 1 high-yield multiple choice question" in prompt.lower():
            # Check if prompt contains specific topic context
            topic = None
            if 'for: "' in prompt:
                try:
                    topic = prompt.split('for: "')[1].split('"')[0]
                except Exception:
                    pass

            bank_quiz = self._get_bank_quiz(user_id="default_student", topic=topic)
            return json.dumps(bank_quiz)

        # 2. ELI5 Concept Explainer Fallback
        if "explain this concept using this clear 3-step format" in prompt.lower():
            concept = "Sprint"
            if 'explain \'' in prompt:
                try:
                    concept = prompt.split("explain '")[1].split("'")[0]
                except Exception:
                    pass

            return (
                f"🧒 **The Everyday Analogy (ELI5):**\n"
                f"Imagine you are building a giant LEGO castle. Instead of locking yourself in a room for months hoping it looks right, you build one small tower in a 1-week mini-mission ({concept}), show it to your friends for feedback, and then build the next piece!\n\n"
                f"💼 **Practical Real-World Application:**\n"
                f"On real product teams, {concept} keeps teams focused on delivering high-value working features frequently without getting overwhelmed or derailed by shifting goals.\n\n"
                f"📖 **From Your Study Notes:**\n"
                f"According to your uploaded notes: A fixed timeboxed period (typically 1 to 4 weeks) during which the team works to complete planned tasks and deliver a potentially shippable increment. Sprints have consistent durations, and sprint goals are protected from disruptive mid-cycle changes."
            )

        # 3. Chapter Summary Fallback
        if "create a structured, high-yield chapter summary" in prompt.lower():
            topic = "Agile & Scrum Framework"
            if 'for: "' in prompt:
                try:
                    topic = prompt.split('for: "')[1].split('"')[0]
                except Exception:
                    pass

            return (
                f"📌 **Executive Overview:**\n"
                f"{topic} is an iterative approach designed to deliver high customer value through small, consumable increments with rapid feedback cycles.\n\n"
                f"🔑 **Core Frameworks & Principles from Your Notes:**\n"
                f"• **4 Core Values:** Individuals & interactions over processes; Working software over documentation; Customer collaboration over contract negotiation; Responding to change over following a plan.\n"
                f"• **Key Roles:** Product Owner (vision & backlog), Scrum Master (servant-leader & impediment remover), Development Team (cross-functional builders).\n"
                f"• **Core Ceremonies:** Sprint Planning, Daily Scrum (15-min sync), Sprint Review (demo), Sprint Retrospective (continuous improvement).\n\n"
                f"⚠️ **Common Exam Pitfalls:**\n"
                f"Remember: Sprints have fixed consistent durations. Quality standards never decrease mid-sprint, and the Sprint Goal cannot be compromised.\n\n"
                f"*(💡 Note: Add your GEMINI_API_KEY via `/key <api_key>` to unlock dynamic Gemini 1.5 Flash synthesis for any custom question!)*"
            )

        # 4. Revision Roadmap Fallback
        if "targeted revision roadmap" in prompt.lower():
            return (
                f"🎯 **Targeted 15-Minute Revision Roadmap**\n\n"
                f"1. **Core Concept Review (5 mins):**\n"
                f"   • Re-read Chapter 2 in your notes on the *Scrum Framework* and *Sprint Lifecycle*.\n"
                f"   • Focus on the difference between the Product Backlog (the master list) and the Sprint Backlog (the commitment for the current sprint).\n\n"
                f"2. **Active Recall Trap Checks (5 mins):**\n"
                f"   • Why was Option A incorrect? Sprints are short timeboxes (1-4 weeks), NOT long multi-year plans.\n"
                f"   • Remember the INVEST criteria for user stories: Independent, Negotiable, Valuable, Estimable, Small, Testable.\n\n"
                f"3. **Self-Testing (5 mins):**\n"
                f"   • Run `/quiz` right here in Telegram to re-test yourself and boost your accuracy score above 70%!"
            )

        return "Study Agent is running. Connect your GEMINI_API_KEY via /key <your_key> for custom generation."

    def generate_quiz(self, user_id: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves grounded notes from Qdrant and generates an active-recall MCQ.
        Guarantees non-repeating questions across successive attempts.
        """
        recent_questions = self.tracker.get_recent_questions(user_id, limit=15)

        # Smart Topic Rotation if not explicitly chosen by the user
        if not topic:
            weak_topics = self.tracker.get_revision_topics(user_id)
            all_topics = self.rag.get_all_topics(user_id=user_id)
            
            # 65% chance to test a weak topic if user has any weak areas
            if weak_topics and random.random() < 0.65:
                topic = random.choice(weak_topics)["topic"]
            elif all_topics:
                # Rotate randomly among indexed topics for variety
                topic = random.choice(all_topics)["topic"]
            else:
                bank_topics = list(set(q["topic"] for q in QUESTION_BANK))
                topic = random.choice(bank_topics) if bank_topics else "Agile Methodology"

        # Check if an LLM is available (Groq Cloud, Gemini, or local Ollama)
        has_llm = bool(os.getenv("GROQ_API_KEY") or self.gemini_api_key)

        quiz_data = None

        if has_llm:
            # 1. Retrieve grounded study chunks scoped strictly to user's private vault
            chunks = self.rag.search(query=f"Core concepts, definitions, and rules about {topic}", user_id=user_id, topic_filter=topic, limit=3)
            context_text = "\n\n".join([f"--- Source: {c['filename']} (Topic: {c['topic']}) ---\n{c['text']}" for c in chunks])

            if not context_text.strip():
                context_text = f"Study Topic: {topic}. Essential concepts and principles."

            # Dynamic question angles
            angles = [
                "core definitions and specific purpose",
                "practical real-world team trade-offs and decision making",
                "roles, responsibilities, and authority boundaries",
                "common misconceptions, anti-patterns, and pitfalls to avoid",
                "comparing this concept with its alternatives or traditional methods"
            ]
            focus_angle = random.choice(angles)
            recent_str = "\n".join([f"- {q}" for q in recent_questions[:8]]) if recent_questions else "None yet."

            prompt = f"""
Based ONLY on the following study materials retrieved from the user's uploaded documents:
=============================
{context_text}
=============================

Generate 1 high-yield Multiple Choice Question (MCQ) testing active recall for: "{topic}".
FOCUS ANGLE: {focus_angle}

CRITICAL ANTI-REPETITION RULE:
The student has ALREADY recently answered the following questions:
{recent_str}
You MUST NOT repeat any of these questions or ask essentially the same question. Generate a fresh, unique question exploring a different facet.

REQUIREMENTS:
1. Ground the question strictly in the provided study materials. Do not invent facts outside of this context.
2. Provide exactly 4 options labeled A, B, C, D. One correct answer and 3 plausible distractors. Randomize which letter (A, B, C, or D) is the correct answer.
3. Provide a clear, thorough explanation explaining why the correct answer is right and why the other options are wrong.
4. Cite the exact file name and section in "grounding_source".

Respond in STRICT JSON format with this exact schema:
{{
  "topic": "{topic}",
  "question": "The question text",
  "options": {{
    "A": "Option text",
    "B": "Option text",
    "C": "Option text",
    "D": "Option text"
  }},
  "correct_option": "A|B|C|D",
  "explanation": "Detailed rationale breaking down the answer and distractors",
  "grounding_source": "Filename and section reference"
}}
"""
            response_text = self._call_gemini(prompt, temperature=0.7)
            try:
                match = re.search(r'\{.*\}', response_text, re.DOTALL)
                parsed = json.loads(match.group(0)) if match else json.loads(response_text)
                if parsed.get("question") and parsed.get("options") and len(parsed.get("options", {})) == 4:
                    # Verify question is not a repeat
                    if parsed.get("question", "").strip() not in recent_questions:
                        quiz_data = parsed
            except Exception:
                pass

        # If LLM unavailable or generated a repeat/invalid JSON, use the rich question bank
        if not quiz_data:
            quiz_data = self._get_bank_quiz(user_id=user_id, topic=topic, recent_questions=recent_questions)

        quiz_id = str(uuid.uuid4())[:8]
        quiz_data["quiz_id"] = quiz_id

        # Save active quiz in SQLite for Telegram callback validation and anti-repetition tracking
        self.tracker.save_active_quiz(
            quiz_id=quiz_id,
            user_id=user_id,
            topic=quiz_data.get("topic", topic),
            question=quiz_data.get("question", ""),
            options_json=json.dumps(quiz_data.get("options", {})),
            correct_option=quiz_data.get("correct_option", "A"),
            explanation=quiz_data.get("explanation", ""),
            source_citation=quiz_data.get("grounding_source", "")
        )

        return quiz_data

    def evaluate_answer(self, quiz_id: str, user_id: str, selected_option: str) -> Dict[str, Any]:
        """
        Validates user's answer, logs quiz result to SQLite, and returns detailed feedback with citation.
        """
        active = self.tracker.get_active_quiz(quiz_id)
        if not active:
            # Fallback if quiz expired or not found
            return {
                "status": "error",
                "message": "Quiz session expired. Use /quiz to start a new question!"
            }

        correct_letter = active["correct_option"].upper().strip()
        selected_raw = selected_option.strip()

        options = {}
        try:
            options = json.loads(active.get("options_json", "{}"))
        except Exception:
            pass

        correct_text = options.get(correct_letter, "").strip()

        # Check match by letter ('A' == 'A') OR by full text ('Scrum Master' == 'Scrum Master')
        is_correct = (
            selected_raw.upper() == correct_letter or
            (bool(correct_text) and selected_raw.lower() == correct_text.lower())
        )
        correct_option = correct_letter

        # Record result in database
        stats = self.tracker.record_quiz_result(
            user_id=user_id,
            topic=active["topic"],
            question=active["question"],
            selected_option=selected_option,
            correct_option=correct_option,
            is_correct=is_correct,
            source_doc=active["source_citation"]
        )

        return {
            "quiz_id": quiz_id,
            "topic": active["topic"],
            "question": active["question"],
            "selected_option": selected_option,
            "correct_option": correct_option,
            "is_correct": is_correct,
            "explanation": active["explanation"],
            "source_citation": active["source_citation"],
            "user_stats": stats
        }

    def summarize_chapter(self, topic_or_chapter: str, user_id: str = "default_student") -> Dict[str, Any]:
        """
        Retrieves relevant sections and generates a comprehensive chapter executive summary.
        Scoped strictly to user_id's private vault and common materials.
        """
        chunks = self.rag.search(query=f"Overview, principles, and chapters about {topic_or_chapter}", user_id=user_id, topic_filter=topic_or_chapter, limit=5)
        context = "\n\n".join([f"[{c['filename']}]:\n{c['text']}" for c in chunks])

        prompt = f"""
Using ONLY the following excerpts from the student's study materials:
=============================
{context}
=============================

Create a structured, high-yield Chapter Summary for: "{topic_or_chapter}".
Format with:
1. 📌 **Executive Overview** (2-3 sentences explaining core idea)
2. 🔑 **Core Frameworks & Key Concepts** (Bullet points with bold highlights)
3. ⚠️ **Common Exam Pitfalls / Things to Remember**
4. 📚 **Grounded Sources Cited** (Include file names and sections from notes)
"""
        summary_text = self._call_gemini(prompt)
        return {
            "topic": topic_or_chapter,
            "summary": summary_text,
            "sources": list(set(c["filename"] for c in chunks))
        }

    def explain_concept(self, concept: str, user_id: str = "default_student") -> Dict[str, Any]:
        """
        Explains difficult concept in simple language (ELI5 + Analogy + Note Reference).
        Scoped strictly to user_id's private vault and common materials.
        """
        chunks = self.rag.search(query=concept, user_id=user_id, limit=4)
        context = "\n\n".join([f"[{c['filename']}]:\n{c['text']}" for c in chunks])

        prompt = f"""
A student asked: "Explain '{concept}' in simple language".
Here is what their study materials say about it:
=============================
{context}
=============================

Explain this concept using this clear 3-step format:
1. 🧒 **The Everyday Analogy (ELI5)**: Explain it as if talking to a 10-year-old using a fun, vivid real-world analogy.
2. 💼 **Practical Application**: How is this actually used in real life / on the job?
3. 📖 **From Your Study Notes**: The formal definition and rules straight from their uploaded document, citing the specific source.
"""
        explanation_text = self._call_gemini(prompt)
        return {
            "concept": concept,
            "explanation": explanation_text,
            "sources": list(set(c["filename"] for c in chunks))
        }

    def _extract_flashcards_from_chunks(self, topic: str, chunks: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """Extracts flashcards from text chunks if LLM is offline."""
        cards = []
        for chunk in chunks:
            text = chunk.get("text", "")
            filename = chunk.get("filename", "Uploaded Notes")
            lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
            for line in lines:
                if ":" in line and len(cards) < count:
                    parts = line.split(":", 1)
                    term = parts[0].strip().strip("-*# ")
                    desc = parts[1].strip()
                    if 3 < len(term) < 60 and len(desc) > 15:
                        cards.append({
                            "topic": topic,
                            "front": f"What is {term}?",
                            "back": desc,
                            "key_takeaway": f"Core concept from {filename}.",
                            "source": filename
                        })
        return cards

    def _get_bank_flashcards(self, topic: Optional[str] = None, count: int = 5) -> Dict[str, Any]:
        """Returns a high-yield curated flashcard deck from FLASHCARD_BANK."""
        cards = list(FLASHCARD_BANK)
        if topic:
            topic_lower = topic.lower()
            matching = [c for c in cards if topic_lower in c.get("topic", "").lower() or topic_lower in c.get("front", "").lower()]
            if matching:
                cards = matching

        # Sample count cards or shuffle
        selected = random.sample(cards, min(count, len(cards))) if len(cards) >= count else cards
        return {
            "topic": topic or "Agile Methodology",
            "flashcards": selected
        }

    def generate_flashcards(self, topic: str, count: int = 5, user_id: str = "default_student") -> Dict[str, Any]:
        """
        Generates active-recall flashcards from user notes.
        Scoped strictly to user_id's private vault and common materials.
        """
        chunks = []
        try:
            chunks = self.rag.search(query=f"Definitions, formulas, key facts about {topic}", user_id=user_id, topic_filter=topic, limit=5)
        except Exception:
            pass

        has_llm = bool(os.getenv("GROQ_API_KEY") or self.gemini_api_key)
        if has_llm:
            try:
                context = "\n\n".join([f"[{c['filename']}]:\n{c['text']}" for c in chunks])

                prompt = f"""
Based on the student's study materials below:
=============================
{context}
=============================

Generate {count} active recall flashcards for "{topic}".
Respond in JSON format:
{{
  "topic": "{topic}",
  "flashcards": [
    {{
      "front": "Question or prompt testing active recall",
      "back": "Clear, concise definition or answer",
      "key_takeaway": "Memory hook or tip",
      "source": "Document reference"
    }}
  ]
}}
"""
                resp = self._call_gemini(prompt)
                if resp:
                    match = re.search(r'\{.*\}', resp, re.DOTALL)
                    data = json.loads(match.group(0)) if match else json.loads(resp)
                    if data.get("flashcards") and len(data["flashcards"]) >= 1:
                        return data
            except Exception as e:
                print(f"Dynamic flashcards note: {e}")

        # If LLM offline, attempt extraction from notes
        if chunks:
            extracted = self._extract_flashcards_from_chunks(topic, chunks, count=count)
            if len(extracted) >= count:
                return {"topic": topic, "flashcards": extracted}

        # High-yield bank fallback guaranteed to return count rich cards
        return self._get_bank_flashcards(topic=topic, count=count)

    def generate_revision_plan(self, user_id: str) -> Dict[str, Any]:
        """
        Identifies weak topics (<70% accuracy) and produces an actionable Revision Roadmap.
        """
        weak_topics = self.tracker.get_revision_topics(user_id)
        if not weak_topics:
            return {
                "status": "all_good",
                "message": "🎉 Great work! You have no weak topics below 70% accuracy. Take another quiz with /quiz to keep testing yourself!",
                "topics": []
            }

        # Gather notes for each weak topic
        revision_sections = []
        for wt in weak_topics:
            chunks = self.rag.search(query=f"Key definitions and mistakes in {wt['topic']}", topic_filter=wt["topic"], limit=2)
            notes_excerpt = "\n".join([c["text"][:300] + "..." for c in chunks])
            revision_sections.append({
                "topic": wt["topic"],
                "accuracy": wt["accuracy"],
                "attempts": wt["attempts"],
                "failed_questions": wt["failed_questions"],
                "notes_excerpt": notes_excerpt
            })

        prompt = f"""
You are the student's personal AI Study Coach.
The student has taken quizzes and struggled with the following topics:
{json.dumps(revision_sections, indent=2)}

Generate a focused, encouraging "Targeted Revision Roadmap" that:
1. Clearly states each topic that needs revision and why (their current accuracy %).
2. Clarifies the exact concepts they got wrong, explaining the underlying rule.
3. Provides a 15-minute Action Plan (step-by-step review actions).
4. Directs them to review specific sections in their notes.
"""
        plan_text = self._call_gemini(prompt)
        return {
            "status": "needs_revision",
            "weak_topics_count": len(weak_topics),
            "weak_topics": weak_topics,
            "revision_plan": plan_text
        }
