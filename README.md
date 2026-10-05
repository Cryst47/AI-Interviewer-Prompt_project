# AI Mock Interview & Dynamic Interview Evaluator
> **Project #4**: Applied Prompt Engineering & 3-Phase Multimodal Assessment Platform  
> **Key Concepts**: Role Prompting, 3-Phase Interview Pipeline, Evaluation Rubrics, Resume Ingestion (PDF/DOCX), Direct Speech-to-Speech Mode, Structured JSON Schemas, Context Engineering, and Guardrails.

---

## 👥 Project Team & Governance
- **Annimesh Sasmal**: *Lead Prompt Engineer & LLM Pipeline Architect* (Multi-persona role prompting, 4-vector STAR evaluation rubrics, JSON schema validation, and guardrails).
- **Swapnajit Sahoo**: *Backend Systems & API Integration Lead* (Flask RESTful microservice backend, session memory store, hybrid GPT-4o / heuristic fallback engine, and 30-day roadmap synthesis).
- **Payal Nanda**: *Frontend & Multimodal Experience Engineer* (Glassmorphism design system, Web Speech API STT/TTS, live closed caption streaming HUD, and presentation viewer).

---

## 🚀 3-Phase Structured Technical Interview Pipeline

1. 🚀 **Phase 1: Resume Verification & Project Deep-Dive**
   - Automatically ingests `.pdf`, `.docx`, or `.txt` resumes.
   - Extracts tech stack keywords (e.g. `Python`, `Docker`, `Kafka`, `PostgreSQL`) and past project claims.
   - Interrogates candidate on specific architectural choices, trade-offs, and bottleneck resolutions from their past experience.

2. ⚙️ **Phase 2: Target Job Description & Domain Technical Rigor**
   - Focuses on deep architectural problem solving, algorithm complexity, system design, and role-specific requirements.

3. 🎯 **Phase 3: HR, Cultural Fit & 5-Year Career Vision**
   - Evaluates behavioral leadership, team conflict resolution, and classic HR inquiries (e.g. *"Where do you see yourself in 5 years?", "What type of culture enables your best work?"*).

---

## 🎙️ Direct Speech-to-Speech Mode & Live Closed Captions
- **Conversational Voice Interview**: Natural Text-to-Speech (TTS) audio questioning with automated Speech-to-Text (STT) mic listening upon completion of question audio.
- **Real-Time Live Closed Captions**: Word-by-word streaming caption bar displays both Interviewer speech and Candidate spoken answers in real time.

---

## ⚡ Core Prompt Engineering Concepts Demonstrated

| Concept | Implementation in Codebase |
| :--- | :--- |
| **Role Prompting & Personas** | Configures distinct interviewer personas (`Alex - Senior Tech Lead`, `Elena - Supportive Mentor`, `Marcus - Demanding Executive`, `Sarah - Culture & HR Director`) with unique behavioral and technical constraints in [`prompts.py`](file:///s:/sem%207/PromptGPT/project/prompts.py). |
| **3-Phase Context Routing** | Dynamically routes context and difficulty across Resume Deep-Dive, Domain Architecture, and HR 5-Year Vision rounds. |
| **Evaluation Prompts & Rubrics** | Decouples assessment into 4 orthogonal vectors: **Technical Depth & Accuracy (35%)**, **STAR Method & Delivery (25%)**, **Communication & Clarity (20%)**, and **Confidence & Alignment (20%)** with mandatory quote grounding. |
| **Strict Structured JSON Output** | Enforces deterministic schema matching across question generation, instant turn feedback, and final hiring dossiers to ensure reliable UI rendering. |

---

## 🛠️ Quick Start & Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Open in Browser
- **Web App UI**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Interactive Presentation Deck (7 Slides)**: [http://127.0.0.1:5000/presentation](http://127.0.0.1:5000/presentation)
- **Download PPTX Presentation**: [http://127.0.0.1:5000/download-ppt](http://127.0.0.1:5000/download-ppt)
