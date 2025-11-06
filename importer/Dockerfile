# Use a slim Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    osmium-tool \
    gdal-bin \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create data and temp directories
RUN mkdir -p /data /tmp

# Ensure logs show immediately (no buffering)
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "/app/main.py"]
