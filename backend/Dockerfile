FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render exposes PORT environment variable
ENV PORT=8000

# Start Uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
