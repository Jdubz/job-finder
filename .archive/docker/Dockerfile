# Multi-stage build for Job Finder
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies (cron for scheduling, procps for pgrep)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run_job_search.py .
COPY scripts/workers/queue_worker.py .
COPY src/job_finder/simple_flask_worker.py .

# Copy cron configuration, entrypoint, and helper scripts
COPY docker/crontab /etc/cron.d/job-finder-cron
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/run-now.sh /app/docker/run-now.sh

# Set proper permissions for cron and scripts
RUN chmod 0644 /etc/cron.d/job-finder-cron && \
    crontab /etc/cron.d/job-finder-cron && \
    touch /var/log/cron.log && \
    chmod +x /app/entrypoint.sh && \
    chmod +x /app/docker/run-now.sh

# Make PATH include user-installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/src:/app

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Healthcheck - check Flask worker health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1

# Use entrypoint script for better logging and startup
ENTRYPOINT ["/app/entrypoint.sh"]
