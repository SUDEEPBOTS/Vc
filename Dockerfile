# Ham Python 3.10 use kar rahe hain jo sabse stable hai
FROM python:3.10-slim

# System updates aur FFmpeg install karna (Deep Voice ke liye zaroori)
RUN apt-get update && apt-get install -y ffmpeg git

# Working folder set karna
WORKDIR /app

# Saari files copy karna
COPY . .

# Libraries install karna
RUN pip install --no-cache-dir -r requirements.txt

# Bot ko start karna
CMD ["python", "main.py"]
