FROM python:3.12-slim

COPY pyproject.toml /app/
COPY src/ /app/src/

WORKDIR /app

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "pr_review_action.main"]
