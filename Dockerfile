FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements-prod-lock.txt .
RUN pip install --no-cache-dir -r requirements-prod-lock.txt && useradd --create-home --uid 10001 escuta
COPY escuta ./escuta
COPY voice_customer ./voice_customer
COPY web ./web
COPY scripts ./scripts
USER escuta
EXPOSE 8501
CMD ["python", "-m", "escuta", "serve", "--host", "0.0.0.0"]
