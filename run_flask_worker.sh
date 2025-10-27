#!/bin/bash
# Start the Flask-based job queue worker
set -e

echo "🚀 Starting Flask-based Job Queue Worker"
echo "========================================"

# Change to the worker directory
cd "$(dirname "$0")"

# Set environment variables
export WORKER_PORT=${WORKER_PORT:-5555}
export WORKER_HOST=${WORKER_HOST:-0.0.0.0}
export LOG_FILE=${LOG_FILE:-"logs/worker.log"}

# Create logs directory if it doesn't exist
mkdir -p logs

echo "📋 Configuration:"
echo "   Port: $WORKER_PORT"
echo "   Host: $WORKER_HOST"
echo "   Log File: $LOG_FILE"
echo ""

# Start the Flask worker
echo "🔄 Starting worker..."
python3 -m job_finder.flask_worker