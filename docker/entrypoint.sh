#!/bin/bash
set -e

echo "========================================="
echo "Job Finder Container Starting"
echo "========================================="
echo "Current time: $(date)"
echo "Timezone: $TZ"
echo "Environment: $ENVIRONMENT"
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

echo ""
echo "Container is ready and waiting for scheduled runs."
echo "Monitor this log for job execution output."
echo "========================================="
echo ""

# Tail the cron log (this keeps container running and shows output)
exec tail -f /var/log/cron.log
