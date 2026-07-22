# Long-polling Telegram bot - no ports, no web server. Secrets are bind-mounted
# at runtime (public repo: nothing sensitive may ever land in this image).
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY secrets/example_api_config.ini secrets/example_api_config.ini

# ics_files is written at runtime (calendar exports); secrets/ is the bind-mount
# target for api_config.ini + the Firebase service-account JSON.
RUN useradd --create-home appuser \
    && mkdir -p ics_files \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
CMD ["python", "src/main.py"]
