FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

COPY main.py ./
COPY src/ ./src/
COPY prompts/ ./prompts/

RUN mkdir -p /app/datos /app/logs && useradd -m botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "main.py"]