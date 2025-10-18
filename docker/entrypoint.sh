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

# Check if cron should be enabled (default: true for backward compatibility)
ENABLE_CRON=${ENABLE_CRON:-true}

if [ "${ENABLE_CRON}" = "true" ]; then
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
else
    echo "Cron disabled (ENABLE_CRON=false)"
    echo "Job scraping will only run via manual queue submissions"
    echo ""
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
    if [ "${ENABLE_CRON}" = "true" ]; then
        echo "Container is running in DUAL-PROCESS mode:"
        echo "  1. Cron (every 6h) - Scrapes sources and adds to queue"
        echo "  2. Queue Worker (continuous) - Processes queue items"
    else
        echo "Container is running in QUEUE-ONLY mode:"
        echo "  - Cron disabled (manual queue submissions only)"
        echo "  - Queue Worker (continuous) - Processes queue items"
    fi
    echo "========================================="
else
    echo ""
    if [ "${ENABLE_CRON}" = "true" ]; then
        echo "Container is running in LEGACY mode (direct processing)"
        echo "Queue mode disabled. Use ENABLE_QUEUE_MODE=true to enable."
    else
        echo "Container is running in IDLE mode:"
        echo "  - Cron disabled (ENABLE_CRON=false)"
        echo "  - Queue disabled (ENABLE_QUEUE_MODE=false)"
        echo "  - No automatic processing will occur"
    fi
    echo "========================================="
fi

echo ""
echo "Monitor logs:"
if [ "${ENABLE_CRON}" = "true" ]; then
    echo "  - Cron output: tail -f /var/log/cron.log"
fi
if [ "${ENABLE_QUEUE_MODE}" = "true" ]; then
    echo "  - Queue worker: tail -f /app/logs/queue_worker.log"
fi
echo "========================================="
echo ""

# Tail logs (this keeps container running and shows output)
if [ "${ENABLE_QUEUE_MODE}" = "true" ] && [ "${ENABLE_CRON}" = "true" ]; then
    # Tail both cron and queue worker logs
    exec tail -f /var/log/cron.log /app/logs/queue_worker.log
elif [ "${ENABLE_QUEUE_MODE}" = "true" ]; then
    # Tail just queue worker log
    exec tail -f /app/logs/queue_worker.log
elif [ "${ENABLE_CRON}" = "true" ]; then
    # Tail just cron log
    exec tail -f /var/log/cron.log
else
    # Neither enabled - just keep container alive
    echo "No active processes to monitor. Container will sleep indefinitely."
    exec sleep infinity
fi
