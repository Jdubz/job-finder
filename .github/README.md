# GitHub Actions Setup

This directory contains GitHub Actions workflows for CI/CD automation.

## Required Secrets

The following secrets must be configured in the GitHub repository for workflows to function properly:

### `FIREBASE_SERVICE_ACCOUNT`

**Required for**: `deploy-firestore-indexes.yml`

**Description**: Google Cloud Platform service account key for Firestore index deployment.

**Status**: ✅ Already configured in repository

**Required permissions**:
- `datastore.indexes.create`
- `datastore.indexes.list`
- `datastore.indexes.get`

**To update or verify**:
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Verify `FIREBASE_SERVICE_ACCOUNT` exists
3. If needed, update with contents of `.firebase/static-sites-257923-firebase-adminsdk.json`

## Workflows

### `tests.yml`
- **Trigger**: Push/PR to `main` or `develop`
- **Purpose**: Run tests, type checking, and code quality checks
- **Secrets**: None required

### `docker-build-push.yml`
- **Trigger**: Push to `main`
- **Purpose**: Build and push Docker images to GHCR
- **Secrets**: None required (uses GitHub token)

### `deploy-firestore-indexes.yml`
- **Trigger**:
  - Push to `main` when `firestore.indexes.json` changes
  - Manual workflow dispatch
- **Purpose**: Deploy Firestore composite indexes to production/staging
- **Secrets**: `GCP_SA_KEY` ⚠️ **REQUIRED**

## Manual Deployment

You can manually deploy Firestore indexes without GitHub Actions:

```bash
# Install gcloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project static-sites-257923

# Deploy indexes to production
bash -c 'cat firestore.indexes.json | jq -c ".indexes[]" | while read index; do
  COLLECTION=$(echo "$index" | jq -r ".collectionGroup")
  echo "Creating index for: $COLLECTION"
  # Build and execute gcloud command...
done'

# Or use the deployment script (if created)
./scripts/deploy-firestore-indexes.sh portfolio
```

## Troubleshooting

### Error: "workflow must specify exactly one of workload_identity_provider or credentials_json"

**Cause**: The `FIREBASE_SERVICE_ACCOUNT` secret is not set or is empty in GitHub repository secrets.

**Fix**: Verify the secret exists in repository settings. If not, add it with the contents of `.firebase/static-sites-257923-firebase-adminsdk.json`

### Error: "Permission denied" when deploying indexes

**Cause**: Service account lacks necessary Firestore permissions.

**Fix**: Grant the service account the **Cloud Datastore Owner** role:
```bash
gcloud projects add-iam-policy-binding static-sites-257923 \
  --member="serviceAccount:YOUR_SA_EMAIL@static-sites-257923.iam.gserviceaccount.com" \
  --role="roles/datastore.owner"
```
