#!/bin/bash

# Start Development Environment for Job Finder Worker
# This script coordinates starting emulators and the worker container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BE_REPO="$(cd "$PROJECT_ROOT/../job-finder-BE" && pwd)"

echo "🚀 Starting Job Finder Development Environment"
echo ""

# Check if emulators are already running
if curl -s http://localhost:4000 > /dev/null 2>&1; then
  echo "✅ Firebase Emulators are already running"
else
  echo "📦 Starting Firebase Emulators..."
  echo "   Location: $BE_REPO"
  echo ""

  if [ ! -d "$BE_REPO" ]; then
    echo "❌ Error: job-finder-BE repository not found at $BE_REPO"
    echo "   Please ensure the BE repository is cloned in the same parent directory"
    exit 1
  fi

  # Start emulators in the background
  echo "   Starting emulators in background..."
  cd "$BE_REPO/functions"
  npm run emulators:start > /tmp/firebase-emulators.log 2>&1 &
  EMULATOR_PID=$!

  echo "   Waiting for emulators to start (PID: $EMULATOR_PID)..."

  # Wait for emulators to be ready (max 30 seconds)
  for i in {1..30}; do
    if curl -s http://localhost:4000 > /dev/null 2>&1; then
      echo "   ✅ Emulators started successfully"
      break
    fi

    if [ $i -eq 30 ]; then
      echo "   ❌ Emulators failed to start within 30 seconds"
      echo "   Check logs: tail -f /tmp/firebase-emulators.log"
      exit 1
    fi

    sleep 1
  done
fi

echo ""
echo "🔍 Emulator Status:"
echo "   UI: http://localhost:4000"
echo "   Firestore: localhost:8080"
echo "   Auth: localhost:9099"
echo "   Functions: localhost:5001"
echo ""

# Start worker container
echo "🐳 Starting Worker Container..."
cd "$PROJECT_ROOT"

# Check if container is already running
if docker ps | grep -q job-finder-dev; then
  echo "   Container already running - restarting..."
  docker-compose -f docker-compose.dev.yml restart
else
  echo "   Starting fresh container..."
  docker-compose -f docker-compose.dev.yml up -d
fi

echo ""
echo "✅ Development Environment Ready!"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker-compose -f docker-compose.dev.yml logs -f"
echo "   Enter shell:  docker-compose -f docker-compose.dev.yml exec job-finder bash"
echo "   Restart:      docker-compose -f docker-compose.dev.yml restart"
echo "   Stop all:     ./scripts/dev/stop-dev.sh"
echo ""
echo "🌐 Access Points:"
echo "   Emulator UI:  http://localhost:4000"
echo "   Worker logs:  docker-compose -f docker-compose.dev.yml logs -f"
