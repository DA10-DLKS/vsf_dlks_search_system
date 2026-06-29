FROM python:3.11-slim

WORKDIR /app

# System deps for lxml / scrapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && sed -i '/^torch/d' requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
