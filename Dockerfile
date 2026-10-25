FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home app
COPY server.py welcome.html index.html app.js i18n.js ./
COPY loanmirror ./loanmirror
COPY samples ./samples
USER app
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --limit-concurrency 20"]
