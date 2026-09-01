# Dockerfile for SuryaSetu Solar Flare Forecaster Dashboard
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    DATA_DIR=dashboard_data

WORKDIR /app

# Install minimal deploy dependencies
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy dashboard server application and pre-computed verified data
COPY app ./app
COPY dashboard_data ./dashboard_data

# Expose standard port
EXPOSE 8000

# Run uvicorn on all interfaces with dynamic PORT support for cloud platforms
CMD ["sh", "-c", "uvicorn app.dashboard_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
