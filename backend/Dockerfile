FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt \
    && useradd --uid 10001 --create-home warfront \
    && mkdir /data /backups && chown warfront:warfront /data /backups
COPY app ./app
COPY tools/backup_sqlite.py tools/check_readiness.py ./tools/
USER warfront
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "25"]
