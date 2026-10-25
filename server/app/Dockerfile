FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home marketplace
COPY . .
RUN test -f market/migrations/0001_initial.py || (echo "Prepare and commit initial migrations before building the release image." >&2; exit 1)
RUN DEBUG=1 python manage.py collectstatic --noinput && mkdir -p /data/media && chown -R marketplace:marketplace /data /app
USER marketplace
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "90", "--access-logfile", "-"]
