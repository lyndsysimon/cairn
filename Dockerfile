FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY alembic.ini .

RUN pip install --no-cache-dir .

CMD ["uvicorn", "cairn.main:app", "--host", "0.0.0.0", "--port", "8000"]
