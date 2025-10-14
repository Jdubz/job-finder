#!/bin/bash
# Commands to run on bignasty.local (OMV) to set up job-finder
# You can either:
# 1. Copy this file to OMV and run it: bash omv-setup-commands.sh
# 2. Run commands one by one manually

set -e

echo "=== Setting up job-finder on OMV (bignasty.local) ==="

# Base path on your OMV storage
BASE_PATH="/srv/dev-disk-by-uuid-45e47416-96ad-41be-9fc0-582e15241cbd/storage/jobscraper"

echo "Checking existing directory..."
ls -la "$BASE_PATH"

echo ""
echo "Creating subdirectories for staging and production..."

# Create staging directories
mkdir -p "$BASE_PATH/staging/credentials"
mkdir -p "$BASE_PATH/staging/config"
mkdir -p "$BASE_PATH/staging/logs"
mkdir -p "$BASE_PATH/staging/data"

# Create production directories
mkdir -p "$BASE_PATH/production/credentials"
mkdir -p "$BASE_PATH/production/config"
mkdir -p "$BASE_PATH/production/logs"
mkdir -p "$BASE_PATH/production/data"

# Set permissions
chmod 755 "$BASE_PATH/staging"
chmod 700 "$BASE_PATH/staging/credentials"
chmod 755 "$BASE_PATH/staging/config"
chmod 755 "$BASE_PATH/staging/logs"
chmod 755 "$BASE_PATH/staging/data"

chmod 755 "$BASE_PATH/production"
chmod 700 "$BASE_PATH/production/credentials"
chmod 755 "$BASE_PATH/production/config"
chmod 755 "$BASE_PATH/production/logs"
chmod 755 "$BASE_PATH/production/data"

echo ""
echo "✅ Directory structure created:"
tree -L 2 "$BASE_PATH" 2>/dev/null || find "$BASE_PATH" -type d

echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Copy Firebase credentials to:"
echo "   Staging:    $BASE_PATH/staging/credentials/serviceAccountKey.json"
echo "   Production: $BASE_PATH/production/credentials/serviceAccountKey.json"
echo ""
echo "2. Set correct permissions:"
echo "   chmod 600 $BASE_PATH/staging/credentials/serviceAccountKey.json"
echo "   chmod 600 $BASE_PATH/production/credentials/serviceAccountKey.json"
echo ""
echo "3. (Optional) Copy config files to:"
echo "   $BASE_PATH/staging/config/config.yaml"
echo "   $BASE_PATH/production/config/config.yaml"
echo ""
echo "4. Deploy stack in Portainer using the docker-compose files"
echo ""

# Check if serviceAccountKey.json exists in the base directory
if [ -f "$BASE_PATH/serviceAccountKey.json" ]; then
    echo "Found serviceAccountKey.json in base directory."
    read -p "Copy to staging and production? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$BASE_PATH/serviceAccountKey.json" "$BASE_PATH/staging/credentials/"
        cp "$BASE_PATH/serviceAccountKey.json" "$BASE_PATH/production/credentials/"
        chmod 600 "$BASE_PATH/staging/credentials/serviceAccountKey.json"
        chmod 600 "$BASE_PATH/production/credentials/serviceAccountKey.json"
        echo "✅ Credentials copied to staging and production"
    fi
fi

echo ""
echo "Setup complete!"
