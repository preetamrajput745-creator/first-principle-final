FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# libpq-dev for psycopg2, curl/unzip for healthchecks
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY . /app

# Set python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "api/main.py"]
