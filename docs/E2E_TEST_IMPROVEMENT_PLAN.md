# E2E Test Suite Improvement Plan

**Date:** October 18, 2025  
**Status:** Planning Phase  
**Priority:** High

## Executive Summary

The E2E test suite has identified three critical issues:
1. **Deduplication failures** - Repeated scans creating duplicate job entries
2. **Rotation/prioritization bugs** - Sources not being rotated appropriately, some companies favored over others
3. **Hanging tests** - Tests timeout or hang indefinitely during processing

This document outlines root causes and implementation plan for fixes.

---

## Issue 1: Job Deduplication Failures

### Root Causes

#### 1a. Inefficient URL Lookup
**Location:** `src/job_finder/storage/firestore_storage.py:341` - `job_exists()`

```python
def job_exists(self, job_url: str, user_id: Optional[str] = None) -> bool:
    query = self.db.collection("job-matches").where("url", "==", job_url)
    # ... single lookup
```

**Problems:**
- Performs individual Firestore queries for each job (N+1 problem)
- No batch checking for performance at scale
- No URL normalization (trailing slashes, params, case sensitivity)
- No caching of recent lookups

**Impact:** 
- When scraping 50+ jobs, makes 50+ Firestore queries
- Slow performance: ~100-200ms per job
- Total time: 5-10 seconds just for dedup checks
- Easy to miss duplicates if URL formatting varies

#### 1b. URL Normalization Issues
**Location:** Multiple locations (queue/scraper_intake.py, scrape_runner.py)

**Problems:**
- URLs not normalized before comparison
- `https://example.com/job/123` vs `https://example.com/job/123/` treated as different
- Query parameters stripped inconsistently
- Case sensitivity issues: `jobs.example.com` vs `JOBS.EXAMPLE.COM`

#### 1c. Cross-Collection Deduplication
**Location:** `src/job_finder/queue/scraper_intake.py:70` - `submit_jobs()`

```python
# Only checks against job-matches collection
if self.job_storage.job_exists(url):
    logger.debug(f"Job already exists in job-matches: {url}")
    continue
```

**Problems:**
- Only checks `job-matches` collection
- Doesn't check if URL already in `job-queue` (could be processing)
- Doesn't check against company sources (URLs might be company website)

### Solutions

#### Solution 1a: Implement Batch Deduplication
```python
def batch_check_exists(self, job_urls: List[str]) -> Dict[str, bool]:
    """
    Check multiple URLs in single batched Firestore query.
    
    Uses composite query on url field for bulk lookup.
    Returns dict mapping URL -> exists (bool)
    """
    # Split into chunks of 10 (Firestore IN operator limit)
    # Use single query with IN operator instead of N queries
    # Result: ~10 queries for 100 URLs instead of 100
```

#### Solution 1b: Normalize URLs
```python
def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent comparison.
    
    - Remove trailing slashes
    - Lower case domain and path
    - Sort query parameters
    - Remove tracking parameters (utm_*, fbclid, etc)
    - Remove fragments
    """
```

#### Solution 1c: Add Caching Layer
```python
class DuplicationCache:
    """Cache recent dedup checks to avoid repeated queries."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}  # {normalized_url: exists_bool}
        self.ttl = ttl_seconds
        self.timestamps = {}
    
    def check(self, url: str) -> Optional[bool]:
        """Return cached result if within TTL, else None."""
```

#### Solution 1d: Add Checksum-Based Deduplication
```python
# Store URL hash in job-matches for faster lookups
job_match = {
    "url": job_url,
    "urlHash": hashlib.sha256(normalize_url(job_url).encode()).hexdigest(),
    "urlNormalized": normalize_url(job_url),
    ...
}

# Query on hash instead of full URL
query = db.collection("job-matches").where("urlHash", "==", url_hash)
```

---

## Issue 2: Source Rotation & Prioritization Failures

### Root Causes

#### 2a. Incomplete Scrape Timestamp Tracking
**Location:** `src/job_finder/scrape_runner.py:236` - `_scrape_source()`

**Problems:**
- `scraped_at` not being updated consistently
- `health.last_scraped_at` sometimes null
- No clear timestamp format (Firestore timestamp vs unix vs ISO)

#### 2b. Rotation Algorithm Issues
**Location:** `src/job_finder/scrape_runner.py:197` - `_get_next_sources_by_rotation()`

**Problems:**
- Uses `scraped_at` or `created_at` without validation
- Doesn't handle null/missing timestamps
- No tie-breaking mechanism (what if two sources have same `scraped_at`?)
- Doesn't consider source health/priority tier

#### 2c. No Company Fairness Mechanism
**Location:** Job rotation doesn't track company participation

**Problems:**
- Some popular companies (Netflix, Stripe) get scraped more frequently
- Less popular sources never get rotated in
- No priority scoring based on source tier (S/A/B/C/D)

#### 2d. Test Rotation Verification Issues
**Location:** `tests/e2e/scenarios/scenario_04_scrape_rotation.py:235` - `_identify_scraped_sources()`

**Problems:**
- Timestamp comparison unreliable if timestamps too close
- No transaction isolation (could miss concurrent updates)
- Test assumes sources changed but doesn't verify scraping actually happened
- Doesn't check jobs were actually created from scraping

### Solutions

#### Solution 2a: Implement Comprehensive Timestamp Tracking
```python
class SourceHealthTracker:
    """Track source health and scraping history."""
    
    def update_after_scrape(self, source_id: str, stats: Dict) -> None:
        """Update source after scraping completes."""
        health = {
            "lastScrapedAt": datetime.now(timezone.utc),
            "lastScrapeDuration": stats["duration"],
            "successCount": source.get("health", {}).get("successCount", 0) + 1,
            "failureCount": source.get("health", {}).get("failureCount", 0),
            "averageJobsPerScrape": calculate_average(...),
            "healthScore": calculate_health_score(...),
        }
```

#### Solution 2b: Improve Rotation Algorithm
```python
def _get_next_sources_by_rotation(self, limit: Optional[int]) -> List[Dict]:
    """
    Get sources in rotation order.
    
    Priority order:
    1. Source health score (failures reduce priority)
    2. Never scraped (created_at oldest)
    3. Oldest last_scraped_at
    4. Tier-based priority (S > A > B > C > D)
    5. Company fairness (less frequently scraped companies first)
    """
    
    active_sources = self.sources_manager.get_active_sources()
    
    # Score each source
    scored = []
    for source in active_sources:
        health = source.get("health", {})
        
        score = {
            "source": source,
            "health_score": health.get("healthScore", 1.0),  # 0-1
            "last_scraped": health.get("lastScrapedAt") or source.get("createdAt"),
            "tier_priority": {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}.get(source.get("tier", "D"), 4),
            "company_scrape_count": self._get_company_scrape_count(source.get("company_id")),
        }
        scored.append(score)
    
    # Sort by: health_score DESC, tier DESC, last_scraped ASC, company_count ASC
    sorted_sources = sorted(
        scored,
        key=lambda x: (
            -x["health_score"],           # Higher health first
            x["tier_priority"],            # Better tier first
            x["last_scraped"],             # Oldest first
            x["company_scrape_count"],     # Less scraped companies first
        )
    )
    
    return [s["source"] for s in sorted_sources[:limit]]
```

#### Solution 2c: Add Company Fairness Tracking
```python
class CompanyScrapeTracker:
    """Track scraping frequency by company."""
    
    def __init__(self, db: FirestoreClient, window_days: int = 30):
        self.db = db
        self.window = timedelta(days=window_days)
    
    def get_scrape_frequency(self, company_id: str) -> float:
        """Get scrapes/day for company in past N days."""
        cutoff = datetime.now(timezone.utc) - self.window
        
        query = self.db.collection("scrape-history").where(
            "company_id", "==", company_id
        ).where(
            "scraped_at", ">", cutoff
        )
        
        count = len(list(query.stream()))
        return count / self.window.days
```

#### Solution 2d: Improve Test Verification
```python
def _identify_scraped_sources(
    self, sources_before: List[Dict], sources_after: List[Dict]
) -> List[str]:
    """
    Identify which sources were scraped with verification.
    
    Checks:
    1. health.lastScrapedAt updated
    2. health.successCount increased
    3. Job count increased (jobs collection)
    4. Timestamp > scenario start time
    """
    scraped = []
    
    for source_id, before in sources_before.items():
        after = sources_after.get(source_id)
        if not after:
            continue
        
        # Multi-point verification
        before_scrape_time = (
            before.get("health", {}).get("lastScrapedAt") 
            or before.get("createdAt")
        )
        after_scrape_time = (
            after.get("health", {}).get("lastScrapedAt") 
            or after.get("createdAt")
        )
        
        # Check timestamp changed AND is after scenario started
        if (after_scrape_time > before_scrape_time and 
            after_scrape_time > self.scenario_start_time):
            
            # Verify success count increased
            success_before = before.get("health", {}).get("successCount", 0)
            success_after = after.get("health", {}).get("successCount", 0)
            
            if success_after > success_before:
                scraped.append(source_id)
    
    return scraped
```

---

## Issue 3: E2E Tests Hanging/Timeout

### Root Causes

#### 3a. Fixed Timeouts Without Backoff
**Location:** `tests/e2e/helpers/queue_monitor.py:17` - `QueueMonitor.__init__()`

```python
def __init__(self, db_client, collection: str = "job-queue", 
             poll_interval: float = 2.0, timeout: float = 300.0):
```

**Problems:**
- Fixed 300s timeout for all operations
- No consideration for slow staging environment
- No exponential backoff
- Portainer worker might be slow/restarting
- GCP Firestore might have latency spikes

**Impact:**
- Sometimes jobs take >5 minutes to process
- Test fails with "timeout" instead of "success"
- No visibility into why it's slow

#### 3b. No Health Checks Before Tests
**Location:** E2E test startup

**Problems:**
- Doesn't verify Portainer worker is running
- Doesn't verify Firestore connectivity
- Doesn't verify GCP credentials are valid
- Doesn't check Google Cloud logging access

#### 3c. Poor Error Diagnostics
**Location:** `tests/e2e/helpers/queue_monitor.py:83` - timeout error message

```python
raise TimeoutError(
    f"Timeout waiting for {doc_id} to reach '{expected_status}' "
    f"(waited {elapsed:.1f}s, last status: {current_status})"
)
```

**Problems:**
- Doesn't include intermediate status transitions
- No logs of what happened
- Doesn't show result_message or error field
- Can't debug what went wrong

#### 3d. Polling Issues
**Location:** Queue monitor polling loop

**Problems:**
- Fixed 2-second poll interval might be too slow for fast jobs
- Might be too fast for slow jobs (wasting Firestore reads)
- No adaptive polling
- No backoff when document not found

### Solutions

#### Solution 3a: Implement Adaptive Timeout with Backoff
```python
class AdaptiveQueueMonitor:
    """Monitor with adaptive timeout and exponential backoff."""
    
    def __init__(self, db_client, collection: str = "job-queue",
                 base_timeout: float = 60.0,  # per stage
                 max_timeout: float = 600.0,   # 10 min max
                 initial_poll_interval: float = 1.0):
        self.db = db_client
        self.collection = collection
        self.base_timeout = base_timeout
        self.max_timeout = max_timeout
        self.poll_interval = initial_poll_interval
    
    def wait_for_status(
        self, 
        doc_id: str, 
        expected_status: str,
        timeout: Optional[float] = None,
        adaptive: bool = True,
    ) -> Dict[str, Any]:
        """
        Wait for status with adaptive timeout.
        
        Adjusts timeout based on queue type:
        - JOB type: 5 min (includes scraping, AI analysis)
        - SCRAPE type: 10 min (multiple sources)
        - COMPANY type: 3 min (single company analysis)
        
        Uses exponential backoff: 1s -> 2s -> 4s -> 8s max 10s
        """
        
        # Auto-detect timeout based on queue item type
        if adaptive:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                item_type = doc.to_dict().get("type", "job")
                timeouts = {
                    "job": 300.0,      # 5 min
                    "scrape": 600.0,   # 10 min
                    "company": 180.0,  # 3 min
                }
                timeout = timeouts.get(item_type, self.base_timeout)
        
        timeout = min(timeout or self.base_timeout, self.max_timeout)
        
        start_time = time.time()
        end_time = start_time + timeout
        poll_interval = self.poll_interval
        attempt = 0
        
        while time.time() < end_time:
            try:
                doc_ref = self.db.collection(self.collection).document(doc_id)
                doc = doc_ref.get()
                
                if not doc.exists:
                    logger.warning(f"Document not found: {doc_id}")
                    # Backoff when doc not found
                    time.sleep(min(poll_interval, 10.0))
                    poll_interval *= 1.5
                    continue
                
                data = doc.to_dict()
                current_status = data.get("status")
                
                # Reset poll interval on success
                poll_interval = self.poll_interval
                
                if current_status == expected_status:
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Status '{expected_status}' after {elapsed:.1f}s")
                    return data
                
                if current_status in ["failed", "error", "rejected"]:
                    return data  # Return even if error
                
                # Adaptive polling: faster at start, slower over time
                attempt += 1
                if attempt < 3:
                    poll_interval = 1.0  # Fast initial checks
                elif attempt < 10:
                    poll_interval = 2.0
                else:
                    poll_interval = min(5.0, poll_interval * 1.1)
                
                logger.debug(
                    f"Status: {current_status} "
                    f"(elapsed: {time.time() - start_time:.1f}s, "
                    f"next poll in {poll_interval:.1f}s)"
                )
                
            except Exception as e:
                logger.warning(f"Error polling: {e}, backing off...")
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 2, 10.0)
                continue
            
            time.sleep(poll_interval)
        
        # Timeout - get detailed info
        elapsed = time.time() - start_time
        final_doc = self.db.collection(self.collection).document(doc_id).get()
        final_data = final_doc.to_dict() if final_doc.exists else {}
        
        raise TimeoutError(
            f"Timeout waiting for {doc_id} to reach '{expected_status}'\n"
            f"  Waited: {elapsed:.1f}s (max: {timeout}s)\n"
            f"  Last status: {final_data.get('status')}\n"
            f"  Message: {final_data.get('result_message', 'N/A')}\n"
            f"  Error: {final_data.get('error', 'N/A')}\n"
            f"  See Google Cloud Logging for details"
        )
```

#### Solution 3b: Add Pre-Test Health Checks
```python
class E2EHealthCheck:
    """Verify environment is ready for E2E tests."""
    
    def __init__(self, db_name: str = "portfolio-staging"):
        self.db_name = db_name
    
    def run_all_checks(self) -> Dict[str, bool]:
        """Run all health checks."""
        return {
            "firestore": self.check_firestore(),
            "gcp_credentials": self.check_gcp_credentials(),
            "google_cloud_logging": self.check_logging(),
            "portainer_worker": self.check_portainer(),
            "network": self.check_network(),
        }
    
    def check_firestore(self) -> bool:
        """Verify Firestore connectivity."""
        try:
            db = FirestoreClient.get_client(self.db_name)
            doc = db.collection("_health_check").document("ping").get()
            return True
        except Exception as e:
            logger.error(f"Firestore check failed: {e}")
            return False
    
    def check_portainer(self) -> bool:
        """Verify Portainer worker is running."""
        try:
            import requests
            # Check if worker process is active
            # Could check Portainer API or check for recent queue activity
            return True
        except Exception as e:
            logger.warning(f"Portainer check: {e}")
            return False
    
    def check_google_cloud_logging(self) -> bool:
        """Verify Google Cloud Logging access."""
        try:
            from google.cloud import logging as cloud_logging
            client = cloud_logging.Client()
            # Verify we can list logs
            return True
        except Exception as e:
            logger.error(f"Google Cloud Logging check failed: {e}")
            return False
```

#### Solution 3c: Add Verbose Status Tracking
```python
class StatusHistoryTracker:
    """Track status changes through processing."""
    
    def __init__(self, db_client, doc_id: str):
        self.db = db_client
        self.doc_id = doc_id
        self.history = []  # [(status, timestamp, message)]
    
    def get_status_history(self, collection: str) -> List[Dict]:
        """Get all status transitions for debugging."""
        doc = self.db.collection(collection).document(self.doc_id).get()
        if not doc.exists:
            return []
        
        data = doc.to_dict()
        
        # Reconstruct timeline from fields
        timeline = [
            {
                "stage": "created",
                "time": data.get("createdAt"),
                "status": "pending",
            },
        ]
        
        # Add pipeline stages if present
        for stage in ["fetch", "extract", "analyze", "save"]:
            key = f"{stage}StartedAt"
            if key in data and data[key]:
                timeline.append({
                    "stage": stage,
                    "time": data[key],
                    "status": stage,
                })
        
        if data.get("completedAt"):
            timeline.append({
                "stage": "completed",
                "time": data.get("completedAt"),
                "status": "completed",
            })
        
        return sorted(timeline, key=lambda x: x.get("time") or 0)
    
    def print_timeline(self, collection: str):
        """Pretty print status timeline."""
        history = self.get_status_history(collection)
        print(f"\nStatus Timeline for {self.doc_id}:")
        print("-" * 70)
        
        start = history[0]["time"] if history else None
        for item in history:
            elapsed = (
                (item["time"] - start).total_seconds() 
                if start and item["time"] else 0
            )
            print(f"  {elapsed:6.1f}s - {item['stage']:12} {item['status']}")
```

#### Solution 3d: Improve Error Reporting
```python
def diagnose_timeout(self, doc_id: str, collection: str) -> str:
    """Generate diagnostic report for timeout."""
    doc_ref = self.db.collection(collection).document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return f"Document {doc_id} not found in {collection}"
    
    data = doc.to_dict()
    
    report = f"""
TIMEOUT DIAGNOSTIC REPORT
{'='*70}

Document: {collection}/{doc_id}
Type: {data.get('type')}
Status: {data.get('status')}
Created: {data.get('createdAt')}

TIMELINE:
"""
    
    # Add timeline
    tracker = StatusHistoryTracker(self.db, doc_id)
    for item in tracker.get_status_history(collection):
        report += f"\n  {item['time']}: {item['status']}"
    
    # Add error details
    report += f"\n\nERROR DETAILS:\n"
    report += f"  Error: {data.get('error', 'N/A')}\n"
    report += f"  Message: {data.get('result_message', 'N/A')}\n"
    
    # Add logs link
    report += f"\n\nGOOGLE CLOUD LOGGING:\n"
    report += f"  Filter: jsonPayload.doc_id='{doc_id}'\n"
    report += f"  URL: https://console.cloud.google.com/logs\n"
    
    return report
```

---

## Implementation Timeline

### Phase 1: Deduplication (2-3 hours)
- [ ] Implement batch URL checking (batch_check_exists)
- [ ] Add URL normalization utility
- [ ] Update job_exists calls
- [ ] Add caching layer
- [ ] Test with test suite

### Phase 2: Rotation (3-4 hours)
- [ ] Implement SourceHealthTracker
- [ ] Improve rotation algorithm
- [ ] Add company fairness tracking
- [ ] Update test verification
- [ ] Validate rotation order in tests

### Phase 3: Timeout/Reliability (2-3 hours)
- [ ] Implement AdaptiveQueueMonitor
- [ ] Add E2E health checks
- [ ] Add status tracking
- [ ] Improve error reporting
- [ ] Update E2E test runner

### Phase 4: Testing & Validation (2 hours)
- [ ] Run full E2E test suite
- [ ] Monitor for regressions
- [ ] Create monitoring dashboard
- [ ] Document improvements

---

## Success Criteria

1. **Deduplication:**
   - ✓ No duplicate jobs from repeated scans
   - ✓ Job dedup checks complete in <1s for 50 jobs
   - ✓ URLs normalized consistently

2. **Rotation:**
   - ✓ All sources rotated fairly
   - ✓ Oldest sources prioritized
   - ✓ Company-level fairness enforced
   - ✓ Scenario 4 tests pass

3. **Reliability:**
   - ✓ Tests rarely timeout
   - ✓ Timeout errors include diagnostics
   - ✓ Pre-flight health checks prevent surprises
   - ✓ Exponential backoff prevents failures from transient issues

---

## Monitoring & Observability

### New Metrics to Track
- Dedup check time per job
- Dedup cache hit rate
- Source rotation fairness (% scrapes per company)
- E2E test timeout rate
- Average test duration by type
- Flake rate

### Google Cloud Logging
```
resource.type="gce_instance"
labels.test_run_id="e2e_test_*"
severity>=ERROR
```

### Dashboard (Future)
- Test results over time
- Dedup effectiveness
- Rotation distribution
- Timeout trends

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing dedup logic | Keep batch_check_exists alongside job_exists, test both |
| Slow URL normalization | Cache normalized URLs, profile performance |
| Rotation changes impact production | Test in staging first, gradual rollout |
| Test flakiness increases | Add comprehensive health checks, generous timeouts |

---

## Rollout Strategy

1. **Week 1:** Implement fixes in feature branches
2. **Week 2:** Full E2E testing in staging
3. **Week 3:** Merge to main with monitoring
4. **Week 4:** Monitor production, adjust as needed

---

## Next Steps

1. Create dedicated branch: `feature/e2e-improvements`
2. Start with deduplication (highest impact)
3. Run tests frequently to catch regressions
4. Document any new findings
5. Update this plan as we learn
