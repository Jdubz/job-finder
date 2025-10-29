# Sync Production Content Items Into Local Emulator

**Last Updated:** 2025-10-29  
**Owner:** Worker A (Backend)  
**Purpose:** Restore clean `content-items` data in the local Firestore emulator so worker pipelines and frontend smoke tests run against realistic records.

This runbook consolidates the old `SYNC_PRODUCTION_DATA.md` workflow and reflects the current repository layout after the documentation migration.

---

## Overview

- Source of truth lives in **production (`portfolio`) Firestore**.
- Destination is the **local Firestore emulator** running inside `job-finder-BE`.
- Preferred approach uses the scripted sync (`scripts/sync-content-from-production.js`).
- Manual export/import and `gcloud`-based workflows remain as fallbacks.

---

## Prerequisites

- `gcloud` CLI authenticated against `static-sites-257923`.
- Access to generate Firebase service account keys.
- Local env already has the Firestore emulator installed (`firebase-tools`).
- Repositories should be checked out as sibling directories under a common workspace folder (e.g., both `job-finder-BE` and `job-finder-worker` are siblings within the same workspace directory).

---

## Option A — Service Account Script (Recommended)

1. **Generate credentials**
   1. Open [Firebase Console → Service Accounts](https://console.firebase.google.com/project/static-sites-257923/settings/serviceaccounts).
   2. Click **Generate new private key** for the default App Engine service account.
   3. Save the JSON key as `job-finder-BE/service-account.json`.
   4. Confirm `job-finder-BE/.gitignore` already contains `service-account.json` (it should; add if missing).

2. **Run the sync**
   ```bash
   cd path/to/job-finder-BE   # Replace with the path to your local job-finder-BE repo, e.g. ../job-finder-BE
   FIRESTORE_EMULATOR_HOST=localhost:8080 node scripts/sync-content-from-production.js
   ```

3. **Script behaviour**
   - Reads `content-items` documents from production (`portfolio` database).
   - Streams them into the local emulator.
   - Prints progress summary including processed count and failures.

> Tip: If the emulator is already running, stop it first to avoid partial writes.

---

## Option B — Firebase Console Export/Import

1. **Export from UI**
   - Navigate to [Firestore Data](https://console.firebase.google.com/project/static-sites-257923/firestore/databases/portfolio/data).
   - Ensure database selection is **`portfolio`**.
   - Use **Import/Export → Export**.
   - Select collection **`content-items`**.
   - Export to the default Cloud Storage bucket.

2. **Download archive**
   - Open [Cloud Storage Browser](https://console.cloud.google.com/storage/browser?project=static-sites-257923).
   - Locate the timestamped export folder.
   - Download to `job-finder-BE/.firebase/production-content-export/`.

3. **Import into emulator**
   ```bash
   cd path/to/job-finder-BE   # Replace with the path to your local job-finder-BE repo, e.g. ../job-finder-BE
   pkill -f "firebase emulators:start" || true

   firebase emulators:start \
     --import=.firebase/production-content-export \
     --export-on-exit=.firebase/emulator-data
   ```

---

## Option C — `gcloud` Scripted Export

If you have the Cloud SDK installed:

```bash
cd path/to/job-finder-BE   # Replace with the path to your local job-finder-BE repo, e.g. ../job-finder-BE
./scripts/export-production-content.sh
```

Follow the prompts to download and import the dataset.

---

## Verification

1. Launch the emulator UI: http://localhost:4000/firestore  
2. Inspect the `content-items` collection.  
3. Confirm each doc includes expected fields:
   - `userId`, `type`, `order`, `visibility`
   - `createdAt`, `updatedAt`, `createdBy`, `updatedBy`
4. Run worker smoke scripts or App Monitor content views to verify data renders correctly.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `Permission denied` during export | `gcloud auth login` and `gcloud config set project static-sites-257923`. |
| Emulator says `database not found` | Ensure database ID is `portfolio` (production), not staging. |
| Script fails to load service account | Re-run Option A step 1; make sure JSON is in `job-finder-BE/` root. |
| Data still garbled after sync | Repeat export ensuring correct collection; clear emulator data (`rm -rf job-finder-BE/.firebase/emulator-data`) before import. |

---

## Clean-Up Checklist

- Remove downloaded service account JSON if not needed (`rm job-finder-BE/service-account.json`).
- Delete temporary export archives after import to avoid secrets lingering.
- Restart any local worker processes so they pick up refreshed emulator data.

---

## Change Log

- **2025-10-29:** Migrated runbook from legacy `SYNC_PRODUCTION_DATA.md` into worker operations directory and aligned instructions with current repo layout.
