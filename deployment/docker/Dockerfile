# Multi-stage Dockerfile for WaveForge Pro

# Stage 1: Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy backend application
COPY backend/app /app/backend/app
COPY backend/__init__.py /app/backend/
COPY backend/pyproject.toml /app/backend/

# Copy frontend
COPY frontend /app/frontend

# Create upload directories
RUN mkdir -p /app/backend/uploaded_data/temp /app/backend/uploaded_data/completed

# Create non-root user
RUN useradd -m -u 1000 waveforge && \
    chown -R waveforge:waveforge /app

USER waveforge

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
WORKDIR /app/backend/app
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
