FROM python:3.11-slim

# Install system dependencies with optimizations
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies with optimizations
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy application code
COPY . .

# Pre-download and cache models for faster startup
RUN python -c "import livekit.plugins.silero as silero; silero.VAD.load()" || true

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Expose port (LiveKit agents typically use port 8080)
EXPOSE 8080

# Optimized health check with faster startup
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=2 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=3)" || exit 1

# Start the agent with optimized settings
CMD ["python", "-O", "agent.py", "start"]
