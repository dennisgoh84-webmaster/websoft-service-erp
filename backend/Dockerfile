# Backend image -- FastAPI + Alembic, run behind the nginx container (see
# ../frontend/Dockerfile) which serves the frontend and reverse-proxies
# /api/* here, so both sides share one origin and no CORS config is
# needed in production (see DEPLOY.md).
FROM python:3.11-slim

# LibreOffice (Writer specifically, not just -core) is needed for the
# "Email" button's docx -> PDF conversion -- see
# app/services/pdf_convert.py and DEV_SETUP.md's note that -core/-common
# alone is NOT enough.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

# Migrations run as a separate one-shot step (see docker-compose.yml's
# `migrate` service) so a rolling restart of `backend` never re-runs them.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
