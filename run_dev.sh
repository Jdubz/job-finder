#!/bin/bash
# Development runner for Flask Job Queue Worker
set -e

echo "🚀 Starting Job Queue Worker (Development Mode)"
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

# Set development environment variables
export FLASK_ENV=development
export WORKER_PORT=${WORKER_PORT:-5555}
export WORKER_HOST=${WORKER_HOST:-127.0.0.1}
export QUEUE_WORKER_LOG_FILE=${QUEUE_WORKER_LOG_FILE:-logs/worker.log}
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Create logs directory
mkdir -p logs

echo "📋 Configuration:"
echo "   Environment: DEVELOPMENT"
echo "   Port: $WORKER_PORT"
echo "   Host: $WORKER_HOST"
echo "   Log File: $QUEUE_WORKER_LOG_FILE"
echo "   Python Path: $PYTHONPATH"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Using default configuration."
    echo "   Copy .env.example to .env and configure your API keys."
    echo ""
fi

# Start the Flask worker
echo "🔄 Starting worker..."
echo "   Health endpoint: http://$WORKER_HOST:$WORKER_PORT/health"
echo "   Status endpoint: http://$WORKER_HOST:$WORKER_PORT/status"
echo "   Shutdown endpoint: POST http://$WORKER_HOST:$WORKER_PORT/shutdown"
echo ""

python3 -m job_finder.flask_worker
