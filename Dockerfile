FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY config ./config
COPY prompts ./prompts
COPY demo ./demo
COPY docs ./docs
RUN pip install --no-cache-dir -e ".[web]" || pip install --no-cache-dir -e .
EXPOSE 8765
CMD ["python", "-m", "safe_desk.web", "--host", "0.0.0.0", "--port", "8765"]
