# Python 3.10 (Stable) Force karenge
FROM python:3.10-slim

# FFmpeg install (Audio deep karne ke liye zaroori)
RUN apt-get update && apt-get install -y ffmpeg git

# Folder setup
WORKDIR /app

# Files copy
COPY . .

# Libraries install
RUN pip install --no-cache-dir -r requirements.txt

# Bot start
CMD ["python", "main.py"]
