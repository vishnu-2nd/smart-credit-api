FROM python:3.13-slim

# Install system deps
RUN apt-get update && apt-get install -y wget gnupg ca-certificates fonts-liberation libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libgtk-3-0 libnss3 libxshmfence1 xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install --with-deps chromium

COPY . .

CMD gunicorn main_api:app --timeout 120 --workers 1 --threads 2 --bind 0.0.0.0:$PORT
