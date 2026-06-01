FROM python:3.11

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-worker.txt .

RUN pip install --no-cache-dir -r requirements-worker.txt

COPY . .

CMD ["celery", "-A", "test_project", "worker", "--loglevel=info", "--concurrency=1"]
