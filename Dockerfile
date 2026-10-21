# Long-polling Telegram bot that also serves the calendar feed on port 8080 (aiohttp, in
# the bot process). Internal only: Caddy reaches it over the `web` network, never published.
# Secrets are bind-mounted at runtime (public repo: nothing sensitive may ever land in
# this image).
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
# pip is build-time only. Its vendored libraries (certifi, urllib3, ...) are scanned by
# the deploy's trivy gate like our own pins but are not covered by Dependabot, so a
# vendored CVE would block every deploy until a pip release ships the fix. Removing pip
# keeps the scan on requirements.txt alone.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

COPY src/ src/
COPY scripts/ scripts/
COPY secrets/example_api_config.ini secrets/example_api_config.ini

# ics_files is written at runtime (calendar exports); secrets/ is the bind-mount
# target for api_config.ini.
RUN useradd --create-home appuser \
    && mkdir -p ics_files \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "src/main.py"]
