from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class IntegrityEvent:
    timestamp: str
    message: str
    severity: int = 1


@dataclass
class IntegrityMonitor:
    events: list[IntegrityEvent] = field(default_factory=list)
    focus_loss_count: int = 0
    paste_count: int = 0
    copy_count: int = 0
    multiple_face_count: int = 0
    webcam_issue_count: int = 0

    def log(self, message: str, severity: int = 1) -> None:
        self.events.append(IntegrityEvent(datetime.now().strftime("%I:%M:%S %p"), message, severity))

    def focus_lost(self) -> None:
        self.focus_loss_count += 1
        self.log("Candidate switched away from the interview application.", 2)

    def paste_detected(self) -> None:
        self.paste_count += 1
        self.log("Candidate pasted text into the response field.", 2)

    def webcam_unavailable(self) -> None:
        self.webcam_issue_count += 1
        self.log("Webcam unavailable during interview.", 2)

    def observe_faces(self, face_count: int) -> None:
        if face_count > 1:
            self.multiple_face_count += 1
            if self.multiple_face_count % 8 == 1:
                self.log("Multiple faces detected in webcam feed.", 3)

    def summary(self) -> dict[str, str | int | list[str]]:
        penalty = self.focus_loss_count * 8 + self.paste_count * 6 + self.copy_count * 2 + self.multiple_face_count * 3 + self.webcam_issue_count * 10
        score = max(0, 100 - penalty)
        risk = "Low Risk" if score >= 85 else "Medium Risk" if score >= 60 else "High Risk"
        return {
            "integrity_score": score,
            "risk": risk,
            "tab_or_app_switches": self.focus_loss_count,
            "paste_events": self.paste_count,
            "copy_events": self.copy_count,
            "multiple_face_events": self.multiple_face_count,
            "webcam_issue_count": self.webcam_issue_count,
            "events": [f"{event.timestamp} - {event.message}" for event in self.events],
        }

