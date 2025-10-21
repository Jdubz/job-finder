#!/bin/bash

# Enter Development Container Shell

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Check if container is running
if ! docker ps | grep -q job-finder-dev; then
  echo "❌ Development container is not running"
  echo "   Start it first: ./scripts/dev/start-dev.sh"
  exit 1
fi

echo "🐚 Entering development container shell..."
echo ""

docker-compose -f docker-compose.dev.yml exec job-finder bash
