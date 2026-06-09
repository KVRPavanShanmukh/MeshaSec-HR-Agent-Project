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
    multiple_face_count: int = 0
    webcam_issue_count: int = 0

    def log(self, message: str, severity: int = 1) -> None:
        self.events.append(IntegrityEvent(datetime.now().strftime("%I:%M:%S %p"), message, severity))

    def focus_lost(self) -> None:
        self.focus_loss_count += 1
        self.log("Candidate left the interview window.", 2)

    def webcam_unavailable(self) -> None:
        self.webcam_issue_count += 1
        self.log("Webcam unavailable during interview.", 2)

    def observe_faces(self, face_count: int) -> None:
        if face_count > 1:
            self.multiple_face_count += 1
            if self.multiple_face_count % 8 == 1:
                self.log("Multiple faces detected in webcam feed.", 3)

    def summary(self) -> dict[str, str | int | list[str]]:
        penalty = self.focus_loss_count * 8 + self.multiple_face_count * 3 + self.webcam_issue_count * 10
        score = max(0, 100 - penalty)
        if score >= 85:
            risk = "Low Risk"
        elif score >= 60:
            risk = "Medium Risk"
        else:
            risk = "High Risk"
        return {
            "integrity_score": score,
            "risk": risk,
            "focus_loss_count": self.focus_loss_count,
            "multiple_face_events": self.multiple_face_count,
            "webcam_issue_count": self.webcam_issue_count,
            "events": [f"{event.timestamp} - {event.message}" for event in self.events],
        }
