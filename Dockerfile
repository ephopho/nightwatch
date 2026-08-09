# Nightwatch — Cloud Run image.
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; add build-essential only if a wheel needs compiling.
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects $PORT (defaults to 8080). uvicorn must bind 0.0.0.0:$PORT.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
