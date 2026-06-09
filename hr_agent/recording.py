import json
import re
import wave
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any


class InterviewRecorder:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.home() / "Documents" / "MESHASEC AI HR Interviews"
        self.session_dir: Path | None = None
        self.audio_dir: Path | None = None
        self.video_dir: Path | None = None
        self._video_writer = None
        self._video_path: Path | None = None
        self._video_size = (640, 360)

    def start_session(self, candidate_name: str, candidate_email: str = "") -> Path:
        candidate_id = self._candidate_id(candidate_name, candidate_email)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_dir = self.base_dir / candidate_id / timestamp
        self.audio_dir = self.session_dir / "audio"
        self.video_dir = self.session_dir / "video"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        return self.session_dir

    def save_audio(self, question_index: int, wav_bytes: bytes) -> str:
        if not self.audio_dir:
            return ""
        path = self.audio_dir / f"question_{question_index:02d}.wav"
        path.write_bytes(wav_bytes)
        return str(path)

    def append_transcript(self, question_index: int, question: str, transcript: str) -> str:
        if not self.session_dir:
            return ""
        path = self.session_dir / "transcript.txt"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{question_index}. Q: {question}\n")
            handle.write(f"A: {transcript}\n\n")
        return str(path)

    def start_video(self, width: int = 640, height: int = 360, fps: float = 12.0) -> str:
        if not self.video_dir:
            return ""
        try:
            import cv2
            self._video_size = (width, height)
            self._video_path = self.video_dir / "candidate_camera.avi"
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self._video_writer = cv2.VideoWriter(str(self._video_path), fourcc, fps, self._video_size)
            return str(self._video_path)
        except Exception:
            self._video_writer = None
            return ""

    def write_video_frame(self, frame_bgr) -> None:
        if self._video_writer is None or frame_bgr is None:
            return
        try:
            import cv2
            frame = cv2.resize(frame_bgr, self._video_size)
            self._video_writer.write(frame)
        except Exception:
            pass

    def finalize_video(self) -> str:
        if self._video_writer is not None:
            try:
                self._video_writer.release()
            except Exception:
                pass
            self._video_writer = None
        return str(self._video_path) if self._video_path else ""

    def save_json(self, name: str, data: dict[str, Any]) -> str:
        if not self.session_dir:
            return ""
        path = self.session_dir / name
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(path)

    def save_text(self, name: str, text: str) -> str:
        if not self.session_dir:
            return ""
        path = self.session_dir / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def save_simple_pdf(self, name: str, title: str, lines: list[str]) -> str:
        if not self.session_dir:
            return ""
        path = self.session_dir / name
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            doc = SimpleDocTemplate(str(path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
            for line in lines:
                story.append(Paragraph(line, styles["BodyText"]))
            doc.build(story)
            return str(path)
        except Exception:
            fallback = path.with_suffix(".txt")
            fallback.write_text(title + "\n\n" + "\n".join(lines), encoding="utf-8")
            return str(fallback)

    def save_report_path(self, source_pdf: str, target_name: str = "final_report.pdf") -> str:
        if not self.session_dir or not source_pdf:
            return ""
        source = Path(source_pdf)
        if not source.exists():
            return ""
        target = self.session_dir / target_name
        target.write_bytes(source.read_bytes())
        return str(target)

    def create_package(self) -> str:
        if not self.session_dir:
            return ""
        package = self.session_dir.with_suffix(".zip")
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in self.session_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(self.session_dir))
        return str(package)

    def references(self) -> dict[str, str | list[str]]:
        if not self.session_dir:
            return {}
        return {
            "session_directory": str(self.session_dir),
            "audio_files": [str(path) for path in sorted((self.audio_dir or self.session_dir).glob("*.wav"))],
            "video_file": str(self._video_path) if self._video_path else "",
            "transcript_file": str(self.session_dir / "transcript.txt"),
        }

    def _candidate_id(self, candidate_name: str, candidate_email: str) -> str:
        raw = candidate_name or candidate_email or "Candidate_001"
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
        return safe or "Candidate_001"
