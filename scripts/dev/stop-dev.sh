#!/bin/bash

# Stop Development Environment for Job Finder Worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🛑 Stopping Job Finder Development Environment"
echo ""

# Stop worker container
echo "🐳 Stopping Worker Container..."
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml down

echo ""
echo "🔥 Stopping Firebase Emulators..."

# Find and kill emulator processes
if pgrep -f "firebase emulators:start" > /dev/null; then
  pkill -f "firebase emulators:start"
  echo "   ✅ Emulators stopped"
else
  echo "   ℹ️  No emulator processes found"
fi

# Clean up log file
if [ -f /tmp/firebase-emulators.log ]; then
  rm /tmp/firebase-emulators.log
fi

echo ""
echo "✅ Development environment stopped"
echo ""
echo "💡 Tip: Emulator data is preserved in .firebase/emulator-data/"
echo "   To start fresh: cd ../job-finder-BE && npm run emulators:clear"
