# Firestore Indexes Deployment

This document explains how to deploy Firestore indexes to staging and production databases.

## Overview

The job-finder application requires a composite index on the `job-queue` collection to efficiently query for pending jobs in FIFO order.

**Required Index:**
- Collection: `job-queue`
- Fields:
  - `status` (Ascending)
  - `created_at` (Ascending)

## Index Configuration

The index is defined in `firestore.indexes.json`:

```json
{
  "collectionGroup": "job-queue",
  "queryScope": "COLLECTION",
  "fields": [
    {
      "fieldPath": "status",
      "order": "ASCENDING"
    },
    {
      "fieldPath": "created_at",
      "order": "ASCENDING"
    }
  ]
}
```

## Deployment Methods

### Method 1: Firebase Console (Manual)

**For Staging:**
1. Go to https://console.firebase.google.com/project/static-sites-257923/firestore/databases/portfolio-staging/indexes
2. Click "Create Index"
3. Set Collection ID: `job-queue`
4. Add fields:
   - Field: `status`, Order: Ascending
   - Field: `created_at`, Order: Ascending
5. Click "Create"
6. Wait 2-5 minutes for index to build

**For Production:**
1. Go to https://console.firebase.google.com/project/static-sites-257923/firestore/databases/(default)/indexes
2. Follow same steps as staging

### Method 2: Firebase CLI (Automated)

**Prerequisites:**
```bash
npm install -g firebase-tools
firebase login
```

**Deploy to Staging:**
```bash
# Deploy indexes to portfolio-staging database
firebase firestore:indexes --database=portfolio-staging

# Or use the Makefile
make firestore-indexes-staging
```

**Deploy to Production:**
```bash
# Deploy indexes to default (production) database
firebase deploy --only firestore:indexes

# Or use the Makefile
make firestore-indexes-prod
```

**Deploy to Both:**
```bash
# Deploy to staging and production
make firestore-indexes-all
```

## Makefile Commands

Add these to your `Makefile`:

```makefile
.PHONY: firestore-indexes-staging firestore-indexes-prod firestore-indexes-all

firestore-indexes-staging: ## Deploy Firestore indexes to staging
	@echo "$(CYAN)Deploying Firestore indexes to portfolio-staging...$(RESET)"
	firebase firestore:indexes --database=portfolio-staging

firestore-indexes-prod: ## Deploy Firestore indexes to production
	@echo "$(CYAN)Deploying Firestore indexes to production...$(RESET)"
	firebase deploy --only firestore:indexes

firestore-indexes-all: ## Deploy Firestore indexes to all environments
	@echo "$(CYAN)Deploying Firestore indexes to all environments...$(RESET)"
	@$(MAKE) firestore-indexes-staging
	@$(MAKE) firestore-indexes-prod
```

## Verification

### Check Index Status

**Staging:**
```bash
firebase firestore:indexes --database=portfolio-staging
```

**Production:**
```bash
firebase firestore:indexes
```

### Test Query

Once the index is built, test with Python:

```python
from job_finder.storage.firestore_client import FirestoreClient

# For staging
db = FirestoreClient.get_client('portfolio-staging', '.firebase/static-sites-257923-firebase-adminsdk.json')

# Test query that requires the index
query = db.collection('job-queue') \
    .where('status', '==', 'pending') \
    .order_by('created_at') \
    .limit(10)

results = query.get()
print(f'✓ Index working! Found {len(results)} pending items')
```

## Troubleshooting

### Index Still Building

If you see "index is currently building":
- Wait 2-5 minutes
- Larger databases may take longer
- Check status in Firebase Console

### Index Creation Failed

If creation fails:
- Check Firebase permissions
- Ensure you're logged in: `firebase login`
- Verify project ID in `.firebaserc`

### Query Still Fails After Index Built

If queries still fail after index shows as "Ready":
1. Wait another minute (propagation delay)
2. Restart the queue worker
3. Check that field names match exactly (`created_at` not `createdAt`)

## Index URL Templates

**Staging Index Console:**
```
https://console.firebase.google.com/project/static-sites-257923/firestore/databases/portfolio-staging/indexes
```

**Production Index Console:**
```
https://console.firebase.google.com/project/static-sites-257923/firestore/databases/(default)/indexes
```

## When to Create Indexes

Create this index:
- ✅ Before first deployment to a new environment
- ✅ When setting up staging database
- ✅ When setting up production database
- ✅ After database migrations that clear indexes

## Notes

- Index building time depends on collection size
- Empty collections build instantly
- Large collections (1000+ docs) may take 10-15 minutes
- Indexes persist even if documents are deleted
- Indexes are database-specific (staging needs its own copy)
