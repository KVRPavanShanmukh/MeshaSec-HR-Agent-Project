import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .agent import TECH_KEYWORDS
from .models import ResumeInsight


def parse_resume(path: str) -> ResumeInsight:
    resume_path = Path(path)
    suffix = resume_path.suffix.lower()
    if suffix == ".docx":
        text = _read_docx(resume_path)
    elif suffix == ".pdf":
        text = _read_pdf(resume_path)
    else:
        raise ValueError("Resume must be a PDF or DOCX file.")
    text = _clean_text(text)
    return ResumeInsight(
        raw_text=text,
        skills=_extract_skills(text),
        projects=_extract_sections(text, ["project", "projects"], max_items=5),
        certifications=_extract_sections(text, ["certification", "certifications", "certificate"], max_items=4),
        experience=_extract_sections(text, ["experience", "employment", "work history"], max_items=5),
        summary=_summary(text),
    )


def _read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        pieces = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        if pieces:
            paragraphs.append("".join(pieces))
    return "\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF resume parsing requires PyPDF2. Run: python -m pip install PyPDF2") from exc
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.replace("\r", "\n")).strip()


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    skills = []
    for skill, keywords in TECH_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            skills.append(skill)
    extra_patterns = [
        "Spring Boot", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "React",
        "Node.js", "FastAPI", "Django", "Flask", "MySQL", "PostgreSQL", "MongoDB",
        "Git", "CI/CD", "REST API", "GraphQL", "Machine Learning",
    ]
    for skill in extra_patterns:
        if skill.lower() in lower and skill not in skills:
            skills.append(skill)
    return sorted(skills)


def _extract_sections(text: str, headings: list[str], max_items: int) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
    matches = []
    capture = False
    for line in lines:
        lower = line.lower()
        if any(heading in lower for heading in headings):
            capture = True
            if len(line.split()) > 2:
                matches.append(_short(line))
            continue
        if capture and re.search(r"education|skills|certifications|projects|experience|summary", lower):
            capture = False
        if capture and len(line.split()) >= 4:
            matches.append(_short(line))
        if len(matches) >= max_items:
            break
    return matches[:max_items]


def _summary(text: str) -> str:
    words = text.split()
    if not words:
        return "No readable resume text was extracted."
    compact = " ".join(words[:90])
    return compact + ("..." if len(words) > 90 else "")


def _short(text: str) -> str:
    clean = " ".join(text.split())
    return clean[:180] + ("..." if len(clean) > 180 else "")

