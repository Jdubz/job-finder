# Firestore Indexes

## Important: Index Management

**Firestore indexes for shared collections are managed in the job-finder-FE project.**

This project shares the following Firestore collections with the job-finder-FE web application:
- `job-queue`
- `job-matches`
- `job-sources`
- `generator` (for resume generation history)

### Single Source of Truth

All Firestore indexes are defined and deployed from:
```
../portfolio/firestore.indexes.json
```

**Why job-finder-FE?**
- job-finder-FE is the primary web application that users interact with
- Firebase Functions are deployed from job-finder-FE
- Easier to manage frontend + backend + indexes in one place
- Job-finder is a background worker that adapts to the shared schema

### Query Requirements

This application requires the following indexes for optimal performance:

#### job-queue Collection
```
status (ASC) + created_at (ASC)
```
Used by: `QueueManager.get_pending_jobs()` to poll for pending jobs

```
status (ASC) + completed_at (ASC)
```
Used by: `QueueManager.cleanup_old_jobs()` to remove completed jobs

#### job-matches Collection
```
userId (ASC) + matchScore (DESC)
```
Used by: `FirestoreStorage.get_job_matches()` to retrieve user's matches

```
userId (ASC) + status (ASC) + matchScore (DESC)
```
Used by: `FirestoreStorage.get_job_matches()` with status filter

### Adding New Indexes

If you add a query that requires a new index:

1. **Test locally:** Run the query and check Firebase Console for "missing index" errors
2. **Update job-finder-FE:** Add the index to `../portfolio/firestore.indexes.json`
3. **Deploy:** Indexes are deployed automatically when job-finder-FE is deployed
4. **Document:** Update this file with the new index requirement

### Verifying Indexes

Check deployed indexes in Firebase Console:
```
https://console.firebase.google.com/project/static-sites-257923/firestore/indexes
```

Or use Firebase CLI:
```bash
firebase firestore:indexes
```

### Archived Index File

The previous `firestore.indexes.json` in this project has been archived.
See `firestore.indexes.ARCHIVED.json` for reference.

### Related Documentation

- job-finder-FE Index Analysis: `../portfolio/docs/FIRESTORE_INDEX_ANALYSIS.md`
- Shared Types: `../shared-types/CONTEXT.md`
