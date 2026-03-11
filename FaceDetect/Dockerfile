FROM python:3.11-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Railway uses PORT env variable
ENV PORT=5000
EXPOSE $PORT

# Run with gunicorn, use PORT env variable
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 app:app
