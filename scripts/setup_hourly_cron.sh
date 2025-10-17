#!/bin/bash
# Setup cron job for hourly scraping during daytime hours (6am-10pm PT)
#
# This script creates a crontab entry that runs the hourly scheduler
# every hour. The scheduler itself checks if it's within daytime hours
# before actually scraping.

# Get the absolute path to the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Path to the hourly cron script
SCHEDULER_PATH="$PROJECT_DIR/scripts/workers/hourly_cron.py"

# Path to the virtual environment
VENV_PATH="$PROJECT_DIR/venv"

# Cron entry - runs every hour
CRON_ENTRY="0 * * * * cd $PROJECT_DIR && source $VENV_PATH/bin/activate && python $SCHEDULER_PATH >> /var/log/job-finder-scheduler.log 2>&1"

echo "Setting up hourly cron job for job scraper..."
echo ""
echo "Project directory: $PROJECT_DIR"
echo "Scheduler script: $SCHEDULER_PATH"
echo "Virtual environment: $VENV_PATH"
echo ""
echo "Cron entry:"
echo "$CRON_ENTRY"
echo ""

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "hourly_cron.py"; then
    echo "⚠️  Cron entry already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "hourly_cron.py" | crontab -
fi

# Also remove old hourly_scheduler.py entries if they exist
if crontab -l 2>/dev/null | grep -q "hourly_scheduler.py"; then
    echo "⚠️  Removing old hourly_scheduler.py entry..."
    crontab -l 2>/dev/null | grep -v "hourly_scheduler.py" | crontab -
fi

# Add the new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "The hourly cron will run every hour and automatically:"
echo "  - Check if it's daytime hours (6am-10pm Pacific Time)"
echo "  - Add a SCRAPE request to the queue (if no pending scrape exists)"
echo "  - Queue worker processes scrapes with source rotation and early exit"
echo ""
echo "How it works:"
echo "  1. Hourly cron creates SCRAPE queue items"
echo "  2. Queue worker picks them up and runs the scraping logic"
echo "  3. Scraper rotates through sources (oldest first)"
echo "  4. Stops after finding configured potential matches (default: 5)"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To view cron logs:"
echo "  tail -f /var/log/job-finder-scheduler.log"
echo ""
echo "To view queue worker logs:"
echo "  docker logs -f job-finder-worker"
echo ""
echo "To trigger a manual scrape:"
echo "  python scripts/trigger_scrape.py --help"
echo ""
echo "To remove the cron job:"
echo "  crontab -e  # Then delete the line containing 'hourly_cron.py'"
