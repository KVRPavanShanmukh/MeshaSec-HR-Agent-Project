from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

size = 256
image = Image.new("RGBA", (size, size), "#16324f")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((18, 18, 238, 238), radius=42, fill="#16324f", outline="#2f80ed", width=8)
draw.ellipse((162, 34, 220, 92), fill="#2f80ed")
draw.rounded_rectangle((54, 126, 202, 192), radius=20, fill="#ffffff")
draw.rectangle((82, 106, 174, 130), fill="#ffffff")
draw.rectangle((96, 92, 160, 110), fill="#ffffff")
try:
    font = ImageFont.truetype("arialbd.ttf", 50)
except OSError:
    font = ImageFont.load_default()
draw.text((72, 133), "HR", fill="#16324f", font=font)
image.save(ASSETS / "app_icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])

