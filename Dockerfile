# Base Python image
FROM python:3.11-slim

# Avoid stdout buffering
ENV PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app

# Install system dependencies required for OCR + OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies with extended timeout + retries
RUN pip install --upgrade pip \
    && pip install --default-timeout=200 --retries=10 --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Expose FastAPI port
EXPOSE 8080

# Start FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
