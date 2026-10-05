/**
 * TalentAI Mock Interview & Evaluator - Frontend Logic
 * Implements 3-Phase Pipeline, Resume File Parser (PDF/DOCX), Direct Speech-to-Speech & Live Captions
 * High-Fidelity Natural Voice Engine
 */

let currentSessionId = null;
let currentQuestionData = null;
let sessionQuestionsList = [];
let totalQuestionsCount = 6;
let currentQNum = 1;
let interviewTimerInterval = null;
let secondsElapsed = 0;
let apiKey = localStorage.getItem("talentai_api_key") || "";

// Direct Speech-to-Speech Mode Flag
let isSpeechToSpeechMode = true;

// Speech Recognition & Synthesis
let recognition = null;
let isRecording = false;
let synth = window.speechSynthesis;
let availableVoices = [];
let selectedVoice = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    initSpeechRecognition();
    initVoiceSynthesis();
    setupPersonaSelector();
    setupTextareaCounter();
    setupDropzone();
    loadPromptsShowcase();

    // Mode Toggle Listener
    const modeToggle = document.getElementById("speech-mode-toggle");
    if (modeToggle) {
        isSpeechToSpeechMode = modeToggle.checked;
        modeToggle.addEventListener("change", (e) => {
            isSpeechToSpeechMode = e.target.checked;
            showToast(isSpeechToSpeechMode ? "Direct Speech-to-Speech mode enabled." : "Standard mode active.", "info");
        });
    }

    if (apiKey) {
        document.getElementById("api-key-label").innerText = "API Connected";
    }
});

// View Navigation
function switchView(viewName) {
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

    const targetView = document.getElementById(`view-${viewName}`);
    const targetNav = document.getElementById(`nav-${viewName}`);

    if (targetView) targetView.classList.add("active");
    if (targetNav) targetNav.classList.add("active");

    const titles = {
        setup: { title: "Interview Configuration & 3-Phase Pipeline", sub: "Configure target role, upload resume (PDF/DOCX), and choose communication mode" },
        room: { title: "Live 3-Phase Multimodal Interview Room", sub: "Speak or type your answers; receive immediate rubric feedback and coaching" },
        report: { title: "3-Phase Hiring Committee Scorecard & Dossier", sub: "Comprehensive rubric evaluation, STAR breakdown, and 30-day mastery roadmap" },
        prompts: { title: "Applied Prompt Engineering Architecture", sub: "Inspect the 3-phase system prompts, JSON schemas, few-shot examples, and guardrails" }
    };

    if (titles[viewName]) {
        document.getElementById("page-title").innerText = titles[viewName].title;
        document.getElementById("page-subtitle").innerText = titles[viewName].sub;
    }
}

// Custom Role Toggle
function handleCustomRole(selectElem) {
    const customGroup = document.getElementById("custom-role-group");
    if (selectElem.value === "custom") {
        customGroup.style.display = "block";
    } else {
        customGroup.style.display = "none";
    }
}

// Persona Selection UI
function setupPersonaSelector() {
    const cards = document.querySelectorAll(".persona-card");
    cards.forEach(card => {
        card.addEventListener("click", () => {
            cards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            card.querySelector('input[type="radio"]').checked = true;
        });
    });
}

// Textarea Word Counter
function setupTextareaCounter() {
    const ta = document.getElementById("candidate-answer-input");
    const counter = document.getElementById("word-count");
    ta.addEventListener("input", () => {
        const text = ta.value.trim();
        const count = text ? text.split(/\s+/).length : 0;
        counter.innerText = `${count} word${count === 1 ? '' : 's'}`;
    });
}

// ==========================================
// NATURAL VOICE ENGINE & SELECTION
// ==========================================
function initVoiceSynthesis() {
    if (!synth) return;

    function populateVoices() {
        availableVoices = synth.getVoices();
        const voiceSelect = document.getElementById("voice-select");
        if (!voiceSelect || availableVoices.length === 0) return;

        // Filter English voices
        const englishVoices = availableVoices.filter(v => v.lang.startsWith("en"));
        const voicePool = englishVoices.length > 0 ? englishVoices : availableVoices;

        // Prioritize natural neural voices
        voicePool.sort((a, b) => {
            const aScore = (a.name.includes("Natural") || a.name.includes("Google") || a.name.includes("Neural") || a.name.includes("Online")) ? 2 : 1;
            const bScore = (b.name.includes("Natural") || b.name.includes("Google") || b.name.includes("Neural") || b.name.includes("Online")) ? 2 : 1;
            return bScore - aScore;
        });

        voiceSelect.innerHTML = voicePool.map((v, i) => {
            const isNatural = v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Neural") || v.name.includes("Online");
            const label = `${isNatural ? '✨ ' : ''}${v.name.replace(/Microsoft /g, '').replace(/Google /g, '')} (${v.lang})`;
            return `<option value="${v.voiceURI}">${label}</option>`;
        }).join('');

        // Select the top natural voice
        selectedVoice = voicePool[0];
    }

    populateVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = populateVoices;
    }
}

function changeInterviewerVoice(voiceURI) {
    if (!voiceURI) return;
    const found = availableVoices.find(v => v.voiceURI === voiceURI);
    if (found) {
        selectedVoice = found;
        showToast(`Voice updated to: ${found.name}`, "info");

        // Short preview
        const previewUtterance = new SpeechSynthesisUtterance("Voice updated. Ready for your mock interview.");
        previewUtterance.voice = selectedVoice;
        previewUtterance.rate = 0.95;
        previewUtterance.pitch = 1.0;
        synth.cancel();
        synth.speak(previewUtterance);
    }
}

// ==========================================
// RESUME FILE UPLOAD (PDF / DOCX / TXT)
// ==========================================
function setupDropzone() {
    const dropzone = document.getElementById("resume-dropzone");
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleResumeUpload(files[0]);
        }
    });
}

async function handleResumeUpload(file) {
    if (!file) return;

    const validExtensions = ['.pdf', '.docx', '.txt'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValid) {
        showToast("Please upload a valid PDF, DOCX, or TXT file.", "warning");
        return;
    }

    showToast(`Parsing ${file.name}...`, "info");

    const formData = new FormData();
    formData.append("resume_file", file);

    try {
        const res = await fetch("/api/upload-resume", {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        if (data.status === "success") {
            document.getElementById("resume-filename").innerText = data.filename;
            document.getElementById("resume-word-count").innerText = `${data.word_count} words extracted`;
            document.getElementById("resume-file-badge").style.display = "flex";
            document.getElementById("resume-dropzone").style.display = "none";

            // Render detected skills
            const skillsCloud = document.getElementById("resume-skills-tags");
            const skillsList = document.getElementById("skills-list");
            if (data.skills && data.skills.length > 0) {
                skillsList.innerHTML = data.skills.map(s => `<span class="skill-pill">${s}</span>`).join('');
                skillsCloud.style.display = "flex";
            }

            // Populate textarea buffer with extracted text
            document.getElementById("resume-context-input").value = data.text;

            showToast(`Resume parsed successfully! Extracted ${data.skills.length} core competencies.`, "success");
        } else {
            showToast(data.message || "Failed to parse resume.", "error");
        }
    } catch (err) {
        console.error(err);
        showToast("Error uploading resume file.", "error");
    }
}

function clearUploadedResume() {
    document.getElementById("resume-file-badge").style.display = "none";
    document.getElementById("resume-skills-tags").style.display = "none";
    document.getElementById("resume-dropzone").style.display = "block";
    document.getElementById("resume-context-input").value = "";
    document.getElementById("resume-file-input").value = "";
    showToast("Cleared uploaded resume.", "info");
}

// ==========================================
// START INTERVIEW SESSION (PRELOAD ALL 3 PHASES)
// ==========================================
async function startInterviewSession() {
    const roleSelect = document.getElementById("role-select").value;
    const customRole = document.getElementById("custom-role-input").value.trim();
    const role = (roleSelect === "custom" && customRole) ? customRole : roleSelect;
    const experience_level = document.getElementById("experience-select").value;
    const interview_type = document.getElementById("interview-type-select").value;
    const total_questions = parseInt(document.getElementById("total-q-select").value, 10);
    const resume_context = document.getElementById("resume-context-input").value.trim();
    
    const personaRadio = document.querySelector('input[name="persona"]:checked');
    const persona = personaRadio ? personaRadio.value : "tech_lead";

    totalQuestionsCount = total_questions;

    // Show Sleek Loading Screen
    const loadingScreen = document.getElementById("loading-screen");
    if (loadingScreen) {
        loadingScreen.style.display = "flex";
        document.getElementById("lstep-1").className = "loading-step-item active";
        document.getElementById("lstep-2").className = "loading-step-item";
        document.getElementById("lstep-3").className = "loading-step-item";
    }

    // Step 1 -> Step 2 transition
    setTimeout(() => {
        if (loadingScreen) {
            document.getElementById("lstep-1").className = "loading-step-item done";
            document.getElementById("lstep-2").className = "loading-step-item active";
        }
    }, 450);

    try {
        const res = await fetch("/api/start-session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                role,
                experience_level,
                persona,
                interview_type,
                total_questions,
                resume_context,
                api_key: apiKey
            })
        });

        const data = await res.json();
        if (data.status === "success") {
            currentSessionId = data.session_id;
            sessionQuestionsList = data.questions || [data.question];
            currentQNum = 1;
            currentQuestionData = sessionQuestionsList[0];

            if (loadingScreen) {
                document.getElementById("lstep-2").className = "loading-step-item done";
                document.getElementById("lstep-3").className = "loading-step-item active";
            }

            setTimeout(() => {
                if (loadingScreen) {
                    document.getElementById("lstep-3").className = "loading-step-item done";
                    loadingScreen.style.display = "none";
                }

                // Enable room view
                document.getElementById("nav-room").disabled = false;
                switchView("room");

                // Populate Room
                renderCurrentQuestion();
                startInterviewTimer();
                showToast(`3-Phase Pipeline Ready! Starting Phase 1: Resume Verification.`, "success");
            }, 600);
        } else {
            if (loadingScreen) loadingScreen.style.display = "none";
            showToast("Failed to initialize session.", "error");
        }
    } catch (err) {
        console.error(err);
        if (loadingScreen) loadingScreen.style.display = "none";
        showToast("Error starting interview.", "error");
    }
}

// Render Question & 3-Phase Badges
function renderCurrentQuestion() {
    if (!currentQuestionData) return;

    const phaseName = currentQuestionData.phase_name || "Phase 1: Resume Verification";

    document.getElementById("stage-phase-badge").innerText = phaseName;
    document.getElementById("s2s-phase-title").innerText = phaseName;
    document.getElementById("stage-round-badge").innerText = `Question ${currentQNum} of ${totalQuestionsCount}`;
    document.getElementById("stage-diff-badge").innerText = currentQuestionData.difficulty || "Medium";
    
    document.getElementById("current-question-text").innerText = currentQuestionData.question;
    document.getElementById("interviewer-hint").innerText = currentQuestionData.interviewer_note || "Focus on concrete architecture, trade-offs, and metrics.";

    // Hide AI model drawer on question switch
    const modelDrawer = document.getElementById("ai-model-answer-drawer");
    if (modelDrawer) {
        modelDrawer.style.display = "none";
        if (currentQuestionData.ai_model_answer) {
            document.getElementById("ai-model-answer-text").innerText = currentQuestionData.ai_model_answer;
        }
    }

    // Clear candidate answer
    document.getElementById("candidate-answer-input").value = "";
    document.getElementById("word-count").innerText = "0 words";

    // Update Live Captions with Question
    updateLiveCaption(`Interviewer: "${currentQuestionData.question}"`);

    // Auto-Speak Question
    speakCurrentQuestion();
}

// ==========================================
// AI MODEL BENCHMARK ANSWER CONTROLS
// ==========================================
function toggleAiModelAnswer() {
    const drawer = document.getElementById("ai-model-answer-drawer");
    if (!drawer) return;

    if (drawer.style.display === "none" || !drawer.style.display) {
        const sampleText = (currentQuestionData && currentQuestionData.ai_model_answer)
            ? currentQuestionData.ai_model_answer
            : (
                "📍 Situation & Task: In my previous initiative, I spearheaded the core service architecture redesign handling high-throughput production workloads.\n\n" +
                "🛠️ Action: I transitioned synchronous blocking endpoints into asynchronous event-driven pipelines using caching, connection pooling, and exponential backoff retries.\n\n" +
                "📊 Result: Reduced p99 latency by 45% and guaranteed 99.99% SLA availability."
            );
        document.getElementById("ai-model-answer-text").innerText = sampleText;
        drawer.style.display = "block";
    } else {
        drawer.style.display = "none";
    }
}

function copyAiModelAnswer() {
    const text = document.getElementById("ai-model-answer-text").innerText;
    navigator.clipboard.writeText(text);
    showToast("AI Model Benchmark Answer copied to clipboard!", "success");
}

function insertAiModelAnswer() {
    const text = document.getElementById("ai-model-answer-text").innerText;
    const ta = document.getElementById("candidate-answer-input");
    ta.value = text;
    ta.dispatchEvent(new Event("input"));
    const drawer = document.getElementById("ai-model-answer-drawer");
    if (drawer) drawer.style.display = "none";
    showToast("Inserted AI Benchmark Answer into response area!", "info");
}

// Update Live Closed Captions
function updateLiveCaption(text) {
    const captionElem = document.getElementById("live-caption-text");
    if (captionElem) {
        captionElem.innerText = text;
    }
}

// Timer
function startInterviewTimer() {
    clearInterval(interviewTimerInterval);
    secondsElapsed = 0;
    interviewTimerInterval = setInterval(() => {
        secondsElapsed++;
        const mins = String(Math.floor(secondsElapsed / 60)).padStart(2, "0");
        const secs = String(secondsElapsed % 60).padStart(2, "0");
        document.getElementById("timer-display").innerText = `${mins}:${secs}`;
    }, 1000);
}

// ==========================================
// SPEECH RECOGNITION (STT) & SPEECH SYNTHESIS (TTS)
// ==========================================
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Web Speech API not supported in this browser.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
        let finalSpeech = "";
        let interimSpeech = "";
        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalSpeech += event.results[i][0].transcript + " ";
            } else {
                interimSpeech += event.results[i][0].transcript;
            }
        }
        const completeSpeech = (finalSpeech + interimSpeech).trim();
        const ta = document.getElementById("candidate-answer-input");
        ta.value = completeSpeech;
        ta.dispatchEvent(new Event("input"));

        // Live captions stream for candidate
        updateLiveCaption(`You (Candidate): "${completeSpeech}"`);
    };

    recognition.onerror = (e) => {
        console.error("Speech Recognition Error:", e);
        stopVoiceRecording();
    };

    recognition.onend = () => {
        if (isRecording) {
            recognition.start();
        }
    };
}

function toggleVoiceInput() {
    if (!recognition) {
        showToast("Speech recognition is not supported in this browser. Please type your response.", "warning");
        return;
    }

    if (!isRecording) {
        recognition.start();
        isRecording = true;
        document.getElementById("mic-btn").classList.add("recording");
        document.getElementById("mic-btn-label").innerText = "Listening... (Click to Stop)";
        document.getElementById("s2s-speaking-indicator").innerText = "Listening to Candidate...";
        showToast("Microphone active. Speak your answer...", "info");
    } else {
        stopVoiceRecording();
    }
}

function stopVoiceRecording() {
    if (recognition && isRecording) {
        isRecording = false;
        recognition.stop();
        document.getElementById("mic-btn").classList.remove("recording");
        document.getElementById("mic-btn-label").innerText = "Speak Answer";
        document.getElementById("s2s-speaking-indicator").innerText = "Response Recorded";
        showToast("Voice recorded.", "success");
    }
}

// Text-to-Speech (Interviewer Natural Voice Audio + S2S Automation)
function speakCurrentQuestion() {
    if (!synth || !currentQuestionData) return;

    synth.cancel();
    const textToSpeak = currentQuestionData.question;
    const utterThis = new SpeechSynthesisUtterance(textToSpeak);

    // Apply selected natural human voice if available
    if (selectedVoice) {
        utterThis.voice = selectedVoice;
    }
    utterThis.rate = 0.94; // Calm, natural human cadence
    utterThis.pitch = 1.0;
    utterThis.volume = 1.0;

    const wave = document.getElementById("voice-wave");
    const indicator = document.getElementById("s2s-speaking-indicator");

    utterThis.onstart = () => {
        if (wave) wave.classList.add("active");
        if (indicator) indicator.innerText = "AI Speaking Question...";
        updateLiveCaption(`Interviewer: "${textToSpeak}"`);
    };

    utterThis.onend = () => {
        if (wave) wave.classList.remove("active");
        if (indicator) indicator.innerText = "Your Turn to Answer";
        
        // If in direct speech-to-speech mode, automatically start microphone for candidate!
        if (isSpeechToSpeechMode && recognition && !isRecording) {
            toggleVoiceInput();
        }
    };

    utterThis.onerror = () => {
        if (wave) wave.classList.remove("active");
        if (indicator) indicator.innerText = "Your Turn to Answer";
    };

    synth.speak(utterThis);
}

// ==========================================
// SUBMIT ANSWER, EVALUATE & SEAMLESS ADVANCE
// ==========================================

// 1. Direct Advance without blocking on evaluation review
// 1. Direct Advance with Instant 0ms Preloaded Question Transition
async function submitAndAdvanceDirectly() {
    const answerText = document.getElementById("candidate-answer-input").value.trim();
    if (!answerText) {
        showToast("Please type or speak your answer before moving to the next question.", "warning");
        return;
    }

    stopVoiceRecording();

    const isFinalRound = (currentQNum >= totalQuestionsCount);
    const saveNextBtn = document.getElementById("btn-save-next");

    if (isFinalRound) {
        if (saveNextBtn) {
            saveNextBtn.disabled = true;
            saveNextBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Finalizing...`;
        }
        showToast("All phases completed! Compiling Hiring Committee Dossier...", "info");

        try {
            const res = await fetch("/api/submit-answer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    answer: answerText
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                renderLiveEvaluation(data.evaluation, true, false);
                document.getElementById("nav-report").disabled = false;
                generateFinalReport();
            }
        } catch (err) {
            console.error(err);
            generateFinalReport();
        }
        return;
    }

    // Instant zero-latency transition to next preloaded question
    const nextQNum = currentQNum + 1;
    if (sessionQuestionsList && sessionQuestionsList.length >= nextQNum) {
        currentQNum = nextQNum;
        currentQuestionData = sessionQuestionsList[nextQNum - 1];
        renderCurrentQuestion();
        showToast(`Entering Question ${currentQNum}/${totalQuestionsCount} (${currentQuestionData.phase_name})`, "info");
    }

    // Evaluate previous answer asynchronously in background
    fetch("/api/submit-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: currentSessionId,
            answer: answerText
        })
    }).then(res => res.json()).then(data => {
        if (data.status === "success") {
            renderLiveEvaluation(data.evaluation, false, false);
        }
    }).catch(err => {
        console.warn("Background evaluation sync error:", err);
    });
}

// 2. Submit & Instant Evaluate with prominent Proceed triggers
async function submitCandidateAnswer() {
    const answerText = document.getElementById("candidate-answer-input").value.trim();
    if (!answerText) {
        showToast("Please type or speak your answer before submitting.", "warning");
        return;
    }

    stopVoiceRecording();

    const submitBtn = document.getElementById("submit-answer-btn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Evaluating...`;
    updateLiveCaption("Assessor analyzing your response against 3-Phase rubric...");

    try {
        const res = await fetch("/api/submit-answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSessionId,
                answer: answerText
            })
        });

        const data = await res.json();
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Submit & Instant Evaluate</span> <i class="fa-solid fa-paper-plane"></i>`;

        if (data.status === "success") {
            if (data.is_completed) {
                document.getElementById("nav-report").disabled = false;
                renderLiveEvaluation(data.evaluation, true, true);
                showToast("All 3 interview phases completed! Ready for Final Committee Dossier.", "success");
            } else {
                currentQuestionData = data.next_question;
                currentQNum = data.current_question_num;
                renderLiveEvaluation(data.evaluation, false, true);
                showToast(`Answer evaluated! Ready for Question ${currentQNum} (${currentQuestionData.phase_name}).`, "success");
            }
        } else {
            showToast(data.error || "Failed to submit answer.", "error");
        }
    } catch (err) {
        console.error(err);
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Submit & Instant Evaluate</span> <i class="fa-solid fa-paper-plane"></i>`;
        showToast("Error submitting answer.", "error");
    }
}

// Render Instant Rubric Feedback & Update Next-Step Controls
function renderLiveEvaluation(evalData, isCompleted, showMainBanner = true) {
    const scores = evalData.scores || {};
    document.getElementById("eval-verdict-badge").innerText = evalData.quick_verdict || "Evaluated";

    const nextLabel = isCompleted 
        ? "Generate Final Committee Dossier" 
        : `Proceed to ${currentQuestionData.phase_name || 'Next Question'} (${currentQNum}/${totalQuestionsCount}) ➔`;

    const actionCall = isCompleted ? "generateFinalReport()" : "proceedToNextQuestion()";

    // Update Main Stage Banner on the left
    if (showMainBanner) {
        const stageActions = document.getElementById("response-actions-container");
        const stageBanner = document.getElementById("post-eval-stage-banner");
        const stageProceedLabel = document.getElementById("stage-proceed-label");
        const stageMessage = document.getElementById("post-eval-message");

        if (stageActions) stageActions.style.display = "none";
        if (stageBanner) {
            stageBanner.style.display = "flex";
            if (stageMessage) {
                stageMessage.innerText = isCompleted 
                    ? "All 3 Phases Finished! Review rubric and generate final dossier." 
                    : `Evaluated (Score: ${scores.overall_score || 80}/100). Click to continue.`;
            }
            if (stageProceedLabel) {
                stageProceedLabel.innerText = nextLabel;
            }
            const proceedBtn = document.getElementById("btn-stage-proceed");
            if (proceedBtn) {
                proceedBtn.setAttribute("onclick", actionCall);
            }
        }
    }

    const container = document.getElementById("eval-body-content");
    container.innerHTML = `
        <!-- Sticky Top Proceed Action Bar so candidate never has to scroll -->
        <div class="eval-sticky-proceed">
            <button class="btn btn-primary btn-lg full-width pulse-btn" onclick="${actionCall}">
                <span>${nextLabel}</span>
            </button>
        </div>

        <div class="rubric-score-grid">
            <div class="rubric-mini-card">
                <span class="metric-name">Technical Depth</span>
                <span class="metric-score">${scores.technical_depth || 80}/100</span>
            </div>
            <div class="rubric-mini-card">
                <span class="metric-name">STAR Method</span>
                <span class="metric-score">${scores.structure_star || 75}/100</span>
            </div>
            <div class="rubric-mini-card">
                <span class="metric-name">Communication</span>
                <span class="metric-score">${scores.communication || 85}/100</span>
            </div>
            <div class="rubric-mini-card">
                <span class="metric-name">Turn Score</span>
                <span class="metric-score text-emerald">${scores.overall_score || 80}/100</span>
            </div>
        </div>

        <div class="eval-section">
            <h4 class="text-emerald"><i class="fa-solid fa-circle-check"></i> Highlighted Strengths</h4>
            <ul class="styled-list">
                ${(evalData.strengths || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>

        <div class="eval-section">
            <h4 class="text-rose"><i class="fa-solid fa-triangle-exclamation"></i> Growth Gaps / Missed Points</h4>
            <ul class="styled-list">
                ${(evalData.weaknesses_or_gaps || []).map(w => `<li>${w}</li>`).join('')}
            </ul>
        </div>

        <div class="eval-section">
            <h4 class="text-cyan"><i class="fa-solid fa-lightbulb"></i> Actionable Next-Level Tip</h4>
            <div class="tip-box">${evalData.actionable_tip || 'Elaborate on edge cases and quantitative impact.'}</div>
        </div>

        <div class="eval-section">
            <h4 class="text-purple"><i class="fa-solid fa-wand-magic-sparkles"></i> Model 'Ideal Benchmark' Answer</h4>
            <div class="benchmark-box">${evalData.ideal_benchmark_answer || 'N/A'}</div>
        </div>

        <div class="mt-4">
            <button class="btn btn-primary btn-lg full-width" onclick="${actionCall}">
                <span>${nextLabel}</span>
            </button>
        </div>
    `;
}

function proceedToNextQuestion() {
    // Reset left stage action bar
    const stageActions = document.getElementById("response-actions-container");
    const stageBanner = document.getElementById("post-eval-stage-banner");
    if (stageActions) stageActions.style.display = "flex";
    if (stageBanner) stageBanner.style.display = "none";

    renderCurrentQuestion();
    document.querySelector(".interview-stage").scrollIntoView({ behavior: "smooth" });
}


// Generate Final Hiring Committee Report
async function generateFinalReport() {
    showToast("Synthesizing 3-Phase Final Hiring Dossier...", "info");

    try {
        const res = await fetch("/api/final-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: currentSessionId })
        });

        const data = await res.json();
        if (data.status === "success") {
            clearInterval(interviewTimerInterval);
            renderFinalReportView(data.report, data.session_summary);
            switchView("report");
            showToast("Report generated successfully!", "success");
        } else {
            showToast("Failed to compile final report.", "error");
        }
    } catch (err) {
        console.error(err);
        showToast("Error generating final report.", "error");
    }
}

// Render Final Scorecard Dossier
function renderFinalReportView(report, summary) {
    document.getElementById("report-hiring-verdict").innerText = report.hiring_verdict || "Hire";
    document.getElementById("report-candidate-summary").innerText = report.candidate_summary || "";
    document.getElementById("report-composite-score").innerText = report.overall_composite_score || "85";

    // Competency Bars
    const compContainer = document.getElementById("competency-bars-container");
    const compScores = report.competency_scores || {};
    
    compContainer.innerHTML = Object.entries(compScores).map(([key, val]) => {
        const formattedName = key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
        return `
            <div class="competency-item">
                <div class="comp-header">
                    <span>${formattedName}</span>
                    <span class="text-cyan font-bold">${val}%</span>
                </div>
                <div class="comp-bar-bg">
                    <div class="comp-bar-fill" style="width: ${val}%;"></div>
                </div>
            </div>
        `;
    }).join('');

    // Strengths and Growth Areas
    const strengthsList = document.getElementById("report-strengths-list");
    strengthsList.innerHTML = (report.key_strengths || []).map(s => `<li>${s}</li>`).join('');

    const growthList = document.getElementById("report-growth-list");
    growthList.innerHTML = (report.critical_growth_areas || []).map(g => `<li>${g}</li>`).join('');

    // 30-Day Roadmap Timeline
    const roadmapContainer = document.getElementById("report-roadmap-timeline");
    roadmapContainer.innerHTML = (report.personalized_study_roadmap || []).map(r => `
        <div class="roadmap-card-item">
            <span class="roadmap-badge">${r.day_range}</span>
            <h4>${r.focus}</h4>
            <p>${r.recommended_action}</p>
        </div>
    `).join('');

    // Transcript Turns
    const transcriptContainer = document.getElementById("report-transcript-container");
    transcriptContainer.innerHTML = (summary.history || []).map((turn, i) => `
        <div class="transcript-turn">
            <div class="turn-header">
                <span class="text-cyan">${turn.phase_name || `Round #${turn.question_number}`}: ${turn.category || 'Interview'}</span>
                <span class="badge badge-emerald">Score: ${turn.evaluation?.scores?.overall_score || 80}/100</span>
            </div>
            <div class="turn-q"><i class="fa-solid fa-circle-question"></i> ${turn.question}</div>
            <div class="turn-a"><strong>Candidate:</strong> ${turn.answer || '(No answer provided)'}</div>
            <div class="turn-feedback">
                <span class="text-muted"><strong>Assessor Verdict:</strong> ${turn.evaluation?.quick_verdict || 'Reviewed'}</span>
                <span class="text-cyan"><strong>Key Tip:</strong> ${turn.evaluation?.actionable_tip || 'N/A'}</span>
            </div>
        </div>
    `).join('');
}

// Load Prompt Architecture Showcase
async function loadPromptsShowcase() {
    try {
        const res = await fetch("/api/prompts");
        const data = await res.json();
        document.getElementById("code-system-prompt").innerText = data.system_interviewer_prompt || "";
        document.getElementById("code-eval-prompt").innerText = data.interviewer_feedback_prompt || "";
        document.getElementById("code-final-prompt").innerText = data.final_evaluation_report_prompt || "";
    } catch (err) {
        console.error("Error loading prompts:", err);
    }
}

// Quick Structuring Hint
function provideAnswerHint() {
    const hint = "💡 PRO TIP: Structure your response using STAR: 1) Situation (the context), 2) Task (the challenge), 3) Action (what YOU specifically built or chose), and 4) Result (metrics, latency % reduction, or outcome).";
    showToast(hint, "info");
}

// API Key Modal
function openApiKeyModal() {
    document.getElementById("modal-api-key").value = apiKey;
    document.getElementById("api-modal").style.display = "flex";
}

function closeApiKeyModal() {
    document.getElementById("api-modal").style.display = "none";
}

function saveApiKeySettings() {
    const key = document.getElementById("modal-api-key").value.trim();
    apiKey = key;
    if (key) {
        localStorage.setItem("talentai_api_key", key);
        document.getElementById("api-key-label").innerText = "API Connected";
        showToast("OpenAI API key saved successfully.", "success");
    } else {
        localStorage.removeItem("talentai_api_key");
        document.getElementById("api-key-label").innerText = "API Settings";
        showToast("Cleared custom API key. Using built-in intelligent engine.", "info");
    }
    closeApiKeyModal();
}

// ==========================================
// END CURRENT LIVE SESSION CONTROLS
// ==========================================
function confirmEndSession() {
    const modal = document.getElementById("end-session-modal");
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeEndSessionModal() {
    const modal = document.getElementById("end-session-modal");
    if (modal) {
        modal.style.display = "none";
    }
}

function terminateSessionToReport() {
    closeEndSessionModal();
    stopVoiceRecording();
    if (synth) synth.cancel();
    clearInterval(interviewTimerInterval);
    generateFinalReport();
}

function terminateSessionToSetup() {
    closeEndSessionModal();
    stopVoiceRecording();
    if (synth) synth.cancel();
    clearInterval(interviewTimerInterval);
    currentSessionId = null;
    currentQuestionData = null;
    currentQNum = 1;

    // Reset controls
    const stageActions = document.getElementById("response-actions-container");
    const stageBanner = document.getElementById("post-eval-stage-banner");
    if (stageActions) stageActions.style.display = "flex";
    if (stageBanner) stageBanner.style.display = "none";
    document.getElementById("candidate-answer-input").value = "";
    document.getElementById("word-count").innerText = "0 words";

    switchView("setup");
    showToast("Interview session ended. Returned to setup.", "info");
}

// Theme Toggle
function toggleTheme() {
    const isDark = document.body.classList.toggle("dark-theme");
    document.body.classList.toggle("light-theme", !isDark);
    const icon = document.querySelector("#theme-toggle i");
    if (isDark) {
        icon.className = "fa-solid fa-moon";
    } else {
        icon.className = "fa-solid fa-sun";
    }
}

// Toast
function showToast(msg, type = "info") {
    const toast = document.getElementById("toast");
    toast.innerText = msg;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = "toast";
    }, 4500);
}
