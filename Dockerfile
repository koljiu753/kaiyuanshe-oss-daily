FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs

RUN python -m pip install --no-cache-dir -e .

ENV PORT=8765

EXPOSE 8765

CMD ["python", "-m", "osdaily.cli", "serve", "--host", "0.0.0.0", "--schedule", "--schedule-time", "06:00", "--notify"]
