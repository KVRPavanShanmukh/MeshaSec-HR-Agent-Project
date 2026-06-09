@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python tools\generate_icon.py
pyinstaller --noconfirm --onefile --windowed --name "AI HR Agent" --icon assets\app_icon.ico --add-data "assets;assets" --hidden-import pyttsx3.drivers.sapi5 --hidden-import speech_recognition --hidden-import pyaudio --hidden-import cv2 --hidden-import PIL.ImageTk main.py
echo.
echo Build complete. Check the dist folder for AI HR Agent.exe
echo To create an installation wizard, install Inno Setup and compile installer\AI_HR_Agent.iss
pause
