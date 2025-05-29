# Use official Python 3.11.4 slim image as base
FROM python:3.11.4-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to the container
COPY . .

# Set environment variables (optional, can be overridden with .env or docker-compose)
ENV PYTHONUNBUFFERED=1 \
    ENV=development \
    PORT=3000

# Expose the port your app will run on
EXPOSE 3000

# Command to run the application
CMD ["python", "main.py"]