# Safe Desk dry-run UI. No API keys. No Binance REST.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAFE_DESK_ROOT=/app \
    SAFE_DESK_MODE=dry-run

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY config ./config
COPY prompts ./prompts
COPY logs ./logs

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8080
USER nobody
CMD ["python", "-m", "safe_desk", "serve", "--host", "0.0.0.0", "--port", "8080"]
