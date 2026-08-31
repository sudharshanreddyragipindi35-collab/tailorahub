FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python scripts/container_healthcheck.py

CMD ["sh", "-c", "case \"${SERVICE_ROLE:-web}\" in worker) exec python -m app.tasks.worker ;; scheduler) exec python -m app.tasks.scheduler_runner ;; migration) exec alembic upgrade head ;; web) exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} ;; *) echo 'Invalid SERVICE_ROLE' >&2; exit 2 ;; esac"]
