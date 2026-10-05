import os
import json
import re
import random
from resume_parser import extract_key_skills
from prompts import (
    SYSTEM_INTERVIEWER_PROMPT,
    INTERVIEWER_FEEDBACK_PROMPT,
    FINAL_EVALUATION_REPORT_PROMPT,
    PERSONA_DESCRIPTIONS
)

# Role-specific question bank organized by the 3 Phases
QUESTION_DATABASE = {
    "software_engineer": {
        "phase1_resume": [
            "Looking at your background and project experience on your resume, can you walk me through the most technically complex architectural decision you made in your recent project and what trade-offs were involved?",
            "In your past projects, what was the most difficult production bottleneck or race condition you personally diagnosed and resolved?",
            "Can you explain how you designed your data access layer, concurrency controls, and caching strategy in your flagship project?"
        ],
        "phase2_domain": [
            "How would you ensure idempotency, eventual consistency, and fault tolerance in a distributed microservices financial payment flow handling 10,000 req/sec?",
            "Explain how indexing works internally in relational databases (e.g. B-Trees) and how you diagnose an unindexed query bottleneck using EXPLAIN ANALYZE.",
            "How would you design a distributed rate limiter supporting multi-tier API clients with zero single point of failure?"
        ],
        "phase3_hr_vision": [
            "Where do you see your career heading in the future, both in terms of technical craftsmanship and leadership impact?",
            "Tell me about a time you strongly disagreed with a senior architect or tech lead's decision. How did you formulate your argument and reach alignment?",
            "What kind of engineering culture and team dynamics bring out your best work, and why does this position fit your professional aspirations?"
        ]
    },
    "full_stack": {
        "phase1_resume": [
            "From your resume, walk me through an end-to-end full stack feature you delivered from database schema design to responsive UI deployment.",
            "In your past projects, how did you handle client-side state management versus server-side caching to keep data consistent across sessions?",
            "Tell me about a high-traffic web application you deployed. How did you ensure smooth CI/CD deployments and zero-downtime database migrations?"
        ],
        "phase2_domain": [
            "Explain how the Critical Rendering Path works in modern browsers and how you optimize First Contentful Paint (FCP) and Cumulative Layout Shift (CLS).",
            "How would you architect a real-time collaborative document editing tool (similar to Google Docs) using WebSockets and CRDTs / Operational Transformation?",
            "What are the core security principles and defense-in-depth mechanisms you implement to guard against XSS, CSRF, and SQL Injection?"
        ],
        "phase3_hr_vision": [
            "How do you approach your professional growth—do you see yourself advancing towards Staff/Principal engineering or Technical Leadership?",
            "Describe a situation where shifting business priorities or tight deadlines forced you to take on technical debt. How did you manage stakeholder expectations?",
            "Why are you interested in this position specifically, and what makes you passionate about building user-facing software systems?"
        ]
    },
    "data_scientist": {
        "phase1_resume": [
            "Looking at your resume, you have deployed machine learning models into production. Walk me through your data pipeline, feature engineering, and model validation strategy.",
            "Tell me about a specific ML project on your resume where the initial model performed poorly. What diagnostic experiments did you conduct to improve it?",
            "How did you monitor data drift, concept drift, and prediction latency in the models you deployed in your previous experience?"
        ],
        "phase2_domain": [
            "Explain the mathematical foundation of Multi-Head Self-Attention in Transformers, and how computational complexity scales with sequence length.",
            "How do you formulate an A/B test sample size calculation, and how do you guard against p-hacking, peeking, and multiple testing anomalies?",
            "How would you design a low-latency recommendation engine serving 100M+ active users with candidate retrieval and neural reranking?"
        ],
        "phase3_hr_vision": [
            "Where do you see yourself contributing most in the rapidly evolving landscape of Applied AI and Data Science?",
            "Tell me about a time you had to explain complex machine learning predictions or statistical risk to non-technical business executives.",
            "What ethical considerations or fairness guidelines do you prioritize when deploying AI systems in production?"
        ]
    },
    "product_manager": {
        "phase1_resume": [
            "Looking at your product experience on your resume, walk me through a 0-to-1 product launch you led and how you defined its Minimum Viable Product (MVP).",
            "Tell me about a product feature on your resume that did not achieve its target KPI. What did you learn and how did you pivot?",
            "How did you manage cross-functional alignment between engineering, design, and executive stakeholders in your last project?"
        ],
        "phase2_domain": [
            "Imagine our core weekly active user retention dropped by 15% week-over-week. Walk me through your structured diagnostic framework.",
            "How would you price and monetize an enterprise AI copilot product while balancing customer adoption friction with long-term gross margins?",
            "Walk me through how you prioritize a backlog when executive leadership, sales, and end-users all have competing urgent requests."
        ],
        "phase3_hr_vision": [
            "What kind of product impact and leadership milestones do you aspire to achieve in your career?",
            "Describe a situation where you had to say 'No' to a high-priority request from an executive or major client. How did you communicate the rationale?",
            "What principles guide your leadership and empathy when working under intense quarterly release pressures?"
        ]
    }
}

class InterviewEngine:
    def __init__(self, openai_api_key=None, gemini_api_key=None):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

    def get_phase_info(self, question_num, total_questions):
        """Calculates the active interview phase based on progress (3, 6, or 9 rounds)."""
        per_phase = max(1, total_questions // 3)
        if question_num <= per_phase:
            return 1, "Phase 1: Resume Verification", "Deeply verify candidate's resume projects, claimed technologies, and architectural ownership."
        elif question_num <= per_phase * 2:
            return 2, "Phase 2: Technical Domain Rigor", "Deep technical architecture, systems design, trade-offs, and core job competencies."
        else:
            return 3, "Phase 3: HR, Leadership & Future Vision", "Behavioral leadership, team collaboration, handling conflict, and long-term career ambition."

    def generate_all_questions(self, role, experience_level, persona_key, interview_type, resume_context, total_questions):
        """Pre-generates the entire sequence of questions across all 3 phases for instant zero-latency transitions."""
        questions = []
        for q_num in range(1, total_questions + 1):
            q_data = self.generate_question(
                role=role,
                experience_level=experience_level,
                persona_key=persona_key,
                interview_type=interview_type,
                resume_context=resume_context,
                question_num=q_num,
                total_questions=total_questions,
                history=[]
            )
            questions.append(q_data)
        return questions

    def generate_question(self, role, experience_level, persona_key, interview_type, resume_context, question_num, total_questions, history=None):
        """Generates the next interview question strictly matching the active phase."""
        persona_desc = PERSONA_DESCRIPTIONS.get(persona_key, PERSONA_DESCRIPTIONS["tech_lead"])
        phase_num, phase_name, phase_focus = self.get_phase_info(question_num, total_questions)

        if question_num <= 2:
            difficulty = "Easy" if question_num == 1 else "Medium"
        elif question_num <= total_questions - 2:
            difficulty = "Medium"
        else:
            difficulty = "Hard"

        # Try OpenAI if available
        if self.openai_api_key and self.openai_api_key.strip():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                prompt = SYSTEM_INTERVIEWER_PROMPT.format(
                    role=role,
                    experience_level=experience_level,
                    persona_desc=persona_desc,
                    interview_type=interview_type,
                    resume_context=resume_context or "General software engineering background.",
                    question_num=question_num,
                    phase_number=phase_num,
                    phase_name=phase_name,
                    phase_focus=phase_focus,
                    difficulty=difficulty
                )
                
                messages = [{"role": "system", "content": prompt}]
                if history:
                    for item in history:
                        messages.append({"role": "assistant", "content": f"Question ({item.get('phase_name', '')}): {item.get('question')}"})
                        messages.append({"role": "user", "content": f"Answer: {item.get('answer')}"})
                messages.append({"role": "user", "content": f"Generate Question #{question_num} strictly for {phase_name}."})

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                data = json.loads(response.choices[0].message.content)
                data["phase_number"] = phase_num
                data["phase_name"] = phase_name
                if "ai_model_answer" not in data:
                    data["ai_model_answer"] = self._synthesize_model_answer(data.get("question", ""), role, phase_num, experience_level)
                return data
            except Exception as e:
                print(f"[OpenAI Gen Error]: {e}, falling back to intelligent offline engine.")

        # Fallback / Smart Heuristic LLM Simulator
        return self._smart_generate_question(role, experience_level, persona_key, interview_type, resume_context, question_num, total_questions, phase_num, phase_name, difficulty, history)


    def evaluate_answer(self, role, experience_level, interview_type, question, candidate_answer, phase_name="Technical", conversation_history=""):
        """Evaluates candidate response using structured prompt rubric."""
        if self.openai_api_key and self.openai_api_key.strip():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                prompt = INTERVIEWER_FEEDBACK_PROMPT.format(
                    role=role,
                    experience_level=experience_level,
                    interview_type=interview_type,
                    phase_name=phase_name,
                    question=question,
                    candidate_answer=candidate_answer,
                    conversation_history=conversation_history
                )
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a senior hiring committee chair. Output only valid JSON conforming to the requested schema."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.4
                )
                data = json.loads(response.choices[0].message.content)
                return data
            except Exception as e:
                print(f"[OpenAI Eval Error]: {e}, using smart heuristic evaluator.")

        return self._smart_evaluate_answer(role, question, candidate_answer, phase_name)

    def generate_final_report(self, role, experience_level, session_data):
        """Generates comprehensive final scorecard & 30-day mastery roadmap."""
        if self.openai_api_key and self.openai_api_key.strip():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                transcript_str = json.dumps(session_data.get("history", []), indent=2)
                prompt = FINAL_EVALUATION_REPORT_PROMPT.format(
                    role=role,
                    experience_level=experience_level,
                    total_questions=len(session_data.get("history", [])),
                    full_transcript=transcript_str
                )
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are the Hiring Committee Chair. Return only structured JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.5
                )
                data = json.loads(response.choices[0].message.content)
                return data
            except Exception as e:
                print(f"[OpenAI Final Report Error]: {e}, synthesizing dynamic offline report.")

        return self._smart_final_report(role, experience_level, session_data)

    # ---------------- SMART OFFLINE ENGINES ---------------- #

    def _smart_generate_question(self, role, experience_level, persona_key, interview_type, resume_context, question_num, total_questions, phase_num, phase_name, difficulty, history):
        role_key = "software_engineer"
        role_lower = role.lower()
        if "full" in role_lower or "web" in role_lower or "front" in role_lower:
            role_key = "full_stack"
        elif "data" in role_lower or "ai" in role_lower or "ml" in role_lower:
            role_key = "data_scientist"
        elif "product" in role_lower or "pm" in role_lower or "manager" in role_lower:
            role_key = "product_manager"

        role_db = QUESTION_DATABASE.get(role_key, QUESTION_DATABASE["software_engineer"])

        per_phase = max(1, total_questions // 3)
        phase_index = (question_num - 1) % per_phase

        if phase_num == 1:
            pool = role_db.get("phase1_resume", [])
            category = "Resume & Past Project Deep-Dive"
            note = f"Assessing factual depth and architectural ownership of projects listed on candidate's resume ({experience_level})."
            
            # Robust extraction of actual technical skills from resume (ignoring names/headings)
            detected_skills = extract_key_skills(resume_context) if resume_context else []
            
            if detected_skills and phase_index == 0:
                if len(detected_skills) >= 2:
                    top_tech = f"{detected_skills[0]} and {detected_skills[1]}"
                else:
                    top_tech = detected_skills[0]
                chosen_q = f"In reviewing your resume, I noticed significant project work involving {top_tech}. Could you walk me through the overall system architecture you implemented, the biggest bottleneck you encountered, and how you resolved it?"
            elif detected_skills and len(detected_skills) > 2 and phase_index == 1:
                top_tech = f"{detected_skills[2]}"
                chosen_q = f"Looking at your experience with {top_tech} on your resume, how did you handle data consistency, failure recovery, and testing in production?"
            elif resume_context and len(resume_context.strip()) > 30 and phase_index == 0:
                chosen_q = "In reviewing your resume, could you walk me through the most technically complex project you delivered, the architectural decisions you made, and how you ensured system resilience?"
            else:
                idx = phase_index % len(pool) if pool else 0
                chosen_q = pool[idx] if pool else "Can you walk me through the most technically complex project listed on your resume?"

        elif phase_num == 2:
            pool = role_db.get("phase2_domain", [])
            category = "Target Job Description & System Rigor"
            note = f"Evaluating system architecture, trade-off analysis, and algorithmic correctness for {role}."
            idx = phase_index % len(pool) if pool else 0
            chosen_q = pool[idx] if pool else f"How would you design a scalable, fault-tolerant backend system for {role}?"

        else:
            pool = role_db.get("phase3_hr_vision", [])
            category = "HR, Culture Fit & Leadership"
            note = "Inspecting long-term career ambition, emotional intelligence, and team leadership traits."
            idx = phase_index % len(pool) if pool else 0
            chosen_q = pool[idx] if pool else "Where do you see yourself contributing most in your future career, and what type of team culture empowers your highest potential?"

        model_ans = self._synthesize_model_answer(chosen_q, role, phase_num, experience_level)

        return {
            "question_number": question_num,
            "phase_number": phase_num,
            "phase_name": phase_name,
            "question": chosen_q,
            "category": category,
            "difficulty": difficulty,
            "expected_key_points": [
                f"Demonstrate structured reasoning for {phase_name}",
                "Clear trade-off analysis and quantifiable impact",
                "Concise delivery aligned with STAR principles"
            ],
            "interviewer_note": note,
            "ai_model_answer": model_ans
        }

    def _synthesize_model_answer(self, question, role, phase_num, experience_level):
        """Generates a high-scoring, STAR-formatted model response for candidate learning."""
        q_lower = question.lower()
        if phase_num == 1:
            return (
                "📍 Situation & Task: In my previous production initiative, I led the core service redesign for our high-throughput data and API layer handling over 8,500 requests/second.\n\n"
                "🛠️ Action: I transitioned our synchronous blocking calls to an asynchronous event-driven worker model using Redis caching, connection pooling, and resilient retry policies with exponential backoff.\n\n"
                "📊 Result & Reflection: We reduced p99 query latency by 45% (from 280ms to 52ms), eliminated database connection saturation, and maintained zero downtime through blue-green canary rollouts."
            )
        elif phase_num == 2:
            if "browser" in q_lower or "render" in q_lower or "fcp" in q_lower:
                return (
                    "📍 Architecture Strategy: Optimizing the Critical Rendering Path requires minimizing render-blocking CSS/JS, prioritizing critical CSS above the fold, and leveraging modern image formats (AVIF/WebP).\n\n"
                    "🛠️ Implementation: I implement code-splitting with dynamic imports, async/defer scripts, and layout containment to avoid layout shifts (CLS < 0.05).\n\n"
                    "📊 Outcome: This consistently achieves sub-1.2s First Contentful Paint (FCP) and a 95+ Lighthouse Performance Score."
                )
            elif "rate limit" in q_lower or "distribute" in q_lower:
                return (
                    "📍 Architecture Strategy: I would implement a distributed Token Bucket / Sliding Window algorithm using Redis clusters with Lua scripts for atomic increments.\n\n"
                    "🛠️ Resilience & Trade-offs: We configure tiered quota limits per API tier, client IP hashing behind NGINX, and fallback to local in-memory rate limiting if the Redis cluster experiences network partitions.\n\n"
                    "📊 Outcome: Prevents DoS spikes, enforces strict SLA multi-tenancy, and maintains <2ms overhead per check."
                )
            else:
                return (
                    f"📍 Architecture Strategy: When designing scalable systems for {role}, I emphasize loose coupling, stateless compute nodes, and CQRS (Command Query Responsibility Segregation) for high-scale reads.\n\n"
                    "🛠️ Technical Action: I establish circuit breakers, idempotency keys for mutation endpoints, and comprehensive telemetry (Prometheus/OpenTelemetry) to trace request lifecycles across microservices.\n\n"
                    "📊 Quantified Impact: Ensures linear horizontal scaling, 99.99% SLA availability, and graceful degradation during peak traffic."
                )
        else:
            return (
                "📍 Career Vision & Alignment: I view my trajectory as combining deep technical craftsmanship with high-leverage engineering leadership—mentoring peers and setting scalable architectural standards.\n\n"
                "🤝 Collaboration & Conflict: When facing differing technical opinions, I ground discussions in objective benchmarks, RFC design docs, and user impact rather than ego.\n\n"
                "🌱 Team Culture: I thrive in blameless, high-trust engineering cultures where teams move with velocity while maintaining rigorous code quality and shared ownership."
            )


    def _smart_evaluate_answer(self, role, question, answer, phase_name="Technical"):
        text = answer.strip()
        words = text.split()
        word_count = len(words)
        words_lower = [re.sub(r'[^a-zA-Z0-9]', '', w.lower()) for w in words if w.strip()]
        
        # 1. Check for extreme repetition or gibberish
        if word_count > 12:
            unique_words = set(words_lower)
            lexical_diversity = len(unique_words) / len(words_lower)
            
            # Check for repeating 3-word or 4-word n-grams
            ngrams = {}
            for i in range(len(words_lower) - 2):
                ngram = " ".join(words_lower[i:i+3])
                ngrams[ngram] = ngrams.get(ngram, 0) + 1
            max_ngram_repeat = max(ngrams.values()) if ngrams else 1

            if lexical_diversity < 0.45 or max_ngram_repeat >= 3:
                # Flag as repetitive filler / scrambled babble
                return {
                    "scores": {
                        "technical_depth": 22,
                        "structure_star": 20,
                        "communication": 28,
                        "confidence_alignment": 25,
                        "overall_score": 24
                    },
                    "quick_verdict": "Unsatisfactory / Highly Repetitive",
                    "strengths": [
                        "Spoken/written input was received by the system."
                    ],
                    "weaknesses_or_gaps": [
                        "The response consists primarily of repeated filler words and lacks substantive domain answers.",
                        "Did not formulate technical reasoning, architectural decisions, or concrete project examples.",
                        "Lacks structured communication and clear progression of thought."
                    ],
                    "actionable_tip": "Avoid filler repetition. Formulate a structured 3-part answer: 1) The core technical concept/project, 2) The specific action or architecture you chose, and 3) The concrete outcome or trade-off.",
                    "ideal_benchmark_answer": (
                        f"When answering '{question}', top candidates start by stating their core thesis, "
                        f"walk through concrete examples with structured logic (Situation, Task, Action, and Quantified Results), "
                        f"and conclude with clear reflections on long-term scalability and resilience."
                    )
                }

        # 2. Check for brief / non-answers
        if word_count < 15:
            tech_score, star_score, comm_score, conf_score = 38, 32, 42, 35
            verdict = "Needs Significant Elaboration"
            strengths = ["Acknowledged the question prompt."]
            weaknesses = [
                "Answer was overly brief with insufficient technical depth or concrete examples.",
                "Lacks structured elaboration (Context, Action, Outcome)."
            ]
            tip = "Use the STAR framework (Situation, Task, Action, Result) and cite concrete technologies, metrics, or career milestones."

        # 3. Check for casual off-topic chatter (lacks technical/domain substance)
        else:
            domain_markers = [
                "python", "javascript", "react", "node", "sql", "database", "api", "architecture",
                "microservices", "docker", "kafka", "redis", "cache", "latency", "scale", "system",
                "performance", "security", "design", "team", "project", "implemented", "optimized",
                "because", "result", "metric", "trade-off", "tradeoff", "challenge", "leadership", "goal"
            ]
            found_markers = [m for m in domain_markers if m in text.lower()]

            if len(found_markers) == 0 and word_count < 60:
                # Off-topic casual speech
                tech_score, star_score, comm_score, conf_score = 35, 30, 42, 35
                verdict = "Off-Topic / Missing Technical Substance"
                strengths = [
                    "Spoken delivery was audible and fluent."
                ]
                weaknesses = [
                    "The response did not address the target technical or domain premise of the question.",
                    "Missing core architectural concepts, tooling choices, or quantified project impact."
                ]
                tip = f"Directly ground your answer in {role} concepts. Explain the specific tools you used and why you chose them."

            elif word_count < 40:
                tech_score, star_score, comm_score, conf_score = 68, 65, 72, 70
                verdict = "Competent with Growth Gaps"
                strengths = [
                    "Answer addresses the question directly and introduces valid concepts.",
                    "Good baseline comprehension of the topic."
                ]
                weaknesses = [
                    "Could dive deeper into specific trade-offs, quantitative metrics, or long-term alignment.",
                    "Opportunity to explain 'why' a particular direction was chosen over alternatives."
                ]
                tip = "Elaborate with concrete examples: cite metrics, timeframes, or specific team scenarios."

            else:
                bonus = min(22, len(found_markers) * 4)
                tech_score = min(96, 75 + bonus)
                star_score = min(94, 73 + bonus)
                comm_score = min(97, 78 + bonus // 2)
                conf_score = min(95, 77 + bonus // 2)
                verdict = "Strong & Articulate Response" if (tech_score > 82) else "Solid Baseline Answer"

                strengths = [
                    f"Demonstrated coherent reasoning tailored to {phase_name}.",
                    f"Used effective terminology relevant to {role} engineering and leadership standards.",
                    "Provided practical depth and clear contextual awareness."
                ]
                weaknesses = [
                    "Can further highlight exact quantitative business/system impact (e.g. % latency reduction, throughput numbers).",
                    "Ensure explicit connection between past experience and future growth."
                ]
                tip = "Quantify your impact using measurable KPIs (e.g. 'reduced latency by 40%', 'led team of 4 engineers', 'achieved 99.9% uptime')."

        overall = int((tech_score + star_score + comm_score + conf_score) / 4)

        ideal_model = (
            f"When answering '{question}', top candidates start by stating their core thesis, "
            f"walk through concrete examples with structured logic (Situation, Task, Action, and Quantified Results), "
            f"and conclude with clear reflections on long-term scalability, resilience, or career vision."
        )

        return {
            "scores": {
                "technical_depth": tech_score,
                "structure_star": star_score,
                "communication": comm_score,
                "confidence_alignment": conf_score,
                "overall_score": overall
            },
            "quick_verdict": verdict,
            "strengths": strengths,
            "weaknesses_or_gaps": weaknesses,
            "actionable_tip": tip,
            "ideal_benchmark_answer": ideal_model
        }

    def _smart_final_report(self, role, experience_level, session_data):
        history = session_data.get("history", [])
        if not history:
            avg_score = 80
        else:
            scores = [h.get("evaluation", {}).get("scores", {}).get("overall_score", 75) for h in history]
            avg_score = int(sum(scores) / len(scores)) if scores else 78

        if avg_score >= 88:
            verdict = "Strong Hire"
            summary = f"Candidate demonstrated outstanding technical acumen, project authenticity, and structured communication across all 3 phases (Resume, Domain Rigor, and Leadership Vision) for the {role} position."
        elif avg_score >= 78:
            verdict = "Hire"
            summary = f"Candidate met expectations across core competencies for {role}. Solid technical understanding with convincing past project ownership and clear professional goals."
        elif avg_score >= 65:
            verdict = "Leaning Hire"
            summary = f"Candidate exhibits good potential and fundamental grasp of {role}, though answers lacked deeper edge-case coverage and STAR framing in complex scenarios."
        else:
            verdict = "Leaning No Hire"
            summary = f"Candidate requires structured reinforcement in domain depth and articulation before meeting the bar for {role} ({experience_level})."

        return {
            "candidate_summary": summary,
            "hiring_verdict": verdict,
            "overall_composite_score": avg_score,
            "competency_scores": {
                "core_domain_knowledge": min(98, avg_score + 2),
                "resume_project_credibility": min(96, avg_score + 4),
                "problem_solving_adaptability": min(96, avg_score),
                "communication_articulation": min(98, avg_score + 3),
                "leadership_culture_fit": min(94, avg_score + 1)
            },
            "key_strengths": [
                f"Authentic defense of projects and technical choices from resume.",
                f"Logical progression from system requirements to implementation nuances in {role}.",
                "Clear long-term career ambition and articulate vision."
            ],
            "critical_growth_areas": [
                "Consistently utilize the STAR method to structure narrative responses.",
                "Explicitly address non-functional requirements (scalability, failure modes, cost, monitoring)."
            ],
            "personalized_study_roadmap": [
                {
                    "day_range": "Days 1 - 7",
                    "focus": "Core Fundamentals & Systems Deep Dive",
                    "recommended_action": f"Review foundational architectural patterns and data flow trade-offs for {role}."
                },
                {
                    "day_range": "Days 8 - 18",
                    "focus": "STAR Structuring & Impact Quantification",
                    "recommended_action": "Draft 5 core project stories formatted strictly into Situation, Task, Action, and Quantified Results."
                },
                {
                    "day_range": "Days 19 - 30",
                    "focus": "Live High-Pressure Mock Drills & Executive Presence",
                    "recommended_action": "Run timed voice mock sessions focusing on concise delivery and rapid whiteboard/design structuring."
                }
            ]
        }
