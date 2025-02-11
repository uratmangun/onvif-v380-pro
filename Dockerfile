FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libx264-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for HLS segments and set permissions
RUN mkdir -p /app/static/hls && \
    chown -R www-data:www-data /app/static && \
    chmod -R 755 /app/static

# Copy application code and env file
COPY app.py .
COPY .env .

# Expose the application ports
EXPOSE 8083

# Run the application
CMD ["python", "app.py"]
