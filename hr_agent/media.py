import threading
import time
import wave
from io import BytesIO
from dataclasses import dataclass


@dataclass
class DeviceStatus:
    camera_available: bool
    microphone_available: bool
    camera_message: str
    microphone_message: str


class MediaManager:
    def __init__(self) -> None:
        self._tts_lock = threading.Lock()
        self._tts_engine = None
        self._tts_stop_requested = False
        self._speaking = False
        self._camera = None
        self._camera_index = 0
        self._camera_backend = None
        self._last_camera_error = ""
        self._last_frame_bgr = None
        self._audio_thread = None
        self._audio_stop_requested = False
        self._audio_chunks: list[bytes] = []
        self._audio_rate = 16000
        self._audio_sample_width = 2
        self._audio_recording = False

    def check_devices(self) -> DeviceStatus:
        camera_available = self._check_camera()
        microphone_available = self._check_microphone()
        return DeviceStatus(
            camera_available=camera_available,
            microphone_available=microphone_available,
            camera_message="Camera ready" if camera_available else self._last_camera_error or "Camera unavailable or permission denied",
            microphone_message="Microphone ready" if microphone_available else "Microphone unavailable or permission denied",
        )

    def speak(self, text: str, rate: int = 155, gender: str = "male") -> bool:
        if not text.strip():
            return False
        self.stop_speaking()
        thread = threading.Thread(target=self._speak_worker, args=(self._speech_text(text), rate, gender), daemon=True)
        thread.start()
        return True

    def stop_speaking(self) -> None:
        self._tts_stop_requested = True
        try:
            if self._tts_engine:
                self._tts_engine.stop()
        except Exception:
            pass

    def is_speaking(self) -> bool:
        return self._speaking

    def _speak_worker(self, text: str, rate: int, gender: str) -> None:
        with self._tts_lock:
            try:
                self._tts_stop_requested = False
                self._speaking = True
                import pyttsx3
                engine = pyttsx3.init("sapi5")
                self._tts_engine = engine
                engine.setProperty("rate", rate)
                engine.setProperty("volume", 1.0)
                voice_id = self._voice_for_gender(engine, gender)
                if voice_id:
                    engine.setProperty("voice", voice_id)
                engine.say(text)
                if not self._tts_stop_requested:
                    engine.runAndWait()
                engine.stop()
            except Exception:
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            finally:
                self._speaking = False
                self._tts_engine = None

    def _speech_text(self, text: str) -> str:
        replacements = {
            "CI/CD": "C I C D",
            "CI / CD": "C I C D",
            "API": "A P I",
            "APIs": "A P I's",
            "SQL": "S Q L",
            "NoSQL": "No S Q L",
            "REST": "rest",
            "JSON": "J son",
            "JWT": "J W T",
            "OAuth": "O auth",
            "UI": "U I",
            "UX": "U X",
            "OOP": "O O P",
        }
        spoken = text
        for source, target in replacements.items():
            spoken = spoken.replace(source, target)
        return spoken.replace("/", " ")

    def _voice_for_gender(self, engine, gender: str) -> str | None:
        try:
            voices = engine.getProperty("voices")
        except Exception:
            return None
        wanted = "female" if gender == "female" else "male"
        fallback = voices[0].id if voices else None
        for voice in voices:
            text = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
            if wanted == "female" and any(name in text for name in ["zira", "female", "hazel", "susan"]):
                return voice.id
            if wanted == "male" and any(name in text for name in ["david", "male", "mark", "ravi"]):
                return voice.id
        return fallback

    def listen_once(self, timeout: int = 15, phrase_time_limit: int = 50) -> tuple[bool, str]:
        try:
            import speech_recognition as sr
        except Exception:
            return False, "Speech recognition package is not installed."
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.25
        recognizer.non_speaking_duration = 0.6
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.2)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            return True, recognizer.recognize_google(audio)
        except sr.WaitTimeoutError:
            return False, "No speech was detected. Click Record, wait for the status to say Listening, then speak clearly near the microphone."
        except sr.UnknownValueError:
            return False, "Audio was captured, but speech could not be understood. Try again closer to the microphone."
        except sr.RequestError as exc:
            return False, f"Speech recognition service is unavailable: {exc}"
        except Exception as exc:
            return False, str(exc)

    def start_audio_recording(self) -> bool:
        if self._audio_recording:
            return True
        try:
            import pyaudio
        except Exception:
            return False
        self._audio_chunks = []
        self._audio_stop_requested = False
        self._audio_recording = True
        self._audio_thread = threading.Thread(target=self._record_audio_worker, args=(pyaudio,), daemon=True)
        self._audio_thread.start()
        return True

    def stop_audio_recording(self) -> tuple[bool, str, bytes]:
        if not self._audio_recording:
            return False, "Recording was not active.", b""
        self._audio_stop_requested = True
        if self._audio_thread:
            self._audio_thread.join(timeout=4)
        self._audio_recording = False
        wav_bytes = self._wav_bytes()
        if not wav_bytes:
            return False, "No audio was captured.", b""
        transcript = self._transcribe_wav(wav_bytes)
        if not transcript:
            return False, "Audio was recorded, but speech could not be converted to text.", wav_bytes
        return True, transcript, wav_bytes

    def is_audio_recording(self) -> bool:
        return self._audio_recording

    def _record_audio_worker(self, pyaudio_module) -> None:
        audio = pyaudio_module.PyAudio()
        stream = None
        try:
            fmt = pyaudio_module.paInt16
            self._audio_sample_width = audio.get_sample_size(fmt)
            stream = audio.open(format=fmt, channels=1, rate=self._audio_rate, input=True, frames_per_buffer=1024)
            while not self._audio_stop_requested:
                self._audio_chunks.append(stream.read(1024, exception_on_overflow=False))
        except Exception:
            pass
        finally:
            try:
                if stream:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            audio.terminate()
            self._audio_recording = False

    def _wav_bytes(self) -> bytes:
        if not self._audio_chunks:
            return b""
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(self._audio_sample_width)
            wav.setframerate(self._audio_rate)
            wav.writeframes(b"".join(self._audio_chunks))
        return buffer.getvalue()

    def _transcribe_wav(self, wav_bytes: bytes) -> str:
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(BytesIO(wav_bytes)) as source:
                audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
        except Exception:
            return ""

    def start_camera(self) -> bool:
        try:
            import cv2
        except Exception:
            self._last_camera_error = "OpenCV is unavailable, so camera preview cannot start."
            return False
        self.stop_camera()
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]
        for backend in backends:
            camera = cv2.VideoCapture(self._camera_index, backend)
            if not camera.isOpened():
                camera.release()
                continue
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            camera.set(cv2.CAP_PROP_FPS, 30)
            ok = False
            for _ in range(5):
                ok, _frame = camera.read()
                if ok:
                    break
                time.sleep(0.05)
            if ok:
                self._camera = camera
                self._camera_backend = backend
                self._last_camera_error = ""
                return True
            camera.release()
        self._last_camera_error = "Camera could not be opened. Close other apps using the camera and check Windows privacy permissions."
        return False

    def read_camera_frame(self, width: int = 640, height: int = 360):
        if self._camera is None and not self.start_camera():
            return None
        try:
            import cv2
            from PIL import Image, ImageTk
            ok, frame = self._camera.read()
        except Exception:
            self._last_camera_error = "Camera read failed."
            return None
        if not ok:
            self.stop_camera()
            self._last_camera_error = "Camera stream dropped. Attempting to reconnect."
            return None
        self._last_frame_bgr = frame.copy()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 1)
        image = Image.fromarray(frame).resize((width, height))
        return ImageTk.PhotoImage(image)

    def last_frame_bgr(self):
        return self._last_frame_bgr

    def capture_camera_frame(self):
        return self.read_camera_frame(640, 360)

    def stop_camera(self) -> None:
        if self._camera is not None:
            try:
                self._camera.release()
            except Exception:
                pass
            self._camera = None

    def _check_camera(self) -> bool:
        try:
            import cv2
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]:
                camera = cv2.VideoCapture(self._camera_index, backend)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                ok = camera.isOpened()
                if ok:
                    for _ in range(3):
                        ok, _ = camera.read()
                        if ok:
                            break
                camera.release()
                if ok:
                    self._last_camera_error = ""
                    return True
            self._last_camera_error = "Camera unavailable, busy in another app, or blocked by Windows privacy permissions."
            return False
        except Exception:
            self._last_camera_error = "Camera check failed."
            return False

    def _check_microphone(self) -> bool:
        try:
            import speech_recognition as sr
            names = sr.Microphone.list_microphone_names()
            return bool(names)
        except Exception:
            return False
