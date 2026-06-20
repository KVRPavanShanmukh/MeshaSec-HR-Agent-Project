"""Provider-neutral avatar animation with a static-image fallback."""


class AvatarAnimator:
    def __init__(self, label, image, image_tk_module) -> None:
        self.label = label
        self._frames = []
        self._index = 0
        self._running = False
        self._after_id = None
        try:
            from PIL import ImageDraw
            base = image.copy()
            speaking = image.copy()
            draw = ImageDraw.Draw(speaking)
            width, height = speaking.size
            mouth_x = width // 2
            mouth_y = int(height * 0.66)
            radius_x = max(5, width // 45)
            radius_y = max(3, height // 70)
            draw.ellipse((mouth_x - radius_x, mouth_y - radius_y, mouth_x + radius_x, mouth_y + radius_y), fill="#3b1f24")
            self._frames = [image_tk_module.PhotoImage(base), image_tk_module.PhotoImage(speaking)]
        except Exception:
            self._frames = [image_tk_module.PhotoImage(image)]
        self.label.configure(image=self._frames[0], text="")

    def start(self) -> None:
        if self._running or len(self._frames) < 2:
            return
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._after_id:
            try:
                self.label.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        if self._frames:
            self.label.configure(image=self._frames[0])

    def _tick(self) -> None:
        if not self._running:
            return
        self._index = (self._index + 1) % len(self._frames)
        self.label.configure(image=self._frames[self._index])
        self._after_id = self.label.after(170, self._tick)
