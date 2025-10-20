# Frontend Integration Guide

**Date:** 2025-10-16
**Queue Implementation:** Phase 1 Complete
**Target:** job-finder-FE frontend application integration

---

## Overview

This guide provides step-by-step instructions for integrating the job-finder queue system with the job-finder-FE frontend application. The queue enables asynchronous job processing, allowing users to submit jobs via the frontend UI for background analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    job-finder-FE Frontend                     │
│  - User submits job URL via form                         │
│  - API validates and writes to Firestore                 │
│  - UI polls for job status updates                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Firestore Database                          │
│  Collections:                                            │
│  - job-queue (pending items)                             │
│  - job-finder-config (stop lists, settings)              │
│  - job-matches (processed results)                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Job Finder Queue Worker                     │
│  - Polls every 60 seconds                                │
│  - Processes pending jobs                                │
│  - Updates status in real-time                           │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Firestore Setup

Before implementing the API routes, create the following Firestore collections and documents:

#### 1. Create `job-finder-config` Collection

Navigate to Firebase Console → Firestore Database → Create Collection

**Document: `stop-list`**
```json
{
  "excludedCompanies": [
    "Example Excluded Company"
  ],
  "excludedKeywords": [
    "commission only",
    "pay to play",
    "unpaid internship"
  ],
  "excludedDomains": [
    "spam-site.com",
    "scam-jobs.net"
  ]
}
```

**Document: `queue-settings`**
```json
{
  "maxRetries": 3,
  "retryDelaySeconds": 60,
  "processingTimeout": 300
}
```

**Document: `ai-settings`**
```json
{
  "provider": "claude",
  "model": "claude-3-haiku-20240307",
  "minMatchScore": 70,
  "costBudgetDaily": 50.0
}
```

---

## Implementation Steps

### Step 1: Create API Route for Job Submission

**File:** `app/api/jobs/submit/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/firebase-admin';
import { FieldValue } from 'firebase-admin/firestore';

interface JobSubmissionRequest {
  url: string;
  companyName?: string;
}

interface StopList {
  excludedCompanies: string[];
  excludedKeywords: string[];
  excludedDomains: string[];
}

export async function POST(request: NextRequest) {
  try {
    // 1. Authenticate user
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // 2. Parse and validate request
    const body: JobSubmissionRequest = await request.json();
    const { url, companyName } = body;

    if (!url || typeof url !== 'string') {
      return NextResponse.json(
        { error: 'URL is required and must be a string' },
        { status: 400 }
      );
    }

    // Validate URL format
    try {
      new URL(url);
    } catch {
      return NextResponse.json(
        { error: 'Invalid URL format' },
        { status: 400 }
      );
    }

    // 3. Load stop list configuration
    const stopList = await loadStopList();

    // 4. Check stop list
    const stopListCheck = checkStopList(url, companyName, stopList);
    if (!stopListCheck.allowed) {
      return NextResponse.json({
        status: 'skipped',
        message: stopListCheck.reason
      });
    }

    // 5. Check for duplicates in queue
    const queueDuplicate = await checkQueueDuplicate(url);
    if (queueDuplicate) {
      return NextResponse.json({
        status: 'skipped',
        message: 'Job already in processing queue'
      });
    }

    // 6. Check if job already exists in job-matches
    const existingJob = await checkExistingJob(url);
    if (existingJob) {
      return NextResponse.json({
        status: 'skipped',
        message: 'Job already analyzed',
        jobId: existingJob.id
      });
    }

    // 7. Add to queue
    const queueItemRef = await db
      .collection('job-queue')
      .add({
        type: 'job',
        status: 'pending',
        url: url,
        company_name: companyName || '',
        company_id: null,
        source: 'user_submission',
        submitted_by: session.user.id,
        retry_count: 0,
        max_retries: 3,
        created_at: FieldValue.serverTimestamp(),
        updated_at: FieldValue.serverTimestamp()
      });

    return NextResponse.json({
      status: 'success',
      message: 'Job submitted for processing',
      queueItemId: queueItemRef.id
    });

  } catch (error) {
    console.error('Error submitting job:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Helper function to load stop list
async function loadStopList(): Promise<StopList> {
  try {
    const stopListDoc = await db
      .collection('job-finder-config')
      .doc('stop-list')
      .get();

    if (!stopListDoc.exists) {
      return {
        excludedCompanies: [],
        excludedKeywords: [],
        excludedDomains: []
      };
    }

    return stopListDoc.data() as StopList;
  } catch (error) {
    console.error('Error loading stop list:', error);
    return {
      excludedCompanies: [],
      excludedKeywords: [],
      excludedDomains: []
    };
  }
}

// Helper function to check stop list
function checkStopList(
  url: string,
  companyName: string | undefined,
  stopList: StopList
): { allowed: boolean; reason?: string } {
  const urlLower = url.toLowerCase();
  const companyLower = companyName?.toLowerCase() || '';

  // Check excluded companies
  for (const excluded of stopList.excludedCompanies) {
    if (companyLower.includes(excluded.toLowerCase())) {
      return {
        allowed: false,
        reason: `Company "${companyName}" is on the exclusion list`
      };
    }
  }

  // Check excluded domains
  for (const domain of stopList.excludedDomains) {
    if (urlLower.includes(domain.toLowerCase())) {
      return {
        allowed: false,
        reason: `Domain "${domain}" is on the exclusion list`
      };
    }
  }

  // Check excluded keywords in URL
  for (const keyword of stopList.excludedKeywords) {
    if (urlLower.includes(keyword.toLowerCase())) {
      return {
        allowed: false,
        reason: `URL contains excluded keyword: "${keyword}"`
      };
    }
  }

  return { allowed: true };
}

// Helper function to check for queue duplicates
async function checkQueueDuplicate(url: string): Promise<boolean> {
  try {
    const queueSnapshot = await db
      .collection('job-queue')
      .where('url', '==', url)
      .limit(1)
      .get();

    return !queueSnapshot.empty;
  } catch (error) {
    console.error('Error checking queue duplicates:', error);
    return false;
  }
}

// Helper function to check existing jobs
async function checkExistingJob(url: string): Promise<{ id: string } | null> {
  try {
    const jobSnapshot = await db
      .collection('job-matches')
      .where('url', '==', url)
      .limit(1)
      .get();

    if (jobSnapshot.empty) {
      return null;
    }

    return { id: jobSnapshot.docs[0].id };
  } catch (error) {
    console.error('Error checking existing jobs:', error);
    return null;
  }
}
```

---

### Step 2: Create API Route for Queue Status

**File:** `app/api/jobs/queue-status/[id]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/auth';
import { db } from '@/lib/firebase-admin';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Authenticate user
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const queueItemId = params.id;

    // Get queue item
    const queueItemDoc = await db
      .collection('job-queue')
      .doc(queueItemId)
      .get();

    if (!queueItemDoc.exists) {
      return NextResponse.json(
        { error: 'Queue item not found' },
        { status: 404 }
      );
    }

    const data = queueItemDoc.data();

    // Verify user owns this submission
    if (data?.submitted_by !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      );
    }

    return NextResponse.json({
      id: queueItemDoc.id,
      status: data.status,
      result_message: data.result_message,
      created_at: data.created_at,
      updated_at: data.updated_at,
      processed_at: data.processed_at,
      completed_at: data.completed_at,
      retry_count: data.retry_count
    });

  } catch (error) {
    console.error('Error fetching queue status:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

---

### Step 3: Create UI Component for Job Submission

**File:** `components/JobSubmissionForm.tsx`

```typescript
'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';

interface QueueStatus {
  id: string;
  status: 'pending' | 'processing' | 'success' | 'failed' | 'skipped';
  result_message?: string;
  created_at?: any;
  completed_at?: any;
}

export default function JobSubmissionForm() {
  const { data: session } = useSession();
  const [url, setUrl] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const submitJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setQueueStatus(null);

    try {
      const response = await fetch('/api/jobs/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, companyName }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to submit job');
      }

      if (data.status === 'success' && data.queueItemId) {
        // Start polling for status
        setQueueStatus({
          id: data.queueItemId,
          status: 'pending',
        });
        startPolling(data.queueItemId);
      } else if (data.status === 'skipped') {
        setError(data.message);
      }

      // Clear form on success
      if (data.status === 'success') {
        setUrl('');
        setCompanyName('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const startPolling = async (queueItemId: string) => {
    setPolling(true);
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/queue-status/${queueItemId}`);
        const data = await response.json();

        if (response.ok) {
          setQueueStatus(data);

          // Stop polling when processing is complete
          if (['success', 'failed', 'skipped'].includes(data.status)) {
            clearInterval(pollInterval);
            setPolling(false);
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 3000); // Poll every 3 seconds

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      setPolling(false);
    }, 5 * 60 * 1000);
  };

  if (!session) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800">Please sign in to submit jobs</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Submit Job for Analysis</h2>

      <form onSubmit={submitJob} className="space-y-4">
        <div>
          <label htmlFor="url" className="block text-sm font-medium mb-2">
            Job URL *
          </label>
          <input
            type="url"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/careers/job-posting"
            required
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            disabled={loading || polling}
          />
        </div>

        <div>
          <label htmlFor="companyName" className="block text-sm font-medium mb-2">
            Company Name (Optional)
          </label>
          <input
            type="text"
            id="companyName"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Acme Corp"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            disabled={loading || polling}
          />
        </div>

        <button
          type="submit"
          disabled={loading || polling}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Submitting...' : polling ? 'Processing...' : 'Submit Job'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {queueStatus && (
        <div className="mt-6 p-4 bg-gray-50 border rounded-lg">
          <h3 className="font-semibold mb-2">Processing Status</h3>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Status:</span>
              <StatusBadge status={queueStatus.status} />
            </div>
            {queueStatus.result_message && (
              <p className="text-sm text-gray-600">{queueStatus.result_message}</p>
            )}
            {polling && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span>Waiting for results...</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    skipped: 'bg-gray-100 text-gray-800',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status as keyof typeof colors] || colors.pending}`}>
      {status.toUpperCase()}
    </span>
  );
}
```

---

### Step 4: Add Job Submission Page

**File:** `app/jobs/submit/page.tsx`

```typescript
import JobSubmissionForm from '@/components/JobSubmissionForm';

export default function SubmitJobPage() {
  return (
    <div className="container mx-auto py-8">
      <JobSubmissionForm />
    </div>
  );
}
```

---

## Testing Your Implementation

### 1. Manual Test Flow

1. **Start the queue worker** (job-finder project):
   ```bash
   python scripts/workers/queue_worker.py
   ```

2. **Access the submission form** in job-finder-FE:
   - Navigate to `/jobs/submit`
   - Sign in if not already authenticated

3. **Submit a test job**:
   - URL: `https://boards.greenhouse.io/example/jobs/123456`
   - Company: `Test Company`
   - Click "Submit Job"

4. **Observe the flow**:
   - Form should show "Processing..." status
   - Queue worker logs should show job being processed
   - UI should update with final status (success/skipped/failed)
   - Check `job-matches` collection for results

### 2. Test Stop List Filtering

1. **Add test entry to stop list**:
   ```json
   {
     "excludedCompanies": ["BadCorp"],
     "excludedKeywords": ["scam"],
     "excludedDomains": ["spam.com"]
   }
   ```

2. **Test submissions**:
   - Submit job with company "BadCorp" → Should return "skipped"
   - Submit URL with "spam.com" → Should return "skipped"
   - Submit valid job → Should return "success"

### 3. Test Duplicate Detection

1. Submit the same job URL twice
2. Second submission should return "already in queue" or "already analyzed"

---

## Configuration Management

### Updating Stop List (Admin Interface)

**File:** `app/admin/config/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { db } from '@/lib/firebase';
import { doc, getDoc, updateDoc } from 'firebase/firestore';

export default function ConfigPage() {
  const [stopList, setStopList] = useState({
    excludedCompanies: [] as string[],
    excludedKeywords: [] as string[],
    excludedDomains: [] as string[]
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadStopList();
  }, []);

  const loadStopList = async () => {
    try {
      const docRef = doc(db, 'job-finder-config', 'stop-list');
      const docSnap = await getDoc(docRef);

      if (docSnap.exists()) {
        setStopList(docSnap.data() as any);
      }
    } catch (error) {
      console.error('Error loading stop list:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveStopList = async () => {
    setSaving(true);
    try {
      const docRef = doc(db, 'job-finder-config', 'stop-list');
      await updateDoc(docRef, stopList);
      alert('Stop list updated successfully!');
    } catch (error) {
      console.error('Error saving stop list:', error);
      alert('Failed to save stop list');
    } finally {
      setSaving(false);
    }
  };

  const addItem = (field: keyof typeof stopList, value: string) => {
    if (value.trim()) {
      setStopList({
        ...stopList,
        [field]: [...stopList[field], value.trim()]
      });
    }
  };

  const removeItem = (field: keyof typeof stopList, index: number) => {
    setStopList({
      ...stopList,
      [field]: stopList[field].filter((_, i) => i !== index)
    });
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Job Finder Configuration</h1>

      {/* Excluded Companies */}
      <ConfigSection
        title="Excluded Companies"
        items={stopList.excludedCompanies}
        onAdd={(value) => addItem('excludedCompanies', value)}
        onRemove={(index) => removeItem('excludedCompanies', index)}
      />

      {/* Excluded Keywords */}
      <ConfigSection
        title="Excluded Keywords"
        items={stopList.excludedKeywords}
        onAdd={(value) => addItem('excludedKeywords', value)}
        onRemove={(index) => removeItem('excludedKeywords', index)}
      />

      {/* Excluded Domains */}
      <ConfigSection
        title="Excluded Domains"
        items={stopList.excludedDomains}
        onAdd={(value) => addItem('excludedDomains', value)}
        onRemove={(index) => removeItem('excludedDomains', index)}
      />

      <button
        onClick={saveStopList}
        disabled={saving}
        className="mt-6 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
      >
        {saving ? 'Saving...' : 'Save Configuration'}
      </button>
    </div>
  );
}

function ConfigSection({
  title,
  items,
  onAdd,
  onRemove
}: {
  title: string;
  items: string[];
  onAdd: (value: string) => void;
  onRemove: (index: number) => void;
}) {
  const [newValue, setNewValue] = useState('');

  const handleAdd = () => {
    onAdd(newValue);
    setNewValue('');
  };

  return (
    <div className="mb-8 p-6 bg-white border rounded-lg">
      <h2 className="text-xl font-semibold mb-4">{title}</h2>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
          placeholder={`Add ${title.toLowerCase()}`}
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <button
          onClick={handleAdd}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
        >
          Add
        </button>
      </div>

      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span>{item}</span>
            <button
              onClick={() => onRemove(index)}
              className="text-red-600 hover:text-red-800"
            >
              Remove
            </button>
          </div>
        ))}
        {items.length === 0 && (
          <p className="text-gray-500 text-sm">No items added yet</p>
        )}
      </div>
    </div>
  );
}
```

---

## Security Considerations

### 1. Authentication
- Always verify `session.user.id` exists before processing
- Check `submitted_by` field matches session user when fetching status

### 2. Input Validation
- Validate URL format before submission
- Sanitize company names
- Limit input lengths to prevent abuse

### 3. Rate Limiting
Consider adding rate limiting to prevent abuse:

```typescript
// In your API route
const RATE_LIMIT = 10; // 10 submissions per hour
const RATE_WINDOW = 60 * 60 * 1000; // 1 hour

async function checkRateLimit(userId: string): Promise<boolean> {
  const cutoffTime = new Date(Date.now() - RATE_WINDOW);

  const recentSubmissions = await db
    .collection('job-queue')
    .where('submitted_by', '==', userId)
    .where('created_at', '>', cutoffTime)
    .count()
    .get();

  return recentSubmissions.data().count < RATE_LIMIT;
}
```

---

## Monitoring & Analytics

### Queue Statistics Dashboard

**File:** `app/admin/queue-stats/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { db } from '@/lib/firebase';
import { collection, query, where, getDocs, Timestamp } from 'firebase/firestore';

interface QueueStats {
  pending: number;
  processing: number;
  success: number;
  failed: number;
  skipped: number;
  total: number;
}

export default function QueueStatsPage() {
  const [stats, setStats] = useState<QueueStats>({
    pending: 0,
    processing: 0,
    success: 0,
    failed: 0,
    skipped: 0,
    total: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const queueRef = collection(db, 'job-queue');
      const snapshot = await getDocs(queueRef);

      const newStats: QueueStats = {
        pending: 0,
        processing: 0,
        success: 0,
        failed: 0,
        skipped: 0,
        total: snapshot.size
      };

      snapshot.forEach((doc) => {
        const data = doc.data();
        const status = data.status;
        if (status in newStats) {
          newStats[status as keyof QueueStats]++;
        }
      });

      setStats(newStats);
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading statistics...</div>;
  }

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Queue Statistics</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total" value={stats.total} color="bg-gray-100" />
        <StatCard label="Pending" value={stats.pending} color="bg-yellow-100" />
        <StatCard label="Processing" value={stats.processing} color="bg-blue-100" />
        <StatCard label="Success" value={stats.success} color="bg-green-100" />
        <StatCard label="Failed" value={stats.failed} color="bg-red-100" />
        <StatCard label="Skipped" value={stats.skipped} color="bg-gray-100" />
      </div>

      <button
        onClick={loadStats}
        className="mt-6 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
      >
        Refresh
      </button>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`p-6 rounded-lg ${color}`}>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}
```

---

## Troubleshooting

### Job Stuck in "Pending"
- Verify queue worker is running
- Check worker logs for errors
- Verify Firestore permissions

### Jobs Being Skipped
- Check stop list configuration
- Verify URL is not already in database
- Review result_message field for reason

### Authentication Errors
- Verify Firebase Admin SDK is properly initialized
- Check session management in Next.js
- Verify user ID is being passed correctly

---

## Next Steps

1. **Implement the API routes** (`/api/jobs/submit` and `/api/jobs/queue-status/[id]`)
2. **Create the UI component** (`JobSubmissionForm.tsx`)
3. **Set up Firestore documents** (stop-list, queue-settings, ai-settings)
4. **Test the integration** (manual submission → queue → results)
5. **Add monitoring** (queue stats dashboard)
6. **Optional: Add configuration UI** for managing stop lists

---

## Support

For questions or issues:
1. Check queue worker logs: `/app/logs/queue_worker.log`
2. Review Firestore documents in Firebase Console
3. Verify all environment variables are set correctly
4. Ensure both services (job-finder-FE + Queue Worker) are running

**Documentation Location:** `job-finder/QUEUE_IMPLEMENTATION_SUMMARY.md`
