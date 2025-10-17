# GitHub Actions Setup

This directory contains GitHub Actions workflows for CI/CD automation.

## Required Secrets

The following secrets must be configured in the GitHub repository for workflows to function properly:

### `GCP_SA_KEY`

**Required for**: `deploy-firestore-indexes.yml`

**Description**: Google Cloud Platform service account key for Firestore index deployment.

**Setup Instructions**:

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GCP_SA_KEY`
4. Value: Paste the **entire contents** of your service account JSON key file

**Finding the service account key**:
- Local path: `.firebase/static-sites-257923-firebase-adminsdk.json`
- Or download from: [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts?project=static-sites-257923)

**Required permissions**:
- `datastore.indexes.create`
- `datastore.indexes.list`
- `datastore.indexes.get`

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

**Cause**: The `GCP_SA_KEY` secret is not set in GitHub repository secrets.

**Fix**: Follow the setup instructions above to add the secret.

### Error: "Permission denied" when deploying indexes

**Cause**: Service account lacks necessary Firestore permissions.

**Fix**: Grant the service account the **Cloud Datastore Owner** role:
```bash
gcloud projects add-iam-policy-binding static-sites-257923 \
  --member="serviceAccount:YOUR_SA_EMAIL@static-sites-257923.iam.gserviceaccount.com" \
  --role="roles/datastore.owner"
```
