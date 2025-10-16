#!/bin/bash
set -e

echo "========================================="
echo "Job Finder Container Starting"
echo "========================================="
echo "Current time: $(date)"
echo "Timezone: $TZ"
echo "Environment: $ENVIRONMENT"
echo "Queue Mode: ${ENABLE_QUEUE_MODE:-false}"
echo ""

# Save environment variables for cron
echo "Saving environment variables for cron..."
printenv > /etc/environment

# Show cron schedule
echo "Cron schedule:"
cat /etc/cron.d/job-finder-cron | grep -v '^#' | grep -v '^$'
echo ""

# Calculate next run time
CURRENT_HOUR=$(date +%H)
CURRENT_MIN=$(date +%M)
NEXT_RUN_HOUR=$(( (CURRENT_HOUR / 6 + 1) * 6 ))
if [ $NEXT_RUN_HOUR -ge 24 ]; then
    NEXT_RUN_HOUR=0
fi

echo "Next scheduled run: $(printf "%02d:00" $NEXT_RUN_HOUR)"
echo ""

# Start cron
echo "Starting cron daemon..."
cron

# Check if cron is running
if pgrep cron > /dev/null; then
    echo "✓ Cron daemon started successfully"
else
    echo "✗ ERROR: Cron daemon failed to start!"
    exit 1
fi

# Start queue worker if enabled
if [ "${ENABLE_QUEUE_MODE}" = "true" ]; then
    echo ""
    echo "========================================="
    echo "Starting Queue Worker Daemon"
    echo "========================================="
    echo "Queue worker will process jobs from Firestore queue"
    echo ""

    # Ensure logs directory exists
    mkdir -p /app/logs

    # Start queue worker in background
    /usr/local/bin/python /app/queue_worker.py >> /app/logs/queue_worker.log 2>&1 &
    QUEUE_WORKER_PID=$!

    # Wait a moment and check if it started
    sleep 2
    if ps -p $QUEUE_WORKER_PID > /dev/null; then
        echo "✓ Queue worker started successfully (PID: $QUEUE_WORKER_PID)"
    else
        echo "✗ ERROR: Queue worker failed to start!"
        exit 1
    fi

    echo ""
    echo "Container is running in DUAL-PROCESS mode:"
    echo "  1. Cron (every 6h) - Scrapes sources and adds to queue"
    echo "  2. Queue Worker (continuous) - Processes queue items"
    echo "========================================="
else
    echo ""
    echo "Container is running in LEGACY mode (direct processing)"
    echo "Queue mode disabled. Use ENABLE_QUEUE_MODE=true to enable."
    echo "========================================="
fi

echo ""
echo "Monitor logs:"
echo "  - Cron output: tail -f /var/log/cron.log"
echo "  - Queue worker: tail -f /app/logs/queue_worker.log"
echo "========================================="
echo ""

# Tail both logs (this keeps container running and shows output)
if [ "${ENABLE_QUEUE_MODE}" = "true" ]; then
    # Tail both cron and queue worker logs
    exec tail -f /var/log/cron.log /app/logs/queue_worker.log
else
    # Tail just cron log
    exec tail -f /var/log/cron.log
fi
