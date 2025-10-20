# job-finder-FE Frontend Configuration for Production Queue

## Required Configuration

To fix the queue submission issue, update your job-finder-FE project with this configuration.

---

## 1. Firestore Database Selection

### Current Issue ❌

Your job-finder-FE frontend is likely using a hardcoded database name:

```typescript
// ❌ WRONG - hardcoded staging database
const db = getFirestore(app, 'portfolio-staging')
```

### Solution ✅

Use environment-based database selection:

```typescript
// ✅ CORRECT - environment-based database selection
import { getFirestore } from 'firebase/firestore'
import { app } from './firebase-config' // your Firebase app instance

// Select database based on environment
const getDatabaseName = (): string => {
  // If you have a specific environment variable
  if (process.env.NEXT_PUBLIC_FIREBASE_DATABASE) {
    return process.env.NEXT_PUBLIC_FIREBASE_DATABASE
  }

  // Otherwise use NODE_ENV
  return process.env.NODE_ENV === 'production'
    ? 'portfolio'           // Production database
    : 'portfolio-staging'   // Development/staging database
}

export const db = getFirestore(app, getDatabaseName())
```

---

## 2. Environment Variables

### Next.js Configuration

**File:** `.env.production`
```bash
NEXT_PUBLIC_FIREBASE_DATABASE=portfolio
```

**File:** `.env.development`
```bash
NEXT_PUBLIC_FIREBASE_DATABASE=portfolio-staging
```

**File:** `.env.local` (for local development)
```bash
NEXT_PUBLIC_FIREBASE_DATABASE=portfolio-staging
```

---

## 3. Queue Item Submission Code

### Verify Your Queue Submission

When submitting queue items, ensure you're using the configured `db` instance:

```typescript
import { collection, addDoc, Timestamp } from 'firebase/firestore'
import { db } from '@/lib/firebase' // Import the correctly configured db

export async function submitDocumentGenerationRequest(
  jobMatchId: string,
  documentType: string
) {
  try {
    // Create queue item
    const queueItem = {
      type: 'document_generation',
      job_match_id: jobMatchId,
      document_type: documentType,
      status: 'pending',
      created_at: Timestamp.now(),
      submitted_by: auth.currentUser?.uid,
    }

    // Add to job-queue collection
    // This will use the db configured above (portfolio or portfolio-staging)
    const docRef = await addDoc(collection(db, 'job-queue'), queueItem)

    console.log('Queue item created:', docRef.id)
    return docRef.id

  } catch (error) {
    console.error('Error creating queue item:', error)
    throw error
  }
}
```

---

## 4. Firestore Security Rules

### Update job-finder-FE's `firestore.rules`

Ensure authenticated users can create queue items:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Job Queue Collection
    match /job-queue/{itemId} {
      // Allow authenticated users to create queue items
      allow create: if request.auth != null
                    && request.resource.data.submitted_by == request.auth.uid;

      // Allow users to read their own queue items
      allow read: if request.auth != null
                  && resource.data.submitted_by == request.auth.uid;

      // Only backend can update/delete
      allow update, delete: if false;
    }

    // ... your other rules ...
  }
}
```

**Deploy the rules:**
```bash
cd /path/to/portfolio-project
firebase deploy --only firestore:rules
```

---

## 5. Verification

### Check Database Configuration in Browser Console

Add this to your job-finder-FE app for debugging:

```typescript
// In your job-finder-FE app, add this temporary debug code
console.log('Firestore Database:', db._databaseId.database)

// Should log:
// Production: "portfolio"
// Development: "portfolio-staging"
```

### Test Queue Submission

1. Open job-finder-FE in production
2. Open browser console (F12)
3. Trigger document generation
4. Look for console logs:
   ```
   Firestore Database: portfolio  ✅ (correct)
   Queue item created: abc123xyz
   ```

   **Not this:**
   ```
   Firestore Database: portfolio-staging  ❌ (wrong!)
   ```

---

## 6. Deployment Checklist

### Before Deploying to Production

- [ ] Update Firestore initialization to use environment-based database name
- [ ] Set `NEXT_PUBLIC_FIREBASE_DATABASE=portfolio` in production environment
- [ ] Update Firestore security rules to allow queue item creation
- [ ] Deploy security rules: `firebase deploy --only firestore:rules`

### After Deploying to Production

- [ ] Clear browser cache and reload job-finder-FE
- [ ] Check browser console - verify database name is "portfolio"
- [ ] Test document generation
- [ ] Verify queue item appears in Firestore console
- [ ] Run job-finder diagnostic: `python scripts/diagnose_production_queue.py`

---

## 7. Debugging Tips

### Check Which Database job-finder-FE is Using

```typescript
// Add this to your job-finder-FE app temporarily
import { db } from '@/lib/firebase'

console.log('Using Firestore database:', db._databaseId.database)
console.log('Environment:', process.env.NODE_ENV)
console.log('Database env var:', process.env.NEXT_PUBLIC_FIREBASE_DATABASE)
```

### Verify Queue Item Creation

```typescript
// Add error handling and logging
async function createQueueItem(data: any) {
  console.log('Creating queue item in database:', db._databaseId.database)

  try {
    const docRef = await addDoc(collection(db, 'job-queue'), data)
    console.log('✅ Queue item created:', docRef.id)
    console.log('   Database:', db._databaseId.database)
    return docRef.id
  } catch (error) {
    console.error('❌ Error creating queue item:', error)
    console.error('   Database:', db._databaseId.database)
    throw error
  }
}
```

### Check Firestore Console

1. Go to Firebase Console → Firestore Database
2. Switch to `portfolio` database (top dropdown)
3. Look for `job-queue` collection
4. Trigger document generation from job-finder-FE UI
5. Refresh Firestore console - new item should appear

---

## Common Mistakes

### ❌ Mistake 1: Hardcoded database name
```typescript
const db = getFirestore(app, 'portfolio-staging')  // Always staging!
```

### ✅ Fix: Environment-based selection
```typescript
const dbName = process.env.NODE_ENV === 'production' ? 'portfolio' : 'portfolio-staging'
const db = getFirestore(app, dbName)
```

---

### ❌ Mistake 2: Wrong environment variable prefix
```typescript
// In Next.js, client-side env vars need NEXT_PUBLIC_ prefix
process.env.FIREBASE_DATABASE  // ❌ Won't work in browser
```

### ✅ Fix: Use NEXT_PUBLIC_ prefix
```typescript
process.env.NEXT_PUBLIC_FIREBASE_DATABASE  // ✅ Works in browser
```

---

### ❌ Mistake 3: Not deploying security rules
```bash
# Just updating firestore.rules file isn't enough
# You must deploy them:
```

### ✅ Fix: Deploy rules
```bash
firebase deploy --only firestore:rules
```

---

## Summary

The fix requires **three changes in your job-finder-FE project**:

1. **Update Firestore initialization** - use environment-based database selection
2. **Set environment variables** - `NEXT_PUBLIC_FIREBASE_DATABASE=portfolio` for production
3. **Update and deploy security rules** - allow authenticated users to create queue items

After these changes, queue items will be created in the correct database and processed by job-finder.
