#!/bin/bash
# Production runner for Flask Job Queue Worker
set -e

echo "🚀 Starting Job Queue Worker (Production Mode)"
echo "==============================================="

# Change to script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set production environment variables
export FLASK_ENV=production
export WORKER_PORT=${WORKER_PORT:-5555}
export WORKER_HOST=${WORKER_HOST:-0.0.0.0}
export QUEUE_WORKER_LOG_FILE=${QUEUE_WORKER_LOG_FILE:-logs/worker.log}
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Create logs directory
mkdir -p logs

# Check required environment variables
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ GOOGLE_APPLICATION_CREDENTIALS not set!"
    echo "   Set this to the path of your Firebase service account key"
    exit 1
fi

if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ Firebase credentials file not found: $GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

echo "📋 Configuration:"
echo "   Environment: PRODUCTION"
echo "   Port: $WORKER_PORT"
echo "   Host: $WORKER_HOST"
echo "   Log File: $QUEUE_WORKER_LOG_FILE"
echo ""

# Start the Flask worker with production settings
echo "🔄 Starting worker..."
exec python3 -m job_finder.flask_worker
