from pathlib import Path

from .models import InterviewReport
from .report import render_report


BRAND_COLOR = "#183A59"
ACCENT_COLOR = "#2F80ED"


def export_enterprise_pdf(report: InterviewReport, output_path: str) -> str:
    path = Path(output_path)
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        fallback = path.with_suffix(".html")
        fallback.write_text(_render_html(report), encoding="utf-8")
        raise RuntimeError(f"ReportLab is required for PDF export. HTML fallback created at {fallback}") from exc

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=36)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", fontSize=20, leading=24, textColor=colors.HexColor(BRAND_COLOR), spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", fontSize=13, leading=16, textColor=colors.HexColor(BRAND_COLOR), spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodySmall", fontSize=9, leading=12))
    story = []

    story.append(Paragraph("MESHASEC AI HR Interview Report", styles["BrandTitle"]))
    story.append(Paragraph(f"Candidate: {report.profile.name or 'Not provided'}", styles["Normal"]))
    story.append(Paragraph(f"Role: {report.profile.role or 'Not provided'} | Generated: {report.generated_at:%Y-%m-%d %H:%M}", styles["Normal"]))
    story.append(Paragraph(f"Recommendation: <b>{report.recommendation}</b> | Overall Score: <b>{report.overall_score}/100</b>", styles["Normal"]))
    story.append(Spacer(1, 10))

    _score_chart(story, report, Table, TableStyle, colors, inch)

    story.append(Paragraph("Evaluation Basis", styles["Section"]))
    story.append(Paragraph("This PDF report is generated solely from the candidate's interview answers and transcript evidence. Resume content may guide the interview questions, but it is not counted as assessment evidence.", styles["BodySmall"]))

    story.append(Paragraph("Competency Scores", styles["Section"]))
    rows = [["Competency", "Score", "Evidence"]]
    for item in report.competencies:
        rows.append([item.name, f"{item.score}/100", "\n".join(item.evidence[:2])])
    table = Table(rows, colWidths=[1.8 * inch, 0.8 * inch, 3.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND_COLOR)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d7dee8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
    ]))
    story.append(table)

    _bullet_section(story, "Strengths", report.strengths, styles, Paragraph)
    _bullet_section(story, "Weaknesses", report.weaknesses, styles, Paragraph)
    _bullet_section(story, "Key Observations", report.observations, styles, Paragraph)

    story.append(Paragraph("Interview Transcript", styles["Section"]))
    for index, turn in enumerate(report.turns, start=1):
        story.append(Paragraph(f"<b>{index}. {turn.focus_area} ({turn.difficulty})</b>", styles["BodySmall"]))
        story.append(Paragraph("Q: " + _escape(turn.question), styles["BodySmall"]))
        story.append(Paragraph("A: " + _escape(turn.answer), styles["BodySmall"]))
        story.append(Spacer(1, 5))

    doc.build(story, onFirstPage=_page_brand, onLaterPages=_page_brand)
    return str(path)


def _score_chart(story, report, Table, TableStyle, colors, inch) -> None:
    rows = [["Metric", "Score", "Visual"]]
    metrics = [
        ("Overall Interview Score", report.overall_score),
        ("Technical Depth", report.technical_depth_score),
        ("Communication", _competency(report, "Communication Skills")),
        ("Confidence", report.confidence_score),
    ]
    for label, score in metrics:
        bars = "█" * max(1, score // 10) + "░" * max(0, 10 - score // 10)
        rows.append([label, f"{score}/100", bars])
    table = Table(rows, colWidths=[2.4 * inch, 1.0 * inch, 2.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(ACCENT_COLOR)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d7dee8")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(table)


def _bullet_section(story, title: str, items: list[str], styles, Paragraph) -> None:
    story.append(Paragraph(title, styles["Section"]))
    for item in items:
        story.append(Paragraph("- " + _escape(item), styles["BodySmall"]))


def _page_brand(canvas_obj, doc) -> None:
    canvas_obj.saveState()
    canvas_obj.setFillColor(BRAND_COLOR)
    canvas_obj.rect(0, 808, 596, 34, fill=True, stroke=False)
    canvas_obj.setFillColor("white")
    canvas_obj.setFont("Helvetica-Bold", 10)
    canvas_obj.drawString(36, 820, "MESHASEC HR INTELLIGENCE")
    canvas_obj.setFillColor("#6b7280")
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawRightString(560, 22, f"Page {doc.page}")
    canvas_obj.restoreState()


def _competency(report: InterviewReport, name: str) -> int:
    for item in report.competencies:
        if item.name == name:
            return item.score
    return 0


def _render_html(report: InterviewReport) -> str:
    text = render_report(report)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AI HR Report</title>
<style>body{{font-family:Segoe UI,Arial;margin:40px;color:#172033}}h1{{color:{BRAND_COLOR}}}pre{{white-space:pre-wrap}}</style>
</head><body><h1>MESHASEC AI HR Interview Report</h1><pre>{_escape(text)}</pre></body></html>"""


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
