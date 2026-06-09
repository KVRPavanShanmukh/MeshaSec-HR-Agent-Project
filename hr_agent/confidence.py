from dataclasses import dataclass
from statistics import mean


@dataclass
class FrameConfidence:
    face_count: int = 0
    eye_contact: bool = False
    centered: bool = False
    expression_signal: str = "Unknown"
    head_offset: float = 0.0


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
            self._face_cascade = None
            self._eye_cascade = None

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
                center_x = x + w / 2
                frame_center = frame_bgr.shape[1] / 2
                metric.head_offset = abs(center_x - frame_center) / max(frame_bgr.shape[1], 1)
                metric.centered = metric.head_offset < 0.18
                roi = gray[y:y + h, x:x + w]
                eyes = self._eye_cascade.detectMultiScale(roi, 1.1, 5, minSize=(18, 18)) if self._eye_cascade is not None else []
                metric.eye_contact = len(eyes) >= 1 and metric.centered
                metric.expression_signal = "Engaged" if metric.eye_contact else "Low visibility"
        except Exception:
            pass
        self.samples.append(metric)
        return metric

    def summary(self) -> dict[str, str | int | float]:
        if not self.samples:
            return {
                "confidence_score": 0,
                "eye_contact": "Insufficient data",
                "engagement": "Insufficient data",
                "nervousness_indicators": "Insufficient data",
                "disclaimer": self.disclaimer(),
            }
        visible = [sample for sample in self.samples if sample.face_count > 0]
        if not visible:
            return {
                "confidence_score": 20,
                "eye_contact": "Poor",
                "engagement": "Low",
                "nervousness_indicators": "High: face not consistently visible",
                "disclaimer": self.disclaimer(),
            }
        eye_ratio = sum(sample.eye_contact for sample in visible) / len(visible)
        centered_ratio = sum(sample.centered for sample in visible) / len(visible)
        offsets = [sample.head_offset for sample in visible]
        stability = max(0, 1 - (mean(offsets) * 3))
        score = round((eye_ratio * 42) + (centered_ratio * 32) + (stability * 26))
        return {
            "confidence_score": max(0, min(score, 100)),
            "eye_contact": self._rating(eye_ratio),
            "engagement": "High" if score >= 75 else "Moderate" if score >= 50 else "Low",
            "nervousness_indicators": "Low" if stability >= 0.72 else "Moderate" if stability >= 0.45 else "High",
            "samples": len(self.samples),
            "disclaimer": self.disclaimer(),
        }

    def disclaimer(self) -> str:
        return "Confidence and emotion metrics are supportive indicators only and are not final hiring criteria."

    def _rating(self, ratio: float) -> str:
        if ratio >= 0.75:
            return "Good"
        if ratio >= 0.45:
            return "Moderate"
        return "Poor"

