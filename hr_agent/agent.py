import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict

from .models import CandidateProfile, CompetencyScore, InterviewReport, InterviewTurn, ResumeInsight, SkillAssessment


TECH_KEYWORDS = {
    "Python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
    "JavaScript": ["javascript", "typescript", "react", "node", "express", "next.js", "vue", "angular"],
    "Java": ["java", "spring", "spring boot", "hibernate"],
    "C#": ["c#", ".net", "asp.net"],
    "C++": ["c++", "cpp"],
    "SQL": ["sql", "postgres", "postgresql", "mysql", "oracle", "sqlite", "joins", "index"],
    "NoSQL": ["mongodb", "redis", "dynamodb", "cassandra", "nosql"],
    "Cloud": ["aws", "azure", "gcp", "cloud", "lambda", "s3", "ec2", "kubernetes", "docker", "iam", "vpc", "serverless"],
    "Networking": ["network", "tcp", "udp", "ip", "dns", "http", "https", "subnet", "routing", "router", "switch", "firewall", "osi", "vpn"],
    "DevOps": ["ci/cd", "jenkins", "github actions", "gitlab", "docker", "terraform", "monitoring"],
    "System Design": ["microservice", "scalability", "load balancer", "cache", "queue", "event", "distributed"],
    "Testing": ["unit test", "integration test", "pytest", "jest", "selenium", "mock", "coverage"],
    "Security": ["auth", "oauth", "jwt", "encryption", "xss", "csrf", "sql injection", "security"],
}

COMPETENCIES = [
    "Programming Fundamentals",
    "Problem Solving",
    "System Design",
    "Database Knowledge",
    "Software Development Practices",
    "Communication Skills",
]


class TechnicalInterviewAgent:
    def __init__(self) -> None:
        self.turns: list[InterviewTurn] = []
        self.difficulty = "medium"
        self._question_count = 0
        self.resume = ResumeInsight()
        self.interviewer_name = "Shanmukh"
        self.last_generation_source = "fallback"
        self.last_generation_error = ""

    def set_interviewer(self, name: str) -> None:
        self.interviewer_name = name or "Shanmukh"

    def opening_question(self, profile: CandidateProfile, resume: ResumeInsight | None = None) -> str:
        return (
            f"Hello, I'm {self.interviewer_name}, your AI HR Interviewer. "
            "Please introduce yourself, summarize your background, and describe one project or achievement you are most proud of."
        )
    def record_answer(self, question: str, answer: str, focus_area: str = "General") -> InterviewTurn:
        evidence = self._evidence_from_answer(answer)
        turn = InterviewTurn(
            question=question,
            answer=answer.strip(),
            difficulty=self.difficulty,
            focus_area=focus_area,
            evidence=evidence,
        )
        self.turns.append(turn)
        self._question_count += 1
        self._adjust_difficulty(answer)
        return turn

    def set_resume(self, resume: ResumeInsight) -> None:
        self.resume = resume

    def next_question(self, profile: CandidateProfile) -> tuple[str, str]:
        if not self.turns:
            return self.opening_question(profile, self.resume), "Resume Introduction"


        answer = self.turns[-1].answer
        skills = self.extract_skills(answer)
        focus_skill = skills[0] if skills else self._resume_focus()
        self.last_generation_error = ""
        question = self._openai_question(profile)
        if question and not self._is_repeated_question(question):
            self.last_generation_source = "ai"
            return question, focus_skill
        if os.getenv("OPENAI_API_KEY", "").strip() and not question:
            self.last_generation_error = "AI generation was unavailable. A fallback question was selected."
        question = self._heuristic_question(focus_skill, answer)
        if self._is_repeated_question(question):
            question = self._unique_fallback_question(focus_skill)
        self.last_generation_source = "fallback"
        return question, focus_skill

    def should_finish(self, max_questions: int) -> bool:
        return self._question_count >= max_questions

    def build_report(self, profile: CandidateProfile, resume: ResumeInsight | None = None) -> InterviewReport:
        skills = self.assess_skills()
        competencies = self.score_competencies()
        strengths, weaknesses = self._strengths_and_weaknesses(skills, competencies)
        observations = self._observations(skills, competencies)
        average = round(sum(score.score for score in competencies) / max(len(competencies), 1))
        confidence_score = self._confidence_score()
        technical_depth_score = self._technical_depth_score(skills, competencies)
        overall_score = round((average * 0.55) + (technical_depth_score * 0.3) + (confidence_score * 0.15))
        if overall_score >= 80:
            recommendation = "Strong Hire"
        elif overall_score >= 68:
            recommendation = "Hire"
        elif overall_score >= 55:
            recommendation = "Hold / Needs Human Review"
        else:
            recommendation = "No Hire"

        return InterviewReport(
            profile=profile,
            turns=self.turns,
            skills=skills,
            competencies=competencies,
            strengths=strengths,
            weaknesses=weaknesses,
            observations=observations,
            recommendation=recommendation,
            resume=ResumeInsight(),
            confidence_score=confidence_score,
            technical_depth_score=technical_depth_score,
            overall_score=overall_score,
        )

    def extract_skills(self, text: str) -> list[str]:
        lower = text.lower()
        found = []
        for skill, words in TECH_KEYWORDS.items():
            if any(word in lower for word in words):
                found.append(skill)
        return found

    def assess_skills(self) -> list[SkillAssessment]:
        skill_evidence: dict[str, list[str]] = defaultdict(list)
        for turn in self.turns:
            for skill in self.extract_skills(turn.answer):
                skill_evidence[skill].extend(turn.evidence or [self._short_quote(turn.answer)])

        assessments = []
        for skill, evidence in sorted(skill_evidence.items()):
            combined = " ".join(evidence).lower()
            depth = "Surface"
            score = 48
            if any(word in combined for word in ["implemented", "designed", "optimized", "debugged", "deployed"]):
                depth = "Practical"
                score = 68
            if any(word in combined for word in ["trade-off", "tradeoff", "latency", "scalability", "complexity", "bottleneck"]):
                depth = "Advanced"
                score = 82
            if any(word in combined for word in ["measured", "profiled", "benchmark", "incident", "production"]):
                depth = "Production-tested"
                score = 88
            assessments.append(SkillAssessment(skill=skill, score=min(score, 95), evidence=evidence[:4], depth=depth))

        if not assessments:
            assessments.append(
                SkillAssessment(
                    skill="Technical Breadth",
                    score=25,
                    evidence=["The interview answers did not provide enough concrete technical evidence for a reliable skill map."],
                    depth="Insufficient evidence",
                )
            )
        return assessments

    def score_competencies(self) -> list[CompetencyScore]:
        ai_scores = self._openai_competency_evaluation()
        if ai_scores:
            return ai_scores
        rubrics = {
            "Programming Fundamentals": ["algorithm", "data structure", "oop", "class", "function", "exception", "async", "complexity", "memory", "thread"],
            "Problem Solving": ["debug", "root cause", "hypothesis", "analyze", "reproduce", "verify", "edge case", "incident", "bottleneck"],
            "System Design": ["scale", "cache", "queue", "load balancer", "microservice", "latency", "availability", "api", "security", "observability"],
            "Database Knowledge": ["sql", "index", "join", "transaction", "normalization", "query", "postgres", "mysql", "mongodb", "consistency"],
            "Software Development Practices": ["git", "code review", "ci/cd", "test", "deploy", "rollback", "monitoring", "documentation", "agile"],
            "Communication Skills": ["because", "first", "then", "for example", "result", "therefore", "trade-off"],
        }
        return [self._evidence_rubric_score(name, signals) for name, signals in rubrics.items()]

    def _evidence_rubric_score(self, name: str, signals: list[str]) -> CompetencyScore:
        relevant = []
        for index, turn in enumerate(self.turns, start=1):
            combined = f"{turn.question} {turn.answer}".lower()
            if name == "Communication Skills" or any(signal in combined for signal in signals):
                relevant.append((index, turn))
        if not relevant:
            return CompetencyScore(name, 15, ["No question-answer evidence demonstrated this competency."])
        turn_scores = []
        evidence = []
        for index, turn in relevant:
            answer = turn.answer.strip()
            lower = answer.lower()
            if self._is_non_answer(answer):
                turn_scores.append(5)
                evidence.append(f"Q{index}: Non-substantive response; no assessable evidence.")
                continue
            score = 18
            words = len(answer.split())
            score += min(16, words // 5)
            concept_hits = [signal for signal in signals if signal in lower]
            score += min(18, len(concept_hits) * 4)
            practical = [term for term in ["implemented", "built", "configured", "deployed", "debugged", "designed", "used"] if term in lower]
            reasoning = [term for term in ["because", "therefore", "root cause", "trade-off", "alternative", "reason"] if term in lower]
            validation = [term for term in ["tested", "measured", "verified", "monitored", "benchmark", "result", "%", "latency"] if term in lower]
            score += min(16, len(practical) * 4)
            score += min(15, len(reasoning) * 5)
            score += min(15, len(validation) * 4)
            if words < 12:
                score = min(score, 30)
            turn_scores.append(min(score, 95))
            markers = concept_hits[:3] + practical[:2] + reasoning[:1] + validation[:1]
            quote = self._short_quote(answer)
            evidence.append(f"Q{index}: {quote} | Evidence markers: {', '.join(markers) or 'limited specificity'}.")
        weighted = round(sum(turn_scores) / len(turn_scores))
        coverage = len(relevant) / max(len(self.turns), 1)
        final_score = round((weighted * 0.9) + (min(1.0, coverage * 2) * 10))
        return CompetencyScore(name, max(5, min(final_score, 95)), evidence[:5])

    def _openai_competency_evaluation(self) -> list[CompetencyScore] | None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or not self.turns:
            return None
        transcript = "\n\n".join(f"Q{index}: {turn.question}\nA{index}: {turn.answer}" for index, turn in enumerate(self.turns, 1))
        prompt = (
            "Evaluate this technical interview rigorously. Read every answer in relation to its question. "
            "Do not award points for merely mentioning keywords. Assess correctness, relevance, conceptual understanding, "
            "implementation detail, reasoning, trade-offs, validation, and measurable outcomes. Penalize vague, incorrect, "
            "contradictory, copied-sounding, or non-responsive answers. Return JSON only with key competencies, an array of "
            "exactly six objects containing name, score (0-100), and evidence (2-4 concise transcript-grounded strings). "
            f"Required names: {', '.join(COMPETENCIES)}.\nRole: {self.resume.summary[:300]}\nTranscript:\n{transcript[:12000]}"
        )
        body = {"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1400, "response_format": {"type": "json_object"}}
        request = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                payload = json.loads(response.read().decode("utf-8"))
            data = json.loads(payload["choices"][0]["message"]["content"])
            items = data.get("competencies", [])
            by_name = {str(item.get("name")): item for item in items}
            if any(name not in by_name for name in COMPETENCIES):
                return None
            return [CompetencyScore(name, max(0, min(int(by_name[name]["score"]), 100)), [str(value) for value in by_name[name].get("evidence", [])][:4]) for name in COMPETENCIES]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, TypeError, TimeoutError, json.JSONDecodeError):
            return None
    def _openai_question(self, profile: CandidateProfile) -> str | None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        transcript = "\n".join(
            f"Q: {turn.question}\nA: {turn.answer}" for turn in self.turns
        )
        prompt = (
            "You are an expert technical HR interviewer. Generate exactly one concise follow-up "
            "technical interview question based on the candidate's latest answer. "
            "Verify depth, adapt difficulty, and avoid asking for personal data. Ask a distinct domain not already covered when possible: programming, algorithms, networking (TCP/IP, DNS, HTTP, routing, subnets), cloud (IAM, VPC, scaling, availability), databases, system design, security, testing, or delivery. Distinguish application programming from network transport and cloud infrastructure.\n\n"
            f"Role: {profile.role}\nExperience: {profile.experience_years}\n"
            f"Resume skills: {', '.join(self.resume.skills[:12])}\nResume projects: {'; '.join(self.resume.projects[:4])}\n"
            f"Resume experience: {'; '.join(self.resume.experience[:4])}\nResume context: {self.resume.summary[:900]}\n"
            f"Current difficulty: {self.difficulty}\nTranscript:\n{transcript}\n\nQuestion:"
        )
        body = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 120,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            question = payload["choices"][0]["message"]["content"].strip()
            return question if question.endswith("?") else question + "?"
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError, json.JSONDecodeError):
            return None

    def _heuristic_question(self, focus_skill: str, answer: str) -> str:
        lower_focus = focus_skill.lower()
        if self._question_count == 1:
            if self.resume.projects:
                return f"Your resume mentions this project: {self.resume.projects[0]}. Explain its architecture, your exact contribution, one difficult decision, and the measured result."
            return "Describe a substantial project you completed, its architecture, your exact contribution, one difficult decision, and the result."
        if self._question_count == 2:
            return f"Let's verify your depth in {self._skill_at(0)}. Explain a production use case, implementation decisions, limitations, and one failure mode."
        if self._question_count == 3:
            return f"Using {self._skill_at(1)}, describe a difficult bug or outage. Explain evidence gathering, root cause, alternatives considered, and how you proved the fix."
        if self._question_count == 4:
            return "Explain the networking path for a user request from DNS through TCP/TLS and HTTP to an application. Include routing, load balancing, failure diagnosis, and how networking differs from programming."
        if self._question_count == 5:
            return f"Design a secure cloud deployment for a {self._skill_at(0)} service. Explain compute, storage, IAM, VPC networking, scaling, availability, monitoring, cost trade-offs, and how cloud infrastructure differs from the program."
        if self._question_count == 6:
            return f"For a data-intensive feature involving {self._skill_at(1)}, choose SQL or NoSQL and justify schema design, indexing, transactions or consistency, and performance validation."
        if self._question_count == 7:
            return f"Demonstrate programming fundamentals using {self._skill_at(0)}. Explain one algorithm or data structure, complexity, error handling, and a concrete implementation example."
        if self._question_count == 8:
            return f"Explain how you would test, review, secure, deploy, and observe a {self._skill_at(2)} change. Include CI/CD, rollback, incident response, and measurable release criteria."
        if self._question_count == 9:
            return f"Final scenario: design a secure and reliable production feature using {self._skill_at(0)}. Connect application logic, network boundaries, cloud resources, data storage, testing, and monitoring, and explain the key trade-offs."
        if "spring" in lower_focus:
            return "In Spring Boot, how would you structure services, transactions, exception handling, and security for a production REST API?"
        if "docker" in lower_focus:
            return "How would you containerize an application with Docker and diagnose a container that works locally but fails in production?"
        if "aws" in lower_focus or "cloud" in lower_focus:
            return "How would you deploy a secure, observable, and cost-conscious application on cloud infrastructure?"
        if self.difficulty == "easy":
            return (
                f"You mentioned {focus_skill}. Can you explain the core concept in simple terms "
                "and describe where you used it?"
            )
        if self.difficulty == "hard":
            return (
                f"Let's go deeper into {focus_skill}. Describe a real technical trade-off you faced, "
                "the options you considered, and how you validated the final decision."
            )
        if any(word in answer.lower() for word in ["database", "sql", "postgres", "mysql", "mongodb"]):
            return "How would you diagnose and optimize a slow database query in a production system?"
        if any(word in answer.lower() for word in ["api", "microservice", "service", "backend"]):
            return "How would you design an API endpoint to be reliable, secure, observable, and easy to maintain?"
        if any(word in answer.lower() for word in ["bug", "debug", "issue", "problem"]):
            return "Walk me through your debugging process from first symptom to verified fix."
        return (
            f"Can you give a concrete example involving {focus_skill}, including the problem, "
            "your implementation choices, and the result?"
        )

    def _is_repeated_question(self, question: str) -> bool:
        normalized = set(re.findall(r"[a-z0-9+#.]+", question.lower()))
        for turn in self.turns:
            previous = set(re.findall(r"[a-z0-9+#.]+", turn.question.lower()))
            union = normalized | previous
            if union and len(normalized & previous) / len(union) >= 0.62:
                return True
        return False

    def _unique_fallback_question(self, focus_skill: str) -> str:
        fallbacks = [
            f"Using {focus_skill}, describe a decision you made, the alternatives you rejected, and the measurable outcome.",
            f"What is the most difficult production issue you have faced with {focus_skill}, and how did you verify the resolution?",
            f"How would you teach an important {focus_skill} concept to a junior engineer using an example from your work?",
            f"Describe one limitation of {focus_skill} and when you would deliberately choose a different technology.",
            "Choose one project from your background and explain what you would redesign today and why.",
        ]
        for question in fallbacks:
            if not self._is_repeated_question(question):
                return question
        return f"Provide another concrete example from your experience with {focus_skill}, focusing on evidence and results."
    def _resume_focus(self) -> str:
        if self.resume.skills:
            return self.resume.skills[self._question_count % len(self.resume.skills)]
        return self._fallback_focus()

    def _skill_at(self, index: int) -> str:
        if self.resume.skills:
            return self.resume.skills[index % len(self.resume.skills)]
        return self._fallback_focus()

    def _fallback_focus(self) -> str:
        cycle = ["Programming Fundamentals", "Problem Solving", "System Design", "Database Knowledge", "Testing"]
        return cycle[self._question_count % len(cycle)]

    def _adjust_difficulty(self, answer: str) -> None:
        lower = answer.lower()
        strong_signals = ["because", "trade-off", "optimized", "implemented", "designed", "measured", "production"]
        weak_signals = ["not sure", "maybe", "i don't know", "no idea", "basic", "beginner"]
        if len(answer.split()) > 70 and sum(signal in lower for signal in strong_signals) >= 2:
            self.difficulty = "hard"
        elif len(answer.split()) < 25 or any(signal in lower for signal in weak_signals):
            self.difficulty = "easy"
        else:
            self.difficulty = "medium"

    def _evidence_from_answer(self, answer: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
        useful = [sentence.strip() for sentence in sentences if len(sentence.split()) >= 7]
        if useful:
            return [self._short_quote(sentence) for sentence in useful[:3]]
        return [self._short_quote(answer)] if answer.strip() else ["No substantive answer provided."]

    def _short_quote(self, text: str) -> str:
        clean = " ".join(text.split())
        return clean[:220] + ("..." if len(clean) > 220 else "")

    def _score_programming(self, words: str) -> CompetencyScore:
        signals = ["algorithm", "data structure", "oop", "function", "class", "complexity", "exception", "async"]
        return self._keyword_score("Programming Fundamentals", words, signals)

    def _score_problem_solving(self, words: str) -> CompetencyScore:
        signals = ["debug", "root cause", "analyze", "step", "test", "verify", "edge case", "hypothesis"]
        return self._keyword_score("Problem Solving", words, signals)

    def _score_system_design(self, words: str) -> CompetencyScore:
        signals = ["scale", "cache", "queue", "load balancer", "microservice", "latency", "availability", "rate limit"]
        return self._keyword_score("System Design", words, signals)

    def _score_database(self, words: str) -> CompetencyScore:
        signals = ["sql", "index", "join", "transaction", "normalization", "query", "postgres", "mongodb"]
        return self._keyword_score("Database Knowledge", words, signals)

    def _score_practices(self, words: str) -> CompetencyScore:
        signals = ["git", "code review", "ci", "cd", "test", "deploy", "monitoring", "documentation"]
        return self._keyword_score("Software Development Practices", words, signals)

    def _score_communication(self) -> CompetencyScore:
        answers = [turn.answer for turn in self.turns if turn.answer.strip()]
        if not answers:
            return CompetencyScore("Communication Skills", 20, ["No answers were provided."])
        avg_words = sum(len(answer.split()) for answer in answers) / len(answers)
        weak_count = sum(self._is_non_answer(answer) for answer in answers)
        structure_words = Counter()
        for answer in answers:
            for word in ["first", "then", "because", "for example", "result", "therefore"]:
                if word in answer.lower():
                    structure_words[word] += 1
        score = 30 + min(35, int(avg_words / 2.4)) + min(22, len(structure_words) * 5) - weak_count * 8
        evidence = [
            f"Average answer length was {avg_words:.0f} words.",
            f"Structured explanation markers detected: {', '.join(structure_words.keys()) or 'none'}.",
            f"Non-substantive answers detected: {weak_count}."
        ]
        return CompetencyScore("Communication Skills", max(12, min(score, 95)), evidence)

    def _keyword_score(self, name: str, words: str, signals: list[str]) -> CompetencyScore:
        matched = [signal for signal in signals if signal in words]
        total_words = len(words.split())
        quality_score, quality_evidence = self._answer_quality_score()
        if total_words < 40:
            base = 12
        elif total_words < 120:
            base = 22
        else:
            base = 30
        score = base + quality_score + len(matched) * 7
        if total_words > 350:
            score += 6
        evidence = [f"Matched evidence signals: {', '.join(matched)}."] if matched else [
            "No meaningful evidence was found in the interview answers for this competency."
        ]
        evidence.extend(quality_evidence)
        return CompetencyScore(name, max(10, min(score, 94)), evidence)

    def _answer_quality_score(self) -> tuple[int, list[str]]:
        answers = [turn.answer for turn in self.turns if turn.answer.strip()]
        if not answers:
            return 0, ["No answers available for quality scoring."]
        joined = " ".join(answer.lower() for answer in answers)
        avg_words = sum(len(answer.split()) for answer in answers) / len(answers)
        weak_count = sum(self._is_non_answer(answer) for answer in answers)
        practical_hits = sum(term in joined for term in [
            "implemented", "designed", "built", "deployed", "debugged", "optimized", "tested", "reviewed",
            "monitored", "measured", "validated", "production", "root cause", "trade-off", "tradeoff",
        ])
        explanation_hits = sum(term in joined for term in [
            "because", "first", "then", "after", "result", "for example", "edge case", "failure", "bottleneck",
        ])
        score = 0
        if avg_words >= 35:
            score += 10
        if avg_words >= 70:
            score += 8
        score += min(16, practical_hits * 3)
        score += min(12, explanation_hits * 2)
        score -= weak_count * 7
        evidence = [
            f"Answer quality average length: {avg_words:.0f} words.",
            f"Practical evidence markers: {practical_hits}; explanation markers: {explanation_hits}; weak answers: {weak_count}.",
        ]
        return max(0, min(score, 38)), evidence

    def _is_non_answer(self, answer: str) -> bool:
        clean = re.sub(r"[^a-zA-Z ]", "", answer).strip().lower()
        return clean in {"no", "nope", "na", "n a", "none", "nothing", "dont know", "i dont know", "not sure"} or len(clean.split()) <= 2

    def _strengths_and_weaknesses(
        self, skills: list[SkillAssessment], competencies: list[CompetencyScore]
    ) -> tuple[list[str], list[str]]:
        strengths = [
            f"{item.skill}: {item.depth} evidence with score {item.score}."
            for item in skills if item.score >= 70
        ]
        strengths.extend(
            f"{item.name}: scored {item.score} with supporting response evidence."
            for item in competencies if item.score >= 75
        )
        weaknesses = [
            f"{item.name}: score {item.score}; requires deeper verification."
            for item in competencies if item.score < 60
        ]
        if not strengths:
            strengths.append("No strong technical strengths were demonstrated in the interview answers.")
        if not weaknesses:
            weaknesses.append("No critical weakness detected from the available transcript.")
        return strengths[:6], weaknesses[:6]

    def _observations(self, skills: list[SkillAssessment], competencies: list[CompetencyScore]) -> list[str]:
        observed_skills = ", ".join(item.skill for item in skills)
        avg = round(sum(item.score for item in competencies) / max(len(competencies), 1))
        return [
            f"Observed skill areas: {observed_skills}.",
            f"Overall competency average: {avg}/100.",
            f"Interview difficulty adapted to {self.difficulty} by the final question.",
            "Scores are evidence-backed by the transcript and should support, not replace, human HR judgment.",
        ]

    def _confidence_score(self) -> int:
        answers = [turn.answer.lower() for turn in self.turns]
        if not answers:
            return 0
        confident = sum(any(word in answer for word in ["i built", "i implemented", "i designed", "i led", "i resolved"]) for answer in answers)
        hedging = sum(any(word in answer for word in ["maybe", "not sure", "i think", "i guess"]) for answer in answers)
        weak_count = sum(self._is_non_answer(answer) for answer in answers)
        length_factor = min(25, sum(len(answer.split()) for answer in answers) // max(len(answers), 1) // 3)
        return max(10, min(95, 45 + confident * 8 - hedging * 6 - weak_count * 7 + length_factor))

    def _technical_depth_score(self, skills: list[SkillAssessment], competencies: list[CompetencyScore]) -> int:
        skill_avg = round(sum(skill.score for skill in skills) / max(len(skills), 1))
        technical = [item.score for item in competencies if item.name != "Communication Skills"]
        competency_avg = round(sum(technical) / max(len(technical), 1))
        return round((skill_avg * 0.55) + (competency_avg * 0.45))









