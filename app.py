import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from ai_engine import InterviewEngine
from resume_parser import extract_text_from_file
from prompts import (
    SYSTEM_INTERVIEWER_PROMPT,
    INTERVIEWER_FEEDBACK_PROMPT,
    FINAL_EVALUATION_REPORT_PROMPT,
    PERSONA_DESCRIPTIONS
)

app = Flask(__name__)
CORS(app)

# In-memory session store for active mock interviews
SESSIONS = {}

engine = InterviewEngine()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/presentation")
def presentation():
    return render_template("presentation.html")

@app.route("/download-ppt")
def download_ppt():
    ppt_path = os.path.join(os.path.dirname(__file__), "AI_Mock_Interview_Deck.pptx")
    if not os.path.exists(ppt_path):
        ppt_path = os.path.join(os.path.dirname(__file__), "AI_Mock_Interview_Presentation.pptx")
    
    if not os.path.exists(ppt_path):
        try:
            import generate_ppt
            ppt_path = generate_ppt.create_presentation()
        except Exception as e:
            print("Error generating PPT:", e)
    
    if os.path.exists(ppt_path):
        return send_file(
            ppt_path,
            as_attachment=True,
            download_name="AI_Mock_Interview_Presentation.pptx",
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    return jsonify({"error": "Presentation file not found."}), 404

@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    """Extracts text, detected skills, and summary from uploaded PDF / DOCX / TXT."""
    if "resume_file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["resume_file"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    result = extract_text_from_file(file, file.filename)
    if "error" in result and result.get("error"):
        return jsonify({"status": "error", "message": result["error"]}), 400

    return jsonify({
        "status": "success",
        "filename": result.get("filename"),
        "text": result.get("text"),
        "skills": result.get("skills", []),
        "word_count": result.get("word_count", 0)
    })

@app.route("/api/start-session", methods=["POST"])
def start_session():
    data = request.get_json() or {}
    role = data.get("role", "Full Stack Software Engineer")
    experience_level = data.get("experience_level", "Mid-Level (3-5 Years)")
    persona_key = data.get("persona", "tech_lead")
    interview_type = data.get("interview_type", "Technical & System Architecture")
    total_questions = int(data.get("total_questions", 4))
    resume_context = data.get("resume_context", "")
    api_key = data.get("api_key", "")

    # Configure engine if API key supplied
    session_engine = InterviewEngine(openai_api_key=api_key) if api_key else engine

    session_id = str(uuid.uuid4())
    all_questions = session_engine.generate_all_questions(
        role=role,
        experience_level=experience_level,
        persona_key=persona_key,
        interview_type=interview_type,
        resume_context=resume_context,
        total_questions=total_questions
    )
    first_question = all_questions[0] if all_questions else {}

    session_data = {
        "id": session_id,
        "role": role,
        "experience_level": experience_level,
        "persona_key": persona_key,
        "interview_type": interview_type,
        "total_questions": total_questions,
        "resume_context": resume_context,
        "api_key": api_key,
        "questions": all_questions,
        "current_question_num": 1,
        "current_question_data": first_question,
        "history": []
    }
    SESSIONS[session_id] = session_data

    return jsonify({
        "status": "success",
        "session_id": session_id,
        "questions": all_questions,
        "question": first_question,
        "current_question_num": 1,
        "total_questions": total_questions
    })

@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    candidate_answer = data.get("answer", "").strip()

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session ID."}), 400

    session = SESSIONS[session_id]
    current_q_data = session["current_question_data"]
    q_num = session["current_question_num"]
    total_q = session["total_questions"]

    session_engine = InterviewEngine(openai_api_key=session.get("api_key")) if session.get("api_key") else engine

    # Evaluate current answer
    phase_name = current_q_data.get("phase_name", "Technical")
    evaluation = session_engine.evaluate_answer(
        role=session["role"],
        experience_level=session["experience_level"],
        interview_type=session["interview_type"],
        question=current_q_data.get("question", ""),
        candidate_answer=candidate_answer,
        phase_name=phase_name,
        conversation_history=json.dumps(session["history"][-2:] if session["history"] else [])
    )

    # Store turn into session history
    turn_record = {
        "question_number": q_num,
        "phase_number": current_q_data.get("phase_number", 1),
        "phase_name": phase_name,
        "question": current_q_data.get("question"),
        "category": current_q_data.get("category"),
        "difficulty": current_q_data.get("difficulty"),
        "answer": candidate_answer,
        "evaluation": evaluation
    }
    session["history"].append(turn_record)

    is_completed = (q_num >= total_q)
    next_question = None

    if not is_completed:
        next_q_num = q_num + 1
        session["current_question_num"] = next_q_num
        if "questions" in session and next_q_num <= len(session["questions"]):
            next_question = session["questions"][next_q_num - 1]
        else:
            next_question = session_engine.generate_question(
                role=session["role"],
                experience_level=session["experience_level"],
                persona_key=session["persona_key"],
                interview_type=session["interview_type"],
                resume_context=session["resume_context"],
                question_num=next_q_num,
                total_questions=total_q,
                history=session["history"]
            )
        session["current_question_data"] = next_question

    return jsonify({
        "status": "success",
        "evaluation": evaluation,
        "is_completed": is_completed,
        "next_question": next_question,
        "current_question_num": session["current_question_num"],
        "total_questions": total_q
    })

@app.route("/api/final-report", methods=["POST"])
def final_report():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid session ID."}), 400

    session = SESSIONS[session_id]
    session_engine = InterviewEngine(openai_api_key=session.get("api_key")) if session.get("api_key") else engine

    report = session_engine.generate_final_report(
        role=session["role"],
        experience_level=session["experience_level"],
        session_data=session
    )

    return jsonify({
        "status": "success",
        "report": report,
        "session_summary": {
            "role": session["role"],
            "experience_level": session["experience_level"],
            "interview_type": session["interview_type"],
            "rounds_completed": len(session["history"]),
            "history": session["history"]
        }
    })

@app.route("/api/prompts", methods=["GET"])
def get_prompts():
    """Returns the prompt engineering blueprints for transparent evaluation showcase."""
    return jsonify({
        "system_interviewer_prompt": SYSTEM_INTERVIEWER_PROMPT,
        "interviewer_feedback_prompt": INTERVIEWER_FEEDBACK_PROMPT,
        "final_evaluation_report_prompt": FINAL_EVALUATION_REPORT_PROMPT,
        "persona_descriptions": PERSONA_DESCRIPTIONS
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
