# Use official Python slim image
FROM python:3.12-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Create screenshots upload folder
RUN mkdir -p static/screenshots

# Expose port
EXPOSE 8080

# Start the app with Gunicorn
CMD gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
