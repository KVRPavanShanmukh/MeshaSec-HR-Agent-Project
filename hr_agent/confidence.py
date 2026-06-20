from dataclasses import dataclass
from statistics import mean


@dataclass
class FrameConfidence:
    face_count: int = 0
    eye_contact: bool = False
    centered: bool = False
    expression_signal: str = "Unknown"
    head_offset: float = 0.0
    eye_position: float | None = None


class ConfidenceAnalyzer:
    def __init__(self) -> None:
        self.samples: list[FrameConfidence] = []
        self._face_cascade = None
        self._eye_cascade = None
        try:
            import cv2
            self._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            self._eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        except Exception:
            pass

    def analyze_frame(self, frame_bgr) -> FrameConfidence:
        metric = FrameConfidence()
        if frame_bgr is None or self._face_cascade is None:
            self.samples.append(metric)
            return metric
        try:
            import cv2
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
            metric.face_count = len(faces)
            if len(faces):
                x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
                metric.head_offset = abs((x + w / 2) - frame_bgr.shape[1] / 2) / max(frame_bgr.shape[1], 1)
                metric.centered = metric.head_offset < 0.18
                roi = gray[y:y + h, x:x + w]
                eyes = self._eye_cascade.detectMultiScale(roi, 1.1, 5, minSize=(18, 18)) if self._eye_cascade is not None else []
                valid_eyes = sorted(eyes, key=lambda item: item[2] * item[3], reverse=True)[:2]
                if valid_eyes:
                    eye_centers = [ex + ew / 2 for ex, ey, ew, eh in valid_eyes]
                    metric.eye_position = mean(eye_centers) / max(w, 1)
                metric.eye_contact = len(valid_eyes) >= 1 and metric.centered
                metric.expression_signal = "Engaged" if metric.eye_contact else "Low visibility"
        except Exception:
            pass
        self.samples.append(metric)
        return metric

    def summary(self) -> dict[str, str | int | float]:
        if not self.samples:
            return self._insufficient(0)
        visible = [sample for sample in self.samples if sample.face_count > 0]
        if not visible:
            result = self._insufficient(20)
            result.update({"face_visibility": "Poor", "head_stability": "Poor", "eye_movement": "Insufficient data"})
            return result
        eye_ratio = sum(sample.eye_contact for sample in visible) / len(visible)
        centered_ratio = sum(sample.centered for sample in visible) / len(visible)
        stability = max(0, 1 - (mean(sample.head_offset for sample in visible) * 3))
        eye_positions = [sample.eye_position for sample in visible if sample.eye_position is not None]
        eye_changes = [abs(eye_positions[i] - eye_positions[i - 1]) for i in range(1, len(eye_positions))]
        eye_motion = mean(eye_changes) if eye_changes else 0.0
        eye_movement = "Stable" if eye_motion < 0.07 else "Moderate" if eye_motion < 0.16 else "Frequent"
        visibility_ratio = len(visible) / max(len(self.samples), 1)
        score = round((eye_ratio * 38) + (centered_ratio * 28) + (stability * 22) + (visibility_ratio * 12))
        return {
            "confidence_score": max(0, min(score, 100)),
            "face_visibility": self._rating(visibility_ratio),
            "eye_contact": self._rating(eye_ratio),
            "eye_movement": eye_movement,
            "head_stability": self._rating(stability),
            "engagement": "High" if score >= 75 else "Moderate" if score >= 50 else "Low",
            "nervousness_indicators": "Low" if stability >= 0.72 and eye_motion < 0.16 else "Moderate" if stability >= 0.45 else "High",
            "samples": len(self.samples),
            "disclaimer": self.disclaimer(),
        }

    def _insufficient(self, score: int) -> dict[str, str | int | float]:
        return {"confidence_score": score, "face_visibility": "Insufficient data", "eye_contact": "Insufficient data", "eye_movement": "Insufficient data", "head_stability": "Insufficient data", "engagement": "Insufficient data", "nervousness_indicators": "Insufficient data", "disclaimer": self.disclaimer()}

    def disclaimer(self) -> str:
        return "Face, eye, confidence, and emotion metrics are supportive indicators only and are not final hiring criteria."

    def _rating(self, ratio: float) -> str:
        return "Good" if ratio >= 0.75 else "Moderate" if ratio >= 0.45 else "Poor"
