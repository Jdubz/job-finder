#!/bin/bash
# Run queue worker locally with staging database configuration

# Set environment variables
export PROFILE_DATABASE_NAME=portfolio-staging
export STORAGE_DATABASE_NAME=portfolio-staging
export QUEUE_WORKER_LOG_FILE=./logs/queue_worker.log

# Ensure logs directory exists
mkdir -p logs

# Run worker
source venv/bin/activate
python scripts/workers/queue_worker.py
