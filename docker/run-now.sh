#!/bin/bash
# Helper script to manually trigger job search in production container
# Usage: docker exec job-finder-staging /app/docker/run-now.sh

echo "========================================"
echo "Manually Triggering Job Search"
echo "========================================"
echo "Started at: $(date)"
echo ""

# Run the scheduler
cd /app
/usr/local/bin/python scheduler.py

echo ""
echo "========================================"
echo "Job Search Completed"
echo "Finished at: $(date)"
echo "========================================"
