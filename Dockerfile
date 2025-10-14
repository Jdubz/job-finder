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

# Install runtime dependencies (cron for scheduling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run_job_search.py .
COPY setup_job_listings.py .
COPY scheduler.py .

# Copy cron configuration
COPY docker/crontab /etc/cron.d/job-finder-cron

# Set proper permissions for cron
RUN chmod 0644 /etc/cron.d/job-finder-cron && \
    crontab /etc/cron.d/job-finder-cron && \
    touch /var/log/cron.log

# Make PATH include user-installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Healthcheck
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command: run cron in foreground with logging
CMD printenv > /etc/environment && cron && tail -f /var/log/cron.log
