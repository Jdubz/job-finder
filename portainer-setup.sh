#!/bin/bash
# Setup script for Portainer host
# Run this on the Portainer host machine (bignasty.local)

set -e

echo "Setting up job-finder directories on Portainer host..."

# Create staging environment directories
echo "Creating staging directories..."
sudo mkdir -p /opt/job-finder-staging/{credentials,config,logs,data}
sudo chown -R $USER:$USER /opt/job-finder-staging
chmod 700 /opt/job-finder-staging/credentials
chmod 755 /opt/job-finder-staging/{config,logs,data}

# Create production environment directories
echo "Creating production directories..."
sudo mkdir -p /opt/job-finder-production/{credentials,config,logs,data}
sudo chown -R $USER:$USER /opt/job-finder-production
chmod 700 /opt/job-finder-production/credentials
chmod 755 /opt/job-finder-production/{config,logs,data}

echo ""
echo "✅ Directories created successfully!"
echo ""
echo "Next steps:"
echo "1. Upload Firebase credentials:"
echo "   Staging:    /opt/job-finder-staging/credentials/serviceAccountKey.json"
echo "   Production: /opt/job-finder-production/credentials/serviceAccountKey.json"
echo ""
echo "2. Upload config files (optional, can use defaults):"
echo "   Staging:    /opt/job-finder-staging/config/config.yaml"
echo "   Production: /opt/job-finder-production/config/config.yaml"
echo ""
echo "3. Set permissions on credentials:"
echo "   chmod 600 /opt/job-finder-staging/credentials/serviceAccountKey.json"
echo "   chmod 600 /opt/job-finder-production/credentials/serviceAccountKey.json"
echo ""
echo "4. Deploy stack in Portainer using the provided docker-compose files"
