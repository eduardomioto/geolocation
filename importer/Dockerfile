FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    osmium-tool \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY importer.py ./

ENTRYPOINT ["python3", "/app/importer.py"]
