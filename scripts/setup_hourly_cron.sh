#!/bin/bash
# Setup cron job for hourly scraping during daytime hours (6am-10pm PT)
#
# This script creates a crontab entry that runs the hourly scheduler
# every hour. The scheduler itself checks if it's within daytime hours
# before actually scraping.

# Get the absolute path to the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Path to the scheduler script
SCHEDULER_PATH="$PROJECT_DIR/scripts/workers/hourly_scheduler.py"

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
if crontab -l 2>/dev/null | grep -q "hourly_scheduler.py"; then
    echo "⚠️  Cron entry already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "hourly_scheduler.py" | crontab -
fi

# Add the new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "The scheduler will run every hour and automatically:"
echo "  - Check if it's daytime hours (6am-10pm Pacific Time)"
echo "  - Rotate through job sources by lastScrapedAt (oldest first)"
echo "  - Stop after finding 5 potential matches OR scraping all sources"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To view scheduler logs:"
echo "  tail -f /var/log/job-finder-scheduler.log"
echo ""
echo "To remove the cron job:"
echo "  crontab -e  # Then delete the line containing 'hourly_scheduler.py'"
