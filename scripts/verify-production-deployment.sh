#!/bin/bash
# Verify production deployment of job type filtering system

echo "=========================================="
echo "Production Deployment Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on production server
if [[ ! -d "/opt/stacks/job-finder" ]]; then
    echo -e "${YELLOW}⚠️  Not running on production server${NC}"
    echo "Run this script on bignasty.local"
    exit 1
fi

cd /opt/stacks/job-finder || exit 1

echo "1️⃣  Checking Git status..."
git fetch origin main -q
CURRENT_COMMIT=$(git rev-parse HEAD)
MAIN_COMMIT=$(git rev-parse origin/main)

if [[ "$CURRENT_COMMIT" == "$MAIN_COMMIT" ]]; then
    echo -e "${GREEN}✅ Code is up to date with main${NC}"
else
    echo -e "${RED}❌ Code is NOT up to date with main${NC}"
    echo "   Current: $CURRENT_COMMIT"
    echo "   Main:    $MAIN_COMMIT"
    echo ""
    echo "Run: git pull origin main"
    exit 1
fi

echo ""
echo "2️⃣  Checking Docker container status..."
CONTAINER_NAME="job-finder-production"
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}" | grep -q "Up"; then
    echo -e "${GREEN}✅ Container is running${NC}"
    CONTAINER_IMAGE=$(docker inspect $CONTAINER_NAME --format='{{.Config.Image}}')
    echo "   Image: $CONTAINER_IMAGE"
else
    echo -e "${RED}❌ Container is not running${NC}"
    exit 1
fi

echo ""
echo "3️⃣  Checking for filtering code in container..."
if docker exec $CONTAINER_NAME test -f /app/src/job_finder/utils/job_type_filter.py; then
    echo -e "${GREEN}✅ Job type filter module exists${NC}"
else
    echo -e "${RED}❌ Job type filter module NOT found${NC}"
    echo "   Container may need to be rebuilt"
    exit 1
fi

echo ""
echo "4️⃣  Checking recent logs for filtering activity..."
echo -e "${YELLOW}Recent log entries:${NC}"
docker logs $CONTAINER_NAME --tail 50 2>&1 | grep -E "(Filtered|role/seniority|filter_job)" | tail -10 || echo "   No filtering logs found yet (may not have run since deployment)"

echo ""
echo "5️⃣  Checking for max_tokens errors..."
MAX_TOKEN_ERRORS=$(docker logs $CONTAINER_NAME --tail 200 2>&1 | grep -c "max_tokens: 5000")
if [[ $MAX_TOKEN_ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✅ No max_tokens errors found${NC}"
else
    echo -e "${RED}❌ Found $MAX_TOKEN_ERRORS max_tokens errors${NC}"
    echo "   Code may not be updated properly"
fi

echo ""
echo "6️⃣  Checking config for filtering settings..."
if docker exec $CONTAINER_NAME grep -q "strict_role_filtering" /app/config/config.yaml 2>/dev/null; then
    echo -e "${GREEN}✅ Filtering config exists${NC}"
    echo "   Settings:"
    docker exec $CONTAINER_NAME grep -A 2 "strict_role_filtering" /app/config/config.yaml
else
    echo -e "${RED}❌ Filtering config NOT found${NC}"
    echo "   Config may need updating"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "To monitor live logs:"
echo "  docker logs $CONTAINER_NAME -f"
echo ""
echo "To trigger a manual search:"
echo "  docker exec $CONTAINER_NAME python run_search.py"
