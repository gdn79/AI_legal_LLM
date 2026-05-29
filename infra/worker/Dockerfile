FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD python -c "import os; from redis import Redis; Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0')).ping()"

CMD ["python", "worker.py"]
