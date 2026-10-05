import os
import re
import io
import fitz  # PyMuPDF
import docx

def extract_text_from_file(file_storage, filename):
    """
    Extracts plain text and key highlights from PDF, DOCX, or TXT uploaded files.
    """
    filename_lower = filename.lower()
    text = ""

    try:
        file_bytes = file_storage.read()
        
        if filename_lower.endswith(".pdf"):
            # PyMuPDF extraction
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()

        elif filename_lower.endswith(".docx"):
            # python-docx extraction
            doc_file = io.BytesIO(file_bytes)
            doc = docx.Document(doc_file)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"

        elif filename_lower.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")

        else:
            text = file_bytes.decode("utf-8", errors="ignore")

    except Exception as e:
        print(f"[Resume Parsing Error]: {e}")
        return {"error": str(e), "text": ""}

    cleaned_text = clean_extracted_text(text)
    skills = extract_key_skills(cleaned_text)

    return {
        "text": cleaned_text,
        "skills": skills,
        "word_count": len(cleaned_text.split()),
        "filename": filename
    }

def clean_extracted_text(raw_text):
    # Remove excessive blank lines and non-printable characters
    cleaned = re.sub(r'\n\s*\n+', '\n\n', raw_text)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    return cleaned.strip()

def extract_key_skills(text):
    """Detects standard tech stack keywords from resume."""
    if not text:
        return []

    SKILL_KEYWORDS = [
        "Python", "JavaScript", "TypeScript", "React", "Next.js", "Vue.js", "Angular",
        "Node.js", "Express", "FastAPI", "Flask", "Django", "Java", "Spring Boot",
        "C++", "C#", ".NET", "Go", "Golang", "Rust", "PHP", "Laravel", "Ruby on Rails",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "SQLite",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "CI/CD", "Terraform", "Ansible",
        "GraphQL", "REST API", "Microservices", "Kafka", "RabbitMQ", "gRPC", "WebSockets",
        "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning", "Deep Learning",
        "LLM", "Prompt Engineering", "NLP", "Computer Vision", "System Design",
        "Linux", "Git", "Webpack", "TailwindCSS", "Redux", "SQL"
    ]
    found = []
    text_lower = text.lower()
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return found[:15]
