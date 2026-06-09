from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CandidateProfile:
    name: str = ""
    email: str = ""
    role: str = ""
    experience_years: str = ""
    hr_email: str = ""
    resume_path: str = ""


@dataclass
class ResumeInsight:
    raw_text: str = ""
    skills: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class InterviewTurn:
    question: str
    answer: str
    difficulty: str
    focus_area: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class SkillAssessment:
    skill: str
    score: int
    evidence: list[str]
    depth: str


@dataclass
class CompetencyScore:
    name: str
    score: int
    evidence: list[str]


@dataclass
class InterviewReport:
    profile: CandidateProfile
    turns: list[InterviewTurn]
    skills: list[SkillAssessment]
    competencies: list[CompetencyScore]
    strengths: list[str]
    weaknesses: list[str]
    observations: list[str]
    recommendation: str
    resume: ResumeInsight = field(default_factory=ResumeInsight)
    confidence_score: int = 0
    technical_depth_score: int = 0
    overall_score: int = 0
    confidence_summary: dict[str, str | int | float] = field(default_factory=dict)
    integrity_summary: dict[str, str | int | float | list[str]] = field(default_factory=dict)
    recording_references: dict[str, str | list[str]] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
