FROM python:3.11-slim

# Install system dependencies for Shapely and GEOS
RUN apt-get update && apt-get install -y \
    build-essential \
    libgeos-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the importer script
COPY importer.py .

# Default command
CMD ["python", "importer.py"]
