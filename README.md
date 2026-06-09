# AI HR Technical Interview Agent

A downloadable enterprise desktop HR interview assistant built with Python and Tkinter.

The app interviews technical candidates through an enterprise-style guided workflow, adapts follow-up questions based on resume content and answers, extracts skills, scores technical competencies with evidence, generates a branded HR report, and emails the report to a human HR contact.

## Features

- Adaptive technical interview flow
- Enterprise multi-screen interface: welcome, resume upload, preparation, live interview, completion, dashboard
- Mandatory PDF/DOCX resume upload
- Camera and microphone readiness checks
- AI interviewer speech output and microphone answer capture
- Fullscreen-only interview experience
- Live camera preview during preparation and interview
- Human-like AI interviewer avatar and persona
- Start Reading / Stop Reading voice playback controls
- Natural pronunciation handling for technical terms such as CI/CD
- Shanmukh male interviewer and Yashna female interviewer options
- Normal user and physically handicapped user interview environments
- Skill extraction for languages, frameworks, databases, cloud tools, and development practices
- Technical depth verification through progressive follow-up questions
- Communication and explanation analysis
- Evidence-backed competency scoring
- Candidate analytics dashboard with score visualizations
- Branded enterprise PDF report generation based only on interview answers
- SMTP email delivery to HR
- Optional OpenAI integration through `OPENAI_API_KEY`
- Local heuristic fallback when no API key is configured

## Run From Source

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Optional AI Setup

Set an OpenAI API key before launching:

```powershell
$env:OPENAI_API_KEY="your-api-key"
python main.py
```

Without an API key, the app still runs using built-in interview logic and scoring heuristics.

## Email Setup

Use the Settings tab in the app:

- SMTP Host: `smtp.gmail.com` for Gmail
- SMTP Port: `587` for Gmail with TLS
- Sender Email: your Gmail address, for example `yourname@gmail.com`
- SMTP/App Password: your Gmail app password
- HR recipient email: enter this in the Candidate tab as Human HR Email

For Gmail, create an app password instead of using your normal account password.

Do not enter your email address in SMTP Host. The SMTP Host field must contain a mail server name such as `smtp.gmail.com`.

## Company Logo

Place your company logo in the `assets` folder with one of these names:

```text
assets\company_logo.png
assets\company_logo.jpg
assets\logo.png
assets\logo.jpg
```

The app automatically replaces the sidebar text logo with the provided image on launch.

## Report Policy

Resume content is used only to personalize interview questions. Final scores, strengths, weaknesses, recommendations, and report evidence are generated solely from the interview answers.

## Voice Controls

During the live interview:

- Normal mode uses a Zoom-style dynamic interview and reads each question automatically.
- Physically handicapped mode shows `Start Reading` and `Stop Reading` controls.
- `Start Reading` reads the current question only.
- `Stop Reading` interrupts interviewer voice playback.
- The interviewer waits for `Submit Answer` before moving to the next question.
- Voice speed can be adjusted in Email Settings under Interviewer Voice.

## Meeting Workflow

The app includes a Meeting Workflow screen for the proposed Zoom/Google Meet recruitment flow. A production auto-join meeting agent requires a backend bot service with Zoom/Meet SDK/API approval, calendar integration, compliance review, and secure meeting recording/transcription handling.

## Build A Windows Executable

Build:

```powershell
build_exe.bat
```

The executable will be created in:

```text
dist\AI HR Agent.exe
```

## Project Structure

```text
main.py
hr_agent/
  __init__.py
  agent.py
  emailer.py
  media.py
  models.py
  pdf_report.py
  report.py
  resume_parser.py
  storage.py
```
=======