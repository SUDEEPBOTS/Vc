# Python 3.10 Use karenge (Stable)
FROM python:3.10-slim

# FFmpeg install karna zaroori hai
RUN apt-get update && apt-get install -y ffmpeg git

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
