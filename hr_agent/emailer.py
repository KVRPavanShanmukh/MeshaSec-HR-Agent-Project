import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass
class EmailSettings:
    smtp_host: str
    smtp_port: int
    sender_email: str
    sender_password: str
    hr_email: str
    use_tls: bool = True


def send_report_email(settings: EmailSettings, subject: str, report_text: str, pdf_path: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = settings.sender_email
    message["To"] = settings.hr_email
    message["Subject"] = subject
    message.set_content(report_text)
    message.add_attachment(
        report_text.encode("utf-8"),
        maintype="text",
        subtype="plain",
        filename="technical_interview_report.txt",
    )
    if pdf_path:
        from pathlib import Path
        path = Path(pdf_path)
        if path.exists():
            message.add_attachment(
                path.read_bytes(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.use_tls:
            smtp.starttls()
        smtp.login(settings.sender_email, settings.sender_password)
        smtp.send_message(message)
