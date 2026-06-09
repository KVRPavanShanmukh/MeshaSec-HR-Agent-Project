import json
import os
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from hr_agent.agent import TechnicalInterviewAgent
from hr_agent.confidence import ConfidenceAnalyzer
from hr_agent.emailer import EmailSettings, send_report_email
from hr_agent.integrity import IntegrityMonitor
from hr_agent.media import MediaManager
from hr_agent.models import CandidateProfile, ResumeInsight
from hr_agent.pdf_report import export_enterprise_pdf
from hr_agent.recording import InterviewRecorder
from hr_agent.report import render_report
from hr_agent.resume_parser import parse_resume
from hr_agent.storage import save_session


APP_TITLE = "MESHASEC AI HR Interview Agent"
CONFIG_FILE = Path.home() / ".ai_hr_agent_config.json"
BRAND = "#005F73"
ACCENT = "#F97316"
SUCCESS = "#0A9396"
DANGER = "#AE2012"
SURFACE = "#ffffff"
BG = "#E6F7FB"


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


class EnterpriseHRApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.attributes("-fullscreen", True)
        self.state("zoomed")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._close_app)
        self.bind("<Escape>", lambda event: "break")

        self.media = MediaManager()
        self.recorder = InterviewRecorder()
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.integrity_monitor = IntegrityMonitor()
        self.agent = TechnicalInterviewAgent()
        self.resume = ResumeInsight()
        self.report = None
        self.report_text = ""
        self.current_question = ""
        self.current_focus = "Resume Introduction"
        self.camera_image = None
        self.logo_image = None
        self.avatar_image = None
        self.camera_running = False
        self.recording = False
        self.device_status = None
        self.session_dir = None
        self.video_recording_started = False
        self.last_confidence_sample = 0.0
        self.last_focus_loss = 0.0
        self.last_webcam_issue = 0.0

        self.profile_vars = {
            "name": tk.StringVar(),
            "email": tk.StringVar(),
            "role": tk.StringVar(value="Software Engineer"),
            "experience_years": tk.StringVar(),
            "hr_email": tk.StringVar(),
            "resume_path": tk.StringVar(),
            "max_questions": tk.IntVar(value=10),
            "voice_rate": tk.IntVar(value=155),
            "interviewer": tk.StringVar(value="Shanmukh"),
            "interview_mode": tk.StringVar(value="normal"),
        }
        self.email_vars = {
            "smtp_host": tk.StringVar(value="smtp.gmail.com"),
            "smtp_port": tk.IntVar(value=587),
            "sender_email": tk.StringVar(),
            "sender_password": tk.StringVar(),
            "use_tls": tk.BooleanVar(value=True),
        }
        self.feature_vars = {
            "voice_interview": tk.BooleanVar(value=True),
            "confidence_analysis": tk.BooleanVar(value=True),
            "integrity_monitoring": tk.BooleanVar(value=True),
            "recording_package": tk.BooleanVar(value=True),
        }
        self.screen = tk.StringVar(value="welcome")
        self.bind("<FocusOut>", self._on_focus_lost)
        self.bind("<FocusIn>", self._on_focus_in)

        self._style()
        self._load_config()
        self._layout()
        self.show_screen("welcome")
        self.after(1000, self._fullscreen_watchdog)

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE, relief="flat")
        style.configure("Brand.TFrame", background=BRAND)
        style.configure("TLabel", background=BG, foreground="#172033", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=SURFACE, foreground="#172033", font=("Segoe UI", 10))
        style.configure("Hero.TLabel", background=SURFACE, foreground=BRAND, font=("Segoe UI", 26, "bold"))
        style.configure("H1.TLabel", background=BG, foreground=BRAND, font=("Segoe UI", 20, "bold"))
        style.configure("H2.TLabel", background=SURFACE, foreground=BRAND, font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", background=SURFACE, foreground="#607086", font=("Segoe UI", 9))
        style.configure("Nav.TLabel", background=BRAND, foreground="#dbeafe", font=("Segoe UI", 10))
        style.configure("Logo.TLabel", background=BRAND, foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background=ACCENT, padding=(14, 9))
        style.map("Accent.TButton", background=[("active", "#EA580C")])
        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background=SUCCESS, padding=(14, 9))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background=DANGER, padding=(14, 9))
        style.configure("Horizontal.TProgressbar", troughcolor="#d7e2ef", background=ACCENT, thickness=8)

    def _layout(self) -> None:
        self.sidebar = ttk.Frame(self, style="Brand.TFrame", width=260)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._brand_header()
        ttk.Label(self.sidebar, text="AI HR Intelligence", style="Nav.TLabel").pack(anchor="w", padx=22, pady=(0, 28))
        self.nav_buttons = {}
        for key, label in [
            ("welcome", "Welcome"),
            ("resume", "Resume Upload"),
            ("prep", "Interview Preparation"),
            ("live", "Live Interview"),
            ("complete", "Completion"),
            ("dashboard", "Report Dashboard"),
            ("meeting", "Meeting Workflow"),
            ("settings", "Email Settings"),
        ]:
            button = tk.Button(
                self.sidebar,
                text=label,
                anchor="w",
                relief="flat",
                bd=0,
                padx=22,
                pady=13,
                bg=BRAND,
                fg="#E0FBFC",
                activebackground="#0A9396",
                activeforeground="#ffffff",
                font=("Segoe UI", 10, "bold"),
                command=lambda item=key: self.show_screen(item),
            )
            button.pack(fill="x")
            self.nav_buttons[key] = button
        ttk.Label(
            self.sidebar,
            text="Voice, camera, resume intelligence, analytics, and HR-ready PDF reporting.",
            style="Nav.TLabel",
            wraplength=210,
        ).pack(side="bottom", padx=22, pady=28)

        self.content = ttk.Frame(self, padding=24)
        self.content.pack(side="left", fill="both", expand=True)
        self.screens = {}
        for name in ["welcome", "resume", "prep", "live", "complete", "dashboard", "meeting", "settings"]:
            frame = ttk.Frame(self.content)
            frame.grid(row=0, column=0, sticky="nsew")
            self.screens[name] = frame
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        self._welcome_screen()
        self._resume_screen()
        self._prep_screen()
        self._live_screen()
        self._complete_screen()
        self._dashboard_screen()
        self._meeting_screen()
        self._settings_screen()

    def _brand_header(self) -> None:
        logo_path = self._find_company_logo()
        if logo_path:
            try:
                from PIL import Image, ImageTk
                image = Image.open(logo_path)
                image.thumbnail((205, 86))
                self.logo_image = ImageTk.PhotoImage(image)
                tk.Label(self.sidebar, image=self.logo_image, bg=BRAND).pack(anchor="w", padx=22, pady=(24, 6))
                return
            except Exception:
                pass
        ttk.Label(self.sidebar, text="MESHASEC", style="Logo.TLabel").pack(anchor="w", padx=22, pady=(26, 4))

    def _find_company_logo(self) -> Path | None:
        assets = resource_path("assets")
        for name in ["company_logo.png", "company_logo.jpg", "company_logo.jpeg", "logo.png", "logo.jpg", "logo.jpeg"]:
            path = assets / name
            if path.exists():
                return path
        return None

    def show_screen(self, name: str) -> None:
        if name == "live" and not self._can_enter_live():
            return
        if name in {"complete", "dashboard"} and not self.report:
            messagebox.showinfo(APP_TITLE, "Complete the interview first to view reports and analytics.")
            return
        self.screens[name].tkraise()
        self.screen.set(name)
        for key, button in self.nav_buttons.items():
            active = key == name
            button.configure(bg=ACCENT if active else BRAND, fg="#ffffff" if active else "#E0FBFC")
        self._enforce_fullscreen()

    def _enforce_fullscreen(self) -> None:
        if not bool(self.attributes("-fullscreen")):
            self.attributes("-fullscreen", True)

    def _fullscreen_watchdog(self) -> None:
        self._enforce_fullscreen()
        self.after(1000, self._fullscreen_watchdog)

    def _screen_title(self, parent, title: str, subtitle: str) -> None:
        ttk.Label(parent, text=title, style="H1.TLabel").pack(anchor="w")
        ttk.Label(parent, text=subtitle, background=BG, foreground="#607086", font=("Segoe UI", 10), wraplength=980).pack(anchor="w", pady=(4, 18))

    def _card(self, parent, padding=20):
        card = ttk.Frame(parent, style="Card.TFrame", padding=padding)
        card.pack(fill="both", expand=False, pady=(0, 16))
        return card

    def _welcome_screen(self) -> None:
        frame = self.screens["welcome"]
        hero = ttk.Frame(frame, style="Card.TFrame", padding=30)
        hero.pack(fill="both", expand=True)
        ttk.Label(hero, text="AI HR Interview Partner", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Choose Shanmukh or Yashna as your AI HR interviewer for resume-aware technical screening, communication assessment, and executive hiring reports.",
            style="Card.TLabel",
            font=("Segoe UI", 12),
            wraplength=820,
        ).pack(anchor="w", pady=(12, 22))
        metrics = ttk.Frame(hero, style="Card.TFrame")
        metrics.pack(fill="x", pady=(8, 28))
        for title, value in [
            ("Interview Flow", "10+ adaptive questions"),
            ("Input", "PDF/DOCX resume + voice"),
            ("Validation", "Camera and mic gated"),
            ("Output", "PDF analytics report"),
        ]:
            box = ttk.Frame(metrics, style="Card.TFrame", padding=16)
            box.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ttk.Label(box, text=value, style="H2.TLabel").pack(anchor="w")
            ttk.Label(box, text=title, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Button(hero, text="Start Candidate Setup", style="Accent.TButton", command=lambda: self.show_screen("resume")).pack(anchor="w")

    def _resume_screen(self) -> None:
        frame = self.screens["resume"]
        self._screen_title(frame, "Resume Upload", "Upload a PDF or DOCX resume. The interview is generated from detected skills, projects, technologies, and experience.")
        form = self._card(frame)
        for row, (label, key) in enumerate([
            ("Candidate Name", "name"),
            ("Candidate Email", "email"),
            ("Role / Position", "role"),
            ("Experience Years", "experience_years"),
            ("Human HR Email", "hr_email"),
        ]):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=8)
            ttk.Entry(form, textvariable=self.profile_vars[key], width=56).grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=8)
        ttk.Label(form, text="Minimum Questions", style="Card.TLabel").grid(row=5, column=0, sticky="w", pady=8)
        ttk.Spinbox(form, from_=10, to=20, textvariable=self.profile_vars["max_questions"], width=8).grid(row=5, column=1, sticky="w", padx=(14, 0), pady=8)
        form.columnconfigure(1, weight=1)

        options = self._card(frame)
        ttk.Label(options, text="Interview Setup", style="H2.TLabel").pack(anchor="w")
        ttk.Label(options, text="AI Interviewer Voice", style="Card.TLabel").pack(anchor="w", pady=(10, 4))
        ttk.Radiobutton(options, text="Shanmukh - Male voice", variable=self.profile_vars["interviewer"], value="Shanmukh").pack(anchor="w")
        ttk.Radiobutton(options, text="Yashna - Female voice", variable=self.profile_vars["interviewer"], value="Yashna").pack(anchor="w")
        ttk.Label(options, text="Candidate Environment", style="Card.TLabel").pack(anchor="w", pady=(14, 4))
        ttk.Radiobutton(options, text="Normal user - Zoom-style dynamic interview", variable=self.profile_vars["interview_mode"], value="normal").pack(anchor="w")
        ttk.Radiobutton(options, text="Physically handicapped user - assisted reading controls", variable=self.profile_vars["interview_mode"], value="accessible").pack(anchor="w")

        upload = self._card(frame)
        ttk.Label(upload, text="Mandatory Resume", style="H2.TLabel").pack(anchor="w")
        row = ttk.Frame(upload, style="Card.TFrame")
        row.pack(fill="x", pady=(10, 8))
        ttk.Entry(row, textvariable=self.profile_vars["resume_path"]).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Choose PDF/DOCX", command=self.choose_resume).pack(side="left", padx=(10, 0))
        self.resume_progress = ttk.Progressbar(upload, mode="indeterminate")
        self.resume_progress.pack(fill="x", pady=(12, 4))
        self.resume_status = ttk.Label(upload, text="Resume not uploaded yet.", style="Muted.TLabel")
        self.resume_status.pack(anchor="w")
        ttk.Button(frame, text="Continue To Device Checks", style="Accent.TButton", command=lambda: self.show_screen("prep")).pack(anchor="e")

    def _prep_screen(self) -> None:
        frame = self.screens["prep"]
        self._screen_title(frame, "Interview Preparation", "Camera and microphone access are required before the AI interview can begin.")
        grid = ttk.Frame(frame)
        grid.pack(fill="x")
        self.camera_status = self._status_card(grid, "Camera Permission", "Not checked")
        self.microphone_status = self._status_card(grid, "Microphone Permission", "Not checked")
        self.audio_test_status = self._status_card(grid, "Audio Test", "Pending")

        preview = self._card(frame)
        ttk.Label(preview, text="Camera Preview", style="H2.TLabel").pack(anchor="w")
        self.camera_label = tk.Label(preview, text="Run device check to preview camera", bg="#102030", fg="#dbeafe", height=22, font=("Segoe UI", 11))
        self.camera_label.pack(fill="both", expand=True, pady=(10, 0))
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Run Camera & Microphone Check", style="Accent.TButton", command=self.run_device_check).pack(side="left")
        ttk.Button(actions, text="Test Microphone", command=self.test_microphone).pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Begin Live Interview", style="Success.TButton", command=self.begin_interview).pack(side="right")

    def _status_card(self, parent, title: str, status: str) -> ttk.Label:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=(0, 16))
        ttk.Label(card, text=title, style="H2.TLabel").pack(anchor="w")
        label = ttk.Label(card, text=status, style="Muted.TLabel")
        label.pack(anchor="w", pady=(8, 0))
        return label

    def _live_screen(self) -> None:
        frame = self.screens["live"]
        self._screen_title(frame, "Live AI Interview Session", "Normal mode uses a Zoom-style dynamic interview. Assisted mode shows Start Reading and Stop Reading controls.")
        room = ttk.Frame(frame)
        room.pack(fill="both", expand=True)
        left = ttk.Frame(room, style="Card.TFrame", padding=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        right = ttk.Frame(room, style="Card.TFrame", padding=16, width=310)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self.interviewer_title = ttk.Label(left, text="AI HR Interviewer", style="H2.TLabel")
        self.interviewer_title.pack(anchor="w")
        video_grid = ttk.Frame(left, style="Card.TFrame")
        video_grid.pack(fill="x", pady=(8, 12))
        self.agent_panel = tk.Label(video_grid, text="AI Interviewer", bg="#edf4fb", fg=BRAND, width=54, height=16)
        self.agent_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.user_panel = tk.Label(video_grid, text="Candidate camera preview", bg="#102030", fg="#dbeafe", width=54, height=16)
        self.user_panel.pack(side="left", fill="both", expand=True)
        self._load_avatar()

        self.question_box = tk.Text(left, height=6, wrap="word", font=("Segoe UI", 12), bg="#f8fbff", relief="flat")
        self.question_box.pack(fill="x", pady=(10, 14))
        self.question_box.configure(state="disabled")
        ttk.Label(left, text="Candidate Response", style="H2.TLabel").pack(anchor="w")
        self.answer_box = tk.Text(left, height=12, wrap="word", font=("Segoe UI", 11), bg="#ffffff")
        self.answer_box.pack(fill="both", expand=True, pady=(10, 14))
        actions = ttk.Frame(left, style="Card.TFrame")
        actions.pack(fill="x")
        self.assist_controls = ttk.Frame(actions, style="Card.TFrame")
        self.assist_controls.pack(side="left")
        self.speak_button = ttk.Button(self.assist_controls, text="Start Reading", command=self.start_reading)
        self.speak_button.pack(side="left")
        self.stop_speak_button = ttk.Button(self.assist_controls, text="Stop Reading", command=self.stop_reading)
        self.stop_speak_button.pack(side="left", padx=(10, 0))
        self.record_button = ttk.Button(actions, text="Start Recording", command=self.start_voice_recording)
        self.record_button.pack(side="left", padx=(10, 0))
        self.stop_record_button = ttk.Button(actions, text="Stop Recording", command=self.stop_voice_recording, state="disabled")
        self.stop_record_button.pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Submit Answer", style="Accent.TButton", command=self.submit_answer).pack(side="right")
        self.voice_status = ttk.Label(left, text="Voice status: ready", style="Muted.TLabel")
        self.voice_status.pack(anchor="w", pady=(8, 0))

        ttk.Label(right, text="Session", style="H2.TLabel").pack(anchor="w")
        self.supportive_label = ttk.Label(
            right,
            text="Confidence metrics are supportive indicators only, not final hiring criteria.",
            style="Muted.TLabel",
            wraplength=260,
        )
        self.supportive_label.pack(anchor="w", pady=(6, 8))
        self.progress = ttk.Progressbar(right, maximum=100)
        self.progress.pack(fill="x", pady=(10, 0))
        self.progress_label = ttk.Label(right, text="Question 0 / 10", style="Muted.TLabel")
        self.progress_label.pack(anchor="w", pady=(8, 16))
        ttk.Label(right, text="Live Transcript", style="H2.TLabel").pack(anchor="w")
        transcript_frame = ttk.Frame(right, style="Card.TFrame")
        transcript_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.transcript = tk.Text(transcript_frame, height=13, wrap="word", font=("Consolas", 9), bg="#f8fbff", relief="flat")
        self.transcript_scroll = ttk.Scrollbar(transcript_frame, orient="vertical", command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=self.transcript_scroll.set)
        self.transcript.pack(side="left", fill="both", expand=True)
        self.transcript_scroll.pack(side="right", fill="y")
        self.transcript.configure(state="disabled")

    def _complete_screen(self) -> None:
        frame = self.screens["complete"]
        self._screen_title(frame, "Interview Completion", "The interview is complete. Generate, review, email, or download the enterprise HR assessment report.")
        card = self._card(frame)
        self.completion_label = ttk.Label(card, text="No completed interview yet.", style="H2.TLabel")
        self.completion_label.pack(anchor="w")
        self.completion_summary = ttk.Label(card, text="", style="Card.TLabel", wraplength=760)
        self.completion_summary.pack(anchor="w", pady=(10, 0))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Button(row, text="Open Dashboard", style="Accent.TButton", command=lambda: self.show_screen("dashboard")).pack(side="left")
        ttk.Button(row, text="Save PDF Report", command=self.save_pdf_report).pack(side="left", padx=(10, 0))
        ttk.Button(row, text="Email Report To HR", command=self.email_report).pack(side="left", padx=(10, 0))
        ttk.Button(row, text="Download Interview Package", command=self.download_interview_package).pack(side="left", padx=(10, 0))

    def _dashboard_screen(self) -> None:
        frame = self.screens["dashboard"]
        self._screen_title(frame, "Final HR Report Dashboard", "This is the same HR-facing report, enhanced with visual performance analytics and transcript-based evidence.")
        top = ttk.Frame(frame)
        top.pack(fill="x")
        self.score_canvas = tk.Canvas(top, height=260, bg=SURFACE, highlightthickness=0)
        self.score_canvas.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self.radar_canvas = tk.Canvas(top, height=260, width=330, bg=SURFACE, highlightthickness=0)
        self.radar_canvas.pack(side="right", fill="y")
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(14, 12))
        ttk.Button(controls, text="Refresh Dashboard", style="Accent.TButton", command=self.refresh_dashboard).pack(side="left")
        ttk.Button(controls, text="Download PDF Report", command=self.save_pdf_report).pack(side="left", padx=(10, 0))
        ttk.Button(controls, text="Email Report", command=self.email_report).pack(side="left", padx=(10, 0))
        ttk.Button(controls, text="Download Interview Package", command=self.download_interview_package).pack(side="left", padx=(10, 0))
        report_frame = ttk.Frame(frame)
        report_frame.pack(fill="both", expand=True)
        self.report_view = tk.Text(report_frame, wrap="word", font=("Consolas", 9), bg=SURFACE)
        self.report_scroll = ttk.Scrollbar(report_frame, orient="vertical", command=self.report_view.yview)
        self.report_view.configure(yscrollcommand=self.report_scroll.set)
        self.report_view.pack(side="left", fill="both", expand=True)
        self.report_scroll.pack(side="right", fill="y")

    def _settings_screen(self) -> None:
        frame = self.screens["settings"]
        self._screen_title(frame, "Email Settings", "Configure SMTP delivery for Human HR report distribution.")
        card = self._card(frame)
        for row, (label, key) in enumerate([
            ("SMTP Host (example: smtp.gmail.com)", "smtp_host"),
            ("SMTP Port (Gmail TLS: 587)", "smtp_port"),
            ("Sender Email", "sender_email"),
            ("SMTP/App Password", "sender_password"),
        ]):
            ttk.Label(card, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=8)
            show = "*" if key == "sender_password" else ""
            ttk.Entry(card, textvariable=self.email_vars[key], width=56, show=show).grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=8)
        ttk.Checkbutton(card, text="Use TLS", variable=self.email_vars["use_tls"]).grid(row=4, column=1, sticky="w", padx=(14, 0), pady=8)
        card.columnconfigure(1, weight=1)
        ttk.Button(frame, text="Save Settings", style="Accent.TButton", command=self.save_config).pack(anchor="w")

        voice = self._card(frame)
        ttk.Label(voice, text="Interviewer Voice", style="H2.TLabel").pack(anchor="w")
        ttk.Label(voice, text="Speaking Speed", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Scale(voice, from_=120, to=190, variable=self.profile_vars["voice_rate"], orient="horizontal").pack(fill="x", pady=(6, 0))

        modules = self._card(frame)
        ttk.Label(modules, text="Feature Modules", style="H2.TLabel").pack(anchor="w")
        ttk.Checkbutton(modules, text="Voice interview recording and transcripts", variable=self.feature_vars["voice_interview"]).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(modules, text="Webcam confidence analysis", variable=self.feature_vars["confidence_analysis"]).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(modules, text="Interview integrity monitoring", variable=self.feature_vars["integrity_monitoring"]).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(modules, text="Local interview recording package", variable=self.feature_vars["recording_package"]).pack(anchor="w", pady=(6, 0))

    def _meeting_screen(self) -> None:
        frame = self.screens["meeting"]
        self._screen_title(
            frame,
            "Meeting Workflow",
            "Roadmap-ready workflow for Zoom and Google Meet: invite intake, auto-join, background interview capture, and separate reports for candidate and hiring manager.",
        )
        card = self._card(frame)
        ttk.Label(card, text="Proposed Enterprise Flow", style="H2.TLabel").pack(anchor="w")
        text = tk.Text(card, height=16, wrap="word", font=("Segoe UI", 11), bg="#f8fbff", relief="flat")
        text.pack(fill="both", expand=True, pady=(12, 0))
        text.insert(
            "1.0",
            "1. Hiring manager sends a Zoom or Google Meet invitation.\n"
            "2. The selected AI Talent Advisor joins the meeting using a bot connector account.\n"
            "3. The AI interviewer introduces itself, records the interview transcript, evaluates technical and HR signals, and monitors communication quality.\n"
            "4. After the call, separate reports are generated for the candidate and hiring manager.\n"
            "5. Reports are emailed automatically and session artifacts are persisted securely.\n\n"
            "Implementation note: true Zoom/Meet auto-join requires platform-specific SDK/API access, organization approval, calendar integration, and meeting-bot compliance review. This desktop build now includes the product workflow screen and reporting foundation; the meeting bot should be built as a backend service for production use.",
        )
        text.configure(state="disabled")

    def _load_avatar(self) -> None:
        avatar_name = "yashna_avatar.png" if self.interviewer_name() == "Yashna" else "shanmukh_avatar.png"
        avatar_path = resource_path(f"assets/{avatar_name}")
        if not avatar_path.exists():
            avatar_path = resource_path("assets/sai_avatar.png")
        if not avatar_path.exists():
            return
        try:
            from PIL import Image, ImageTk
            image = Image.open(avatar_path)
            image.thumbnail((620, 348))
            self.avatar_image = ImageTk.PhotoImage(image)
            self.agent_panel.configure(image=self.avatar_image, text="")
        except Exception:
            self.agent_panel.configure(text=f"{self.interviewer_name()} - AI HR Interviewer")

    def interviewer_name(self) -> str:
        return self.profile_vars["interviewer"].get() or "Shanmukh"

    def interviewer_gender(self) -> str:
        return "female" if self.interviewer_name() == "Yashna" else "male"

    def is_accessible_mode(self) -> bool:
        return self.profile_vars["interview_mode"].get() == "accessible"

    def choose_resume(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose candidate resume",
            filetypes=[("Resume files", "*.pdf *.docx"), ("PDF files", "*.pdf"), ("Word documents", "*.docx")],
        )
        if not path:
            return
        self.profile_vars["resume_path"].set(path)
        self.resume_status.configure(text="Parsing resume securely. Please wait...")
        self.resume_progress.start(12)
        threading.Thread(target=self._parse_resume_worker, args=(path,), daemon=True).start()

    def _parse_resume_worker(self, path: str) -> None:
        try:
            resume = parse_resume(path)
            self.after(0, lambda: self._finish_resume_parse(resume, None))
        except Exception as exc:
            self.after(0, lambda exc=exc: self._finish_resume_parse(None, exc))

    def _finish_resume_parse(self, resume: ResumeInsight | None, error: Exception | None) -> None:
        self.resume_progress.stop()
        if error or resume is None:
            self.profile_vars["resume_path"].set("")
            self.resume_status.configure(text="Resume parsing failed. Please upload a readable PDF or DOCX.")
            messagebox.showerror(APP_TITLE, f"Unable to parse resume:\n{error}")
            return
        self.resume = resume
        self.agent.set_resume(self.resume)
        self.resume_status.configure(text="Resume uploaded and parsed successfully. Details are hidden from the candidate.")

    def run_device_check(self) -> None:
        self.device_status = self.media.check_devices()
        self.camera_status.configure(text=self.device_status.camera_message, foreground=SUCCESS if self.device_status.camera_available else DANGER)
        self.microphone_status.configure(text=self.device_status.microphone_message, foreground=SUCCESS if self.device_status.microphone_available else DANGER)
        self.audio_test_status.configure(text="Run audio test before starting", foreground="#607086")
        if self.device_status.camera_available and self.media.start_camera():
            self.camera_running = True
            self._refresh_camera_preview()
        else:
            self.camera_label.configure(text="Camera preview unavailable. Check Windows camera permissions.", image="")

    def test_microphone(self) -> None:
        self.audio_test_status.configure(text="Listening. Please speak a short sentence...", foreground=ACCENT)
        self.update_idletasks()
        ok, result = self.media.listen_once(timeout=12, phrase_time_limit=12)
        if ok:
            self.audio_test_status.configure(text=f"Audio captured: {result[:70]}", foreground=SUCCESS)
        else:
            self.audio_test_status.configure(text=f"Audio test failed: {result[:80]}", foreground=DANGER)

    def begin_interview(self) -> None:
        if not self._can_enter_live():
            return
        self.agent = TechnicalInterviewAgent()
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.integrity_monitor = IntegrityMonitor()
        if self.feature_vars["recording_package"].get():
            self.session_dir = self.recorder.start_session(self.profile_vars["name"].get(), self.profile_vars["email"].get())
            self.recorder.start_video(620, 348)
            self.video_recording_started = True
        self.agent.set_interviewer(self.interviewer_name())
        self.agent.set_resume(self.resume)
        self.report = None
        self.interviewer_title.configure(text=f"{self.interviewer_name()} - AI HR Interviewer")
        self.agent_panel.configure(text=f"{self.interviewer_name()} - AI HR Interviewer")
        self._load_avatar()
        self._apply_interview_mode()
        self.current_question, self.current_focus = self.agent.next_question(self._profile())
        self._set_question(self.current_question)
        self._set_transcript("")
        self.answer_box.delete("1.0", "end")
        self._update_progress()
        self.show_screen("live")
        self.camera_running = True
        self._refresh_camera_preview()
        if self.is_accessible_mode():
            self.voice_status.configure(text="Voice status: ready. Click Start Reading when the candidate is ready.")
        else:
            self.voice_status.configure(text=f"Voice status: {self.interviewer_name()} is starting the interview.")
            self.start_reading()

    def submit_answer(self) -> None:
        answer = self.answer_box.get("1.0", "end").strip()
        if not answer:
            messagebox.showwarning(APP_TITLE, "Please capture or type the candidate response.")
            return
        self.agent.record_answer(self.current_question, answer, self.current_focus)
        self._append_transcript(self.current_question, answer)
        self.answer_box.delete("1.0", "end")
        if self.agent.should_finish(max(10, int(self.profile_vars["max_questions"].get()))):
            self.finish_interview()
            return
        self.current_question, self.current_focus = self.agent.next_question(self._profile())
        self._set_question(self.current_question)
        self._update_progress()
        if self.is_accessible_mode():
            self.voice_status.configure(text="Voice status: ready. Click Start Reading for the next question.")
        else:
            self.start_reading()

    def _apply_interview_mode(self) -> None:
        if self.is_accessible_mode():
            self.assist_controls.pack(side="left")
        else:
            self.assist_controls.pack_forget()

    def finish_interview(self) -> None:
        self.media.stop_speaking()
        video_path = self.recorder.finalize_video() if self.video_recording_started else ""
        self.report = self.agent.build_report(self._profile(), self.resume)
        if self.feature_vars["confidence_analysis"].get():
            confidence = self.confidence_analyzer.summary()
            self.report.confidence_summary = confidence
            if isinstance(confidence.get("confidence_score"), int):
                self.report.confidence_score = int(confidence["confidence_score"])
                competency_average = round(sum(item.score for item in self.report.competencies) / max(len(self.report.competencies), 1))
                self.report.overall_score = round((competency_average * 0.55) + (self.report.technical_depth_score * 0.3) + (self.report.confidence_score * 0.15))
                self.report.recommendation = self._recommendation_for_score(self.report.overall_score)
        if self.feature_vars["integrity_monitoring"].get():
            self.report.integrity_summary = self.integrity_monitor.summary()
        if self.feature_vars["recording_package"].get():
            refs = self.recorder.references()
            if video_path:
                refs["video_file"] = video_path
            if self.session_dir:
                refs["final_report_pdf"] = str(Path(self.session_dir) / "final_report.pdf")
            self.report.recording_references = refs
            self.recorder.save_json("integrity_report.json", self.report.integrity_summary)
            self.recorder.save_json("confidence_report.json", self.report.confidence_summary)
            integrity_lines = [f"{key}: {value}" for key, value in self.report.integrity_summary.items() if key != "events"]
            integrity_lines.extend(self.report.integrity_summary.get("events", []) if isinstance(self.report.integrity_summary.get("events"), list) else [])
            self.recorder.save_simple_pdf("integrity_report.pdf", "Interview Integrity Report", integrity_lines)
        self.report_text = render_report(self.report)
        if self.feature_vars["recording_package"].get() and self.session_dir:
            try:
                export_enterprise_pdf(self.report, self.report.recording_references.get("final_report_pdf", ""))
            except Exception:
                pass
        save_session(self.report)
        self.completion_label.configure(text=f"Interview Complete: {self.report.recommendation}")
        self.completion_summary.configure(
            text=f"Overall Score: {self.report.overall_score}/100 | Technical Depth: {self.report.technical_depth_score}/100 | Confidence: {self.report.confidence_score}/100"
        )
        self.refresh_dashboard()
        self.show_screen("complete")

    def _recommendation_for_score(self, score: int) -> str:
        if score >= 80:
            return "Strong Hire"
        if score >= 68:
            return "Hire"
        if score >= 55:
            return "Hold / Needs Human Review"
        return "No Hire"

    def download_interview_package(self) -> None:
        if not self.report:
            messagebox.showinfo(APP_TITLE, "Complete an interview before creating an interview package.")
            return
        package = self.recorder.create_package()
        if not package:
            messagebox.showwarning(APP_TITLE, "No recording package is available for this interview.")
            return
        messagebox.showinfo(APP_TITLE, f"Interview package created:\n{package}")

    def start_reading(self, prefix: str = "") -> None:
        if not self.current_question:
            return
        self.voice_status.configure(text=f"Voice status: {self.interviewer_name()} is reading.")
        if not self.media.speak(prefix + self.current_question, int(self.profile_vars["voice_rate"].get()), self.interviewer_gender()):
            messagebox.showinfo(APP_TITLE, "Text-to-speech is not available on this system.")
            self.voice_status.configure(text="Voice status: text-to-speech unavailable")
        else:
            self.after(900, self._poll_speaking_status)

    def stop_reading(self) -> None:
        self.media.stop_speaking()
        self.voice_status.configure(text="Voice status: reading stopped")

    def _poll_speaking_status(self) -> None:
        if self.media.is_speaking():
            self.after(700, self._poll_speaking_status)
        else:
            self.voice_status.configure(text="Voice status: ready")

    def start_voice_recording(self) -> None:
        if not self.feature_vars["voice_interview"].get():
            messagebox.showinfo(APP_TITLE, "Voice interview module is disabled in Settings.")
            return
        if self.recording:
            return
        if not self.media.start_audio_recording():
            self.voice_status.configure(text="Voice status: microphone recording could not start.")
            messagebox.showwarning(APP_TITLE, "Unable to start microphone recording. Check microphone permissions.")
            return
        self.recording = True
        self.record_button.configure(state="disabled", text="Recording...")
        self.stop_record_button.configure(state="normal")
        self.voice_status.configure(text="Voice status: recording. Click Stop Recording when finished.")

    def stop_voice_recording(self) -> None:
        if not self.recording:
            return
        self.stop_record_button.configure(state="disabled")
        self.voice_status.configure(text="Voice status: processing audio transcript...")
        threading.Thread(target=self._stop_recording_worker, daemon=True).start()

    def _stop_recording_worker(self) -> None:
        ok, transcript, wav_bytes = self.media.stop_audio_recording()
        self.after(0, lambda: self._finish_voice_capture(ok, transcript, wav_bytes))

    def _finish_voice_capture(self, ok: bool, transcript: str, wav_bytes: bytes) -> None:
        self.recording = False
        self.record_button.configure(state="normal", text="Start Recording")
        self.stop_record_button.configure(state="disabled")
        if wav_bytes and self.feature_vars["recording_package"].get():
            question_index = len(self.agent.turns) + 1
            self.recorder.save_audio(question_index, wav_bytes)
        if ok:
            self.answer_box.delete("1.0", "end")
            self.answer_box.insert("1.0", transcript)
            self.voice_status.configure(text="Voice status: transcript captured. Click Submit Answer to continue.")
        else:
            self.voice_status.configure(text=f"Voice status: {transcript}")

    def refresh_dashboard(self) -> None:
        if not self.report:
            return
        self.report_text = render_report(self.report)
        self.report_view.delete("1.0", "end")
        self.report_view.insert("1.0", self.report_text)
        self._draw_bar_chart()
        self._draw_radar_chart()

    def save_pdf_report(self) -> None:
        if not self.report:
            messagebox.showinfo(APP_TITLE, "Complete an interview before exporting a PDF report.")
            return
        default_name = f"{self.profile_vars['name'].get().strip() or 'candidate'}_enterprise_interview_report.pdf"
        path = filedialog.asksaveasfilename(title="Save enterprise PDF report", defaultextension=".pdf", initialfile=default_name, filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            output = export_enterprise_pdf(self.report, path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        messagebox.showinfo(APP_TITLE, f"PDF report saved:\n{output}")

    def email_report(self) -> None:
        if not self.report:
            messagebox.showinfo(APP_TITLE, "Complete an interview before emailing a report.")
            return
        try:
            settings = self._email_settings()
        except ValueError as exc:
            messagebox.showwarning(APP_TITLE, str(exc))
            self.show_screen("settings")
            return
        try:
            pdf_path = Path(tempfile.gettempdir()) / f"{self.report.profile.name or 'candidate'}_hr_interview_report.pdf"
            export_enterprise_pdf(self.report, str(pdf_path))
            send_report_email(
                settings,
                f"Technical Interview Report - {self.report.profile.name or 'Candidate'}",
                self.report_text or render_report(self.report),
                str(pdf_path),
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Unable to send email:\n{exc}")
            return
        messagebox.showinfo(APP_TITLE, f"Enhanced visual report emailed to {settings.hr_email}.")

    def _can_enter_live(self) -> bool:
        if not self.profile_vars["resume_path"].get().strip() or not self.resume.raw_text:
            messagebox.showwarning(APP_TITLE, "Resume upload is mandatory before starting the interview.")
            self.show_screen("resume")
            return False
        if not self.device_status:
            messagebox.showwarning(APP_TITLE, "Run camera and microphone checks before starting the interview.")
            self.show_screen("prep")
            return False
        if not self.device_status.camera_available:
            messagebox.showwarning(APP_TITLE, "Camera access is required. Enable Windows camera permission and try again.")
            self.show_screen("prep")
            return False
        if not self.device_status.microphone_available:
            messagebox.showwarning(APP_TITLE, "Microphone access is required. Enable Windows microphone permission and try again.")
            self.show_screen("prep")
            return False
        return True

    def _profile(self) -> CandidateProfile:
        return CandidateProfile(
            name=self.profile_vars["name"].get().strip(),
            email=self.profile_vars["email"].get().strip(),
            role=self.profile_vars["role"].get().strip(),
            experience_years=self.profile_vars["experience_years"].get().strip(),
            hr_email=self.profile_vars["hr_email"].get().strip(),
            resume_path=self.profile_vars["resume_path"].get().strip(),
        )

    def _email_settings(self) -> EmailSettings:
        hr_email = self.profile_vars["hr_email"].get().strip()
        sender = self.email_vars["sender_email"].get().strip()
        password = self.email_vars["sender_password"].get()
        host = self.email_vars["smtp_host"].get().strip()
        if not all([hr_email, sender, password, host]):
            raise ValueError("Please complete HR email, SMTP host, sender email, and SMTP password.")
        if "@" in host:
            raise ValueError("SMTP Host should be a mail server, not an email address. For Gmail, use smtp.gmail.com.")
        return EmailSettings(host, int(self.email_vars["smtp_port"].get()), sender, password, hr_email, bool(self.email_vars["use_tls"].get()))

    def save_config(self) -> None:
        host = self.email_vars["smtp_host"].get().strip()
        if "@" in host:
            messagebox.showwarning(APP_TITLE, "SMTP Host should be a mail server, not an email address. For Gmail, use smtp.gmail.com.")
            return
        data = {
            "email": {key: var.get() for key, var in self.email_vars.items()},
            "profile": {"hr_email": self.profile_vars["hr_email"].get()},
            "features": {key: var.get() for key, var in self.feature_vars.items()},
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo(APP_TITLE, "Settings saved.")

    def _load_config(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for key, value in data.get("email", {}).items():
            if key in self.email_vars:
                self.email_vars[key].set(value)
        for key, value in data.get("features", {}).items():
            if key in self.feature_vars:
                self.feature_vars[key].set(value)
        self._repair_common_email_setting_mistakes()
        hr_email = data.get("profile", {}).get("hr_email")
        if hr_email:
            self.profile_vars["hr_email"].set(hr_email)

    def _repair_common_email_setting_mistakes(self) -> None:
        host = self.email_vars["smtp_host"].get().strip()
        if "@" not in host:
            return
        if not self.email_vars["sender_email"].get().strip():
            self.email_vars["sender_email"].set(host)
        domain = host.split("@", 1)[-1].lower()
        self.email_vars["smtp_host"].set("smtp.gmail.com" if domain == "gmail.com" else "")
        self.email_vars["smtp_port"].set(587)
        self.email_vars["use_tls"].set(True)

    def _set_question(self, text: str) -> None:
        self.question_box.configure(state="normal")
        self.question_box.delete("1.0", "end")
        self.question_box.insert("1.0", text)
        self.question_box.configure(state="disabled")

    def _set_transcript(self, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.insert("1.0", text)
        self.transcript.configure(state="disabled")

    def _append_transcript(self, question: str, answer: str) -> None:
        self.transcript.configure(state="normal")
        index = len(self.agent.turns)
        self.transcript.insert("end", f"{index}. Q: {question}\nA: {answer}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")
        if self.feature_vars["recording_package"].get():
            self.recorder.append_transcript(index, question, answer)

    def _update_progress(self) -> None:
        total = max(10, int(self.profile_vars["max_questions"].get()))
        done = len(self.agent.turns)
        self.progress.configure(value=(done / total) * 100)
        self.progress_label.configure(text=f"Question {done + 1} / {total}")

    def _refresh_camera_preview(self) -> None:
        if not self.camera_running:
            return
        prep_visible = self.screen.get() == "prep"
        live_visible = self.screen.get() == "live"
        if not prep_visible and not live_visible:
            self.after(300, self._refresh_camera_preview)
            return
        width, height = (1280, 720) if prep_visible else (620, 348)
        frame = self.media.read_camera_frame(width, height)
        if frame:
            self.camera_image = frame
            raw_frame = self.media.last_frame_bgr()
            if prep_visible:
                self.camera_label.configure(image=self.camera_image, text="")
            if live_visible:
                self.user_panel.configure(image=self.camera_image, text="")
                self._observe_live_frame(raw_frame)
        else:
            if prep_visible:
                self.camera_label.configure(text="Reconnecting camera...", image="")
            if live_visible:
                self.user_panel.configure(text="Reconnecting camera...", image="")
                if self.feature_vars["integrity_monitoring"].get() and time.time() - self.last_webcam_issue > 10:
                    self.integrity_monitor.webcam_unavailable()
                    self.last_webcam_issue = time.time()
        self.after(80, self._refresh_camera_preview)

    def _observe_live_frame(self, raw_frame) -> None:
        if raw_frame is None:
            return
        if self.feature_vars["recording_package"].get():
            self.recorder.write_video_frame(raw_frame)
        if self.feature_vars["confidence_analysis"].get() and time.time() - self.last_confidence_sample > 1.0:
            metric = self.confidence_analyzer.analyze_frame(raw_frame)
            self.last_confidence_sample = time.time()
            if self.feature_vars["integrity_monitoring"].get():
                self.integrity_monitor.observe_faces(metric.face_count)

    def _on_focus_lost(self, _event) -> None:
        if self.screen.get() != "live" or not self.feature_vars["integrity_monitoring"].get():
            return
        now = time.time()
        if now - self.last_focus_loss > 3:
            self.integrity_monitor.focus_lost()
            self.last_focus_loss = now

    def _on_focus_in(self, _event) -> None:
        pass

    def _close_app(self) -> None:
        self.camera_running = False
        self.media.stop_speaking()
        self.media.stop_camera()
        self.destroy()

    def _draw_bar_chart(self) -> None:
        canvas = self.score_canvas
        canvas.delete("all")
        canvas.create_text(24, 22, text="Competency Performance", anchor="w", fill=BRAND, font=("Segoe UI", 14, "bold"))
        if not self.report:
            return
        y = 58
        for item in self.report.competencies:
            canvas.create_text(24, y, text=item.name, anchor="w", fill="#172033", font=("Segoe UI", 9))
            canvas.create_rectangle(230, y - 9, 610, y + 8, fill="#d7e2ef", outline="")
            canvas.create_rectangle(230, y - 9, 230 + int(3.8 * item.score), y + 8, fill=ACCENT, outline="")
            canvas.create_text(626, y, text=f"{item.score}", anchor="w", fill=BRAND, font=("Segoe UI", 9, "bold"))
            y += 31

    def _draw_radar_chart(self) -> None:
        canvas = self.radar_canvas
        canvas.delete("all")
        canvas.create_text(24, 22, text="Score Distribution", anchor="w", fill=BRAND, font=("Segoe UI", 14, "bold"))
        if not self.report:
            return
        scores = [
            ("Overall", self.report.overall_score),
            ("Depth", self.report.technical_depth_score),
            ("Confidence", self.report.confidence_score),
            ("Comms", next((c.score for c in self.report.competencies if c.name == "Communication Skills"), 0)),
        ]
        x, y = 56, 72
        for label, score in scores:
            color = SUCCESS if score >= 75 else ACCENT if score >= 60 else DANGER
            canvas.create_oval(x, y, x + 52, y + 52, fill=color, outline="")
            canvas.create_text(x + 26, y + 26, text=str(score), fill="#ffffff", font=("Segoe UI", 11, "bold"))
            canvas.create_text(x + 72, y + 26, text=label, anchor="w", fill="#172033", font=("Segoe UI", 10))
            y += 45


if __name__ == "__main__":
    app = EnterpriseHRApp()
    app.mainloop()
