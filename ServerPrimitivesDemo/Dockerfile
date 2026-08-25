FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/data/institute.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --create-home mcpuser \
    && mkdir -p /app/data \
    && chown -R mcpuser:mcpuser /app

USER mcpuser

EXPOSE 8000

CMD ["python", "main.py"]