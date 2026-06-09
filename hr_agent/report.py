from .models import InterviewReport


def render_report(report: InterviewReport) -> str:
    profile = report.profile
    lines = [
        "AI HR Technical Interview Report",
        "=" * 34,
        "",
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
        f"Candidate: {profile.name or 'Not provided'}",
        f"Candidate Email: {profile.email or 'Not provided'}",
        f"Role: {profile.role or 'Not provided'}",
        f"Experience: {profile.experience_years or 'Not provided'}",
        f"Recommendation: {report.recommendation}",
        f"Overall Interview Score: {report.overall_score}/100",
        f"Technical Depth Score: {report.technical_depth_score}/100",
        f"Confidence Score: {report.confidence_score}/100",
        "",
        "Evaluation Basis",
        "-" * 16,
        "This report is generated solely from the candidate's interview answers and transcript evidence.",
        "",
        "Competency Scores",
        "-" * 17,
    ]

    for item in report.competencies:
        lines.append(f"- {item.name}: {item.score}/100")
        for evidence in item.evidence:
            lines.append(f"  Evidence: {evidence}")

    lines.extend(["", "Skill-Wise Assessment", "-" * 21])
    for skill in report.skills:
        lines.append(f"- {skill.skill}: {skill.score}/100 ({skill.depth})")
        for evidence in skill.evidence:
            lines.append(f"  Evidence: {evidence}")

    lines.extend(["", "Technical Strengths", "-" * 19])
    lines.extend(f"- {item}" for item in report.strengths)

    lines.extend(["", "Technical Weaknesses", "-" * 20])
    lines.extend(f"- {item}" for item in report.weaknesses)

    lines.extend(["", "Key Observations", "-" * 16])
    lines.extend(f"- {item}" for item in report.observations)

    if report.confidence_summary:
        lines.extend(["", "Confidence & Engagement Analysis", "-" * 32])
        for key, value in report.confidence_summary.items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    if report.integrity_summary:
        lines.extend(["", "Interview Integrity Report", "-" * 26])
        for key, value in report.integrity_summary.items():
            if key == "events" and isinstance(value, list):
                lines.append("- Events:")
                lines.extend(f"  - {event}" for event in value)
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    if report.recording_references:
        lines.extend(["", "Recording References", "-" * 20])
        for key, value in report.recording_references.items():
            if isinstance(value, list):
                lines.append(f"- {key.replace('_', ' ').title()}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    lines.extend(["", "Interview Transcript", "-" * 20])
    for index, turn in enumerate(report.turns, start=1):
        lines.append(f"{index}. Difficulty: {turn.difficulty} | Focus: {turn.focus_area}")
        lines.append(f"Q: {turn.question}")
        lines.append(f"A: {turn.answer or '[No answer]'}")
        if turn.evidence:
            lines.append("Evidence:")
            lines.extend(f"  - {item}" for item in turn.evidence)
        lines.append("")

    return "\n".join(lines).strip() + "\n"
