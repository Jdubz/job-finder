# Production Queue Troubleshooting Guide

## Quick Links

### Google Cloud Logging

View container logs directly in Google Cloud Console (no SSH required):

**Production Container Logs:**
- [All Logs](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-production%22;timeRange=PT1H?project=static-sites-257923) (last hour)
- [Errors Only](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-production%22%0Aseverity%3E%3DERROR;timeRange=PT1H?project=static-sites-257923)
- [Queue Processing](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-production%22%0AtextPayload%3D~%22Found%20.%2B%20pending%20items%22;timeRange=PT1H?project=static-sites-257923)

**Staging Container Logs:**
- [All Logs](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-staging%22;timeRange=PT1H?project=static-sites-257923) (last hour)
- [Errors Only](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-staging%22%0Aseverity%3E%3DERROR;timeRange=PT1H?project=static-sites-257923)
- [Queue Processing](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fstatic-sites-257923%2Flogs%2Fjob-finder%22%0Aresource.labels.container_name%3D%22job-finder-staging%22%0AtextPayload%3D~%22Found%20.%2B%20pending%20items%22;timeRange=PT1H?project=static-sites-257923)

> **Note:** If resource labels don't filter correctly, use these alternative queries:
> - Production: `logName="projects/static-sites-257923/logs/job-finder" AND textPayload=~"portfolio" AND NOT textPayload=~"staging"`
> - Staging: `logName="projects/static-sites-257923/logs/job-finder" AND textPayload=~"portfolio-staging"`

---

## Issue: Document Generation Requests Not Appearing in Job Queue

### Symptoms
- Document generation requests from job-finder-FE UI don't create queue items
- `job-queue` collection is missing or empty in production database
- No errors in job-finder-FE UI, but nothing happens

### Root Cause
**Database configuration mismatch** between job-finder-FE frontend and job-finder backend.

```
job-finder-FE Frontend → writes to ??? (wrong database)
                           ↓
                   (should be "portfolio")
                           ↓
job-finder backend ← reads from "portfolio" ✅
```

---

## Solution Overview

### 1. Initialize job-queue Collection

The collection doesn't exist because nothing has written to it yet. Run the setup script:

```bash
cd /path/to/job-finder

# Initialize the collection
python scripts/setup_production_queue.py

# Verify it worked
python scripts/diagnose_production_queue.py
```

This creates the collection structure that job-finder-FE frontend needs to write to.

### 2. Fix job-finder-FE Frontend Configuration

The job-finder-FE frontend must be configured to use the `portfolio` database in production.

#### Check job-finder-FE Project Configuration

In your job-finder-FE project, look for Firestore initialization:

**❌ WRONG (using staging database):**
```typescript
// job-finder-FE frontend code
const db = getFirestore(app, 'portfolio-staging')  // WRONG in production!
```

**✅ CORRECT (using production database):**
```typescript
// job-finder-FE frontend code
const db = getFirestore(app, 'portfolio')  // CORRECT for production
```

#### Environment-Based Configuration

Your job-finder-FE frontend should use environment variables:

```typescript
// job-finder-FE frontend - recommended approach
const dbName = process.env.NODE_ENV === 'production'
  ? 'portfolio'           // Production database
  : 'portfolio-staging'   // Development/staging database

const db = getFirestore(app, dbName)
```

### 3. Verify Firestore Security Rules

In your job-finder-FE project's `firestore.rules`, ensure `job-queue` collection allows writes:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Job Queue - Allow authenticated users to create queue items
    match /job-queue/{itemId} {
      allow create: if request.auth != null;  // Users can create queue items
      allow read: if request.auth != null;    // Users can read their items
      allow update: if false;                 // Only backend can update
      allow delete: if false;                 // Only backend can delete
    }

    // ... other rules
  }
}
```

**Deploy security rules:**
```bash
cd /path/to/portfolio-project
firebase deploy --only firestore:rules
```

---

## Verification Steps

### Step 1: Verify Collection Exists

```bash
python scripts/diagnose_production_queue.py
```

**Expected output:**
```
✅ Connected to database: portfolio
✅ job-queue collection exists and has items
```

### Step 2: Test from job-finder-FE UI

1. Open job-finder-FE in production
2. Navigate to a job match
3. Click "Generate Document" (or similar action)
4. Check browser console for errors

### Step 3: Check Queue Items Were Created

```bash
python scripts/diagnose_production_queue.py
```

**Expected output:**
```
✅ Found X recent queue items:
  - 2025-10-17 14:30:00: document_generation (pending) - ...
```

### Step 4: Monitor Queue Worker Logs

```bash
# On your production server
docker logs job-finder-production -f --tail 50
```

Look for:
```
[Iteration X] Found 1 pending items
Processing item: document_generation
```

---

## Common Issues

### Issue 1: Collection exists but no items created

**Symptom:** Collection exists but stays empty when you trigger actions.

**Cause:** job-finder-FE frontend is still writing to wrong database.

**Solution:**
1. Double-check job-finder-FE frontend database configuration
2. Clear browser cache and reload job-finder-FE UI
3. Check browser console for errors

### Issue 2: Security rules blocking writes

**Symptom:** Browser console shows Firestore permission errors.

**Cause:** Security rules don't allow authenticated users to write to `job-queue`.

**Solution:**
1. Update `firestore.rules` to allow `create` on `job-queue` collection
2. Deploy rules: `firebase deploy --only firestore:rules`
3. Retry from job-finder-FE UI

### Issue 3: Items created but not processed

**Symptom:** Queue items created successfully but status stays "pending" forever.

**Cause:** Queue worker not running or configured incorrectly.

**Solution:**
```bash
# Check if queue worker is running
docker ps | grep job-finder-production

# Check worker logs
docker logs job-finder-production -f

# Restart worker if needed
docker restart job-finder-production
```

---

## Database Configuration Reference

### Job Finder Backend (this project)

**File:** `docker-compose.production.yml`
```yaml
environment:
  - STORAGE_DATABASE_NAME=portfolio  # Production database
```

**File:** `config/config.production.yaml`
```yaml
storage:
  database_name: "portfolio"  # Production database
```

### job-finder-FE Frontend (separate project)

**Required configuration:**
```typescript
// Use environment-based database selection
const dbName = process.env.NODE_ENV === 'production'
  ? 'portfolio'           // ← MUST match backend
  : 'portfolio-staging'

const db = getFirestore(app, dbName)
```

---

## Testing Checklist

- [ ] Run `setup_production_queue.py` to initialize collection
- [ ] Run `diagnose_production_queue.py` - collection exists
- [ ] Verify job-finder-FE frontend uses `portfolio` database in production
- [ ] Deploy Firestore security rules with `job-queue` write permissions
- [ ] Test document generation from job-finder-FE UI
- [ ] Run `diagnose_production_queue.py` - queue items appear
- [ ] Check queue worker logs - items being processed
- [ ] Verify documents are generated successfully

---

## Support

If issues persist after following this guide:

1. **Check logs:**
   ```bash
   # job-finder-FE frontend (browser console)
   # Job finder backend
   docker logs job-finder-production --tail 100
   ```

2. **Verify environment:**
   ```bash
   # Check database configuration
   docker exec job-finder-production env | grep DATABASE
   ```

3. **Manual queue item test:**
   ```bash
   # Create test item from backend
   python scripts/setup_production_queue.py --no-cleanup

   # Verify it appears
   python scripts/diagnose_production_queue.py
   ```

4. **Compare databases:**
   - Does `portfolio-staging` have a `job-queue` collection?
   - If yes, that confirms job-finder-FE is writing to staging instead of production
