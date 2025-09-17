# Use official Playwright image (already has browsers installed)
FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Start your Flask app with Gunicorn
CMD ["gunicorn", "main_api:app", "--timeout", "120", "--workers", "1", "--threads", "2", "--bind", "0.0.0.0:8080"]
