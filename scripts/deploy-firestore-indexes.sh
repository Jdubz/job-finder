#!/bin/bash
# Deploy Firestore composite indexes from firestore.indexes.json
#
# Usage:
#   ./scripts/deploy-firestore-indexes.sh [database]
#
# Arguments:
#   database: Target database (portfolio or portfolio-staging). Default: portfolio
#
# Examples:
#   ./scripts/deploy-firestore-indexes.sh                    # Deploy to production
#   ./scripts/deploy-firestore-indexes.sh portfolio-staging  # Deploy to staging

set -e

# Configuration
PROJECT_ID="static-sites-257923"
DATABASE="${1:-portfolio}"
INDEXES_FILE="firestore.indexes.json"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if indexes file exists
if [ ! -f "$INDEXES_FILE" ]; then
    echo -e "${RED}✗ Error: $INDEXES_FILE not found${NC}"
    echo "  Run this script from the project root directory"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}✗ Error: jq is not installed${NC}"
    echo "  Install with: sudo apt-get install jq  (or brew install jq on macOS)"
    exit 1
fi

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}✗ Error: gcloud CLI is not installed${NC}"
    echo "  Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠ Warning: Not authenticated with gcloud${NC}"
    echo "  Run: gcloud auth login"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploying Firestore Indexes${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  Project: ${GREEN}$PROJECT_ID${NC}"
echo -e "  Database: ${GREEN}$DATABASE${NC}"
echo -e "  Indexes file: ${GREEN}$INDEXES_FILE${NC}"
echo ""

# Parse and create each index
INDEX_COUNT=0
SUCCESS_COUNT=0
SKIP_COUNT=0

cat "$INDEXES_FILE" | jq -c '.indexes[]' | while IFS= read -r index; do
    COLLECTION=$(echo "$index" | jq -r '.collectionGroup')
    INDEX_COUNT=$((INDEX_COUNT + 1))

    echo -e "${BLUE}📦 Collection: $COLLECTION${NC}"

    # Build gcloud command
    CMD="gcloud firestore indexes composite create \
        --project=$PROJECT_ID \
        --database=$DATABASE \
        --collection-group=$COLLECTION \
        --query-scope=COLLECTION"

    # Add each field configuration
    echo "$index" | jq -c '.fields[]' | while IFS= read -r field; do
        FIELD_PATH=$(echo "$field" | jq -r '.fieldPath')
        ORDER=$(echo "$field" | jq -r '.order // empty')

        if [ ! -z "$ORDER" ]; then
            ORDER_LOWER=$(echo "$ORDER" | tr '[:upper:]' '[:lower:]')
            echo -e "   • $FIELD_PATH ${GREEN}($ORDER_LOWER)${NC}"
            CMD="$CMD --field-config field-path=$FIELD_PATH,order=$ORDER_LOWER"
        fi
    done

    # Execute the command
    if eval "$CMD --quiet" 2>&1 | grep -q "ALREADY_EXISTS\|already exists"; then
        echo -e "   ${YELLOW}⊙ Index already exists${NC}"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        echo -e "   ${GREEN}✓ Index created${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
    echo ""
done

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  Created: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "  Skipped (already exists): ${YELLOW}$SKIP_COUNT${NC}"
echo ""

# List all indexes
echo -e "${BLUE}Current indexes in $DATABASE:${NC}"
echo ""
gcloud firestore indexes composite list \
    --project=$PROJECT_ID \
    --database=$DATABASE \
    --format="table(name.basename(),collectionGroup,state)" \
    | grep -E "job-queue|job-matches|job-sources|generator|NAME" || echo "No indexes found"

echo ""
echo -e "${GREEN}✓ Done!${NC}"
