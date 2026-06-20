# MESHASEC AI HR Interview Agent 2.0

A standalone Windows desktop interview platform with resume-driven technical questioning, voice interviews, webcam analytics, integrity monitoring, evidence-based evaluation, enterprise PDF reporting, email automation, and downloadable interview packages.

## Install and Run

End users should use the Windows installer in `installer_output` or launch `dist\AI HR Agent.exe`. No terminal or command prompt is required.

## Enterprise Interview Flow

1. Enter candidate and HR details.
2. Choose Shanmukh or Yashna and select Normal or Assisted mode.
3. Upload a PDF/DOCX resume. Parsing runs privately behind a loading indicator.
4. Complete camera, microphone, and audio readiness checks.
5. Conduct a Zoom-style interview with resume-based dynamic questions.
6. Record voice answers with Start Recording / Stop Recording.
7. Generate the final evidence-based report and email the enhanced PDF to HR.
8. Download a ZIP interview package containing audio, video, transcript, integrity analysis, confidence analysis, and final report.

## Feature Modules

Modules can be enabled or disabled in Settings:

- Voice recording and speech-to-text transcripts
- Webcam confidence and engagement analysis
- Interview integrity monitoring
- Local recording package generation

Confidence and emotion metrics are supportive indicators only and must not be treated as final hiring criteria.

## Local Data

Interview artifacts are stored under:

`Documents\MESHASEC AI HR Interviews\<Candidate>\<Timestamp>`

Each enabled session may contain:

- `audio\question_XX.wav`
- `video\candidate_camera.avi`
- `transcript.txt`
- `confidence_report.json`
- `integrity_report.json`
- `integrity_report.pdf`
- `final_report.pdf`
- A downloadable ZIP package

## Email

For Gmail use:

- SMTP host: `smtp.gmail.com`
- Port: `587`
- TLS: enabled
- Sender email: Gmail address
- Password: Gmail App Password

## Developer Build

`build_exe.bat` installs dependencies and builds the standalone executable. Compile `installer\AI_HR_Agent.iss` with Inno Setup to create the installer wizard.

## Privacy and Compliance

The application requests explicit camera and microphone readiness before interview start. Recording, confidence analysis, and integrity monitoring are configurable. Production deployment should include organizational consent, retention, access-control, and applicable employment/privacy-law review.

## Adaptive AI Questions

The interview always contains exactly 10 questions. Question 1 is common to every candidate; questions 2-10 are generated from resume context and prior answers. If the AI service is unavailable, the built-in adaptive question bank is used automatically.

Configure AI credentials only in the runtime environment, never in source code or UI:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

Voice playback can be enabled or disabled during the session. The avatar animation is provider-neutral and retains the existing HR image as its fallback.

## Evidence-Based Scoring

The evaluator reviews every answer in relation to its question. When AI evaluation is configured, the complete transcript is assessed for correctness, relevance, conceptual depth, implementation evidence, reasoning, trade-offs, validation, and outcomes. If AI evaluation is unavailable, a deterministic per-answer rubric produces question-numbered evidence. Keyword mentions alone do not earn high scores.

The ten-question plan intentionally covers distinct relevant domains such as resume projects, programming fundamentals, debugging, networking, cloud infrastructure, databases, security, testing, delivery, and integrated system design.
