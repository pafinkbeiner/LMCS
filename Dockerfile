FROM python:3.11-bookworm

# Install Chromium and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome binary location for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Default interval (can be overridden with docker run -e INTERVAL=30)
ENV INTERVAL=60

# Run script in loop mode with configurable interval
CMD ["sh", "-c", "python script.py --loop --interval $INTERVAL"]
