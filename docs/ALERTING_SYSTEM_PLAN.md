# Job Alerting System - Implementation Plan

**Status:** Planning Phase
**Created:** 2025-01-15
**Target Completion:** 10 days (2 weeks)

## Overview

A real-time alerting system that runs hourly to detect perfect job matches using strict pre-AI filters and high AI matching thresholds. Alerts are delivered via mobile push notifications through the portfolio webhook system, with email fallback.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hourly Alert Service                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Strict       │→ │ AI Matcher   │→ │ Alert        │     │
│  │ Pre-Filter   │  │ (High Thresh)│  │ Dispatcher   │     │
│  └──────────────┘  └──────────────┘  └──────┬───────┘     │
└────────────────────────────────────────────────┼───────────┘
                                                 │
                    ┌────────────────────────────┼───────────┐
                    │                            ▼           │
                    │        ┌─────────────────────────┐    │
                    │        │   job-finder-FE Webhook     │    │
                    │        │  /api/notifications     │    │
                    │        └──────────┬──────────────┘    │
                    │                   │                    │
                    │     ┌─────────────┼──────────────┐    │
                    │     ▼             ▼              ▼    │
                    │  Firebase   Push Notif    Email      │
                    │  Storage    (Mobile)      (Fallback) │
                    └────────────────────────────────────────┘
```

## Components to Build

### 1. Alert Service Core

**File:** `src/job_finder/alert_service.py`

```python
class JobAlertService:
    """Hourly job alerting with strict filters and high AI threshold."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_threshold = config.get('alerts', {}).get('min_score', 90)
        self.webhook_url = config.get('alerts', {}).get('webhook_url')
        self.alert_state = AlertStateManager(config)
        self.webhook_client = AlertWebhookClient(config)

    def run_hourly_check(self) -> Dict[str, Any]:
        """Main entry point for hourly cron job."""
        logger.info("Starting hourly job alert check...")

        # 1. Load profile
        profile = self._load_profile()

        # 2. Get new jobs from last hour (or configurable window)
        jobs = self._get_recent_jobs(hours=1)

        # 3. Apply strict pre-filters
        filtered_jobs = self._apply_strict_filters(jobs)
        logger.info(f"Strict filters: {len(jobs)} → {len(filtered_jobs)} jobs")

        # 4. Run AI matching with high threshold
        perfect_matches = self._find_perfect_matches(filtered_jobs)

        # 5. Remove duplicates (already alerted)
        new_matches = self._deduplicate_matches(perfect_matches)

        # 6. Send alerts for each perfect match
        alerts_sent = self._send_alerts(new_matches)

        # 7. Update alert state
        self._update_alert_state(new_matches)

        return {
            "jobs_checked": len(jobs),
            "after_filters": len(filtered_jobs),
            "perfect_matches": len(perfect_matches),
            "alerts_sent": alerts_sent,
        }

    def _apply_strict_filters(self, jobs: List[Dict]) -> List[Dict]:
        """Apply strict filtering criteria for alerts."""
        strict_filter = StrictAlertFilter(self.config)
        return strict_filter.filter_for_alerts(jobs)

    def _find_perfect_matches(self, jobs: List[Dict]) -> List[JobMatch]:
        """Run AI analysis with high threshold."""
        perfect_matches = []

        for job in jobs:
            result = self.ai_matcher.analyze_job(job)

            if self._is_perfect_match(job, result):
                perfect_matches.append({
                    "job": job,
                    "match_result": result,
                })

        return perfect_matches

    def _is_perfect_match(self, job: Dict, result: Any) -> bool:
        """Determine if job meets perfect match criteria."""
        return (
            result.match_score >= self.alert_threshold and
            result.application_priority == "High" and
            self._is_top_tier_company(job) and
            self._is_recent(job, hours=24)
        )
```

### 2. Strict Alert Filters

**File:** `src/job_finder/filters/alert_filters.py`

```python
class StrictAlertFilter:
    """Enhanced filtering for alert service - much stricter than normal search."""

    REQUIRED_SENIORITY = ["senior", "staff", "principal", "lead"]
    BLOCKED_ROLES = ["manager", "director", "vp", "product manager", "recruiter"]
    TIER_REQUIREMENT = ["S", "A"]  # Only top-tier companies
    MAX_AGE_HOURS = 24
    MIN_CORE_SKILLS = 3

    def filter_for_alerts(self, jobs: List[Dict]) -> List[Dict]:
        """Apply all strict filters."""
        filtered = jobs

        # 1. Seniority requirement
        filtered = self._filter_seniority(filtered)

        # 2. Role type (no management/non-engineering)
        filtered = self._filter_role_type(filtered)

        # 3. Company tier (S/A only)
        filtered = self._filter_company_tier(filtered)

        # 4. Job age (24 hours max)
        filtered = self._filter_age(filtered)

        # 5. Core skill alignment (at least 3 matches)
        filtered = self._filter_skill_alignment(filtered)

        # 6. Location (remote or Portland)
        filtered = self._filter_location(filtered)

        return filtered

    def _filter_seniority(self, jobs: List[Dict]) -> List[Dict]:
        """Only senior+ positions."""
        return [
            job for job in jobs
            if any(level in job.get("title", "").lower()
                   for level in self.REQUIRED_SENIORITY)
        ]

    def _filter_company_tier(self, jobs: List[Dict]) -> List[Dict]:
        """Only Tier S or A companies."""
        return [
            job for job in jobs
            if job.get("company_tier") in self.TIER_REQUIREMENT
        ]

    def _filter_skill_alignment(self, jobs: List[Dict]) -> List[Dict]:
        """Require at least 3 core skill mentions."""
        core_skills = self.config.get("alerts", {}).get("core_skills", [])

        return [
            job for job in jobs
            if self._count_skill_matches(job, core_skills) >= self.MIN_CORE_SKILLS
        ]
```

### 3. Webhook Client

**File:** `src/job_finder/alerts/webhook_client.py`

```python
import hmac
import hashlib
import requests
from typing import Dict, Any

class AlertWebhookClient:
    """Sends alerts to portfolio webhook with retry logic."""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('alerts', {}).get('webhook', {}).get('url')
        self.secret_key = os.getenv('WEBHOOK_SECRET_KEY')
        self.timeout = config.get('alerts', {}).get('webhook', {}).get('timeout', 10)
        self.max_retries = config.get('alerts', {}).get('webhook', {}).get('retry_attempts', 3)

    def send_alert(self, job_match: Dict[str, Any]) -> bool:
        """Send alert to portfolio webhook."""
        payload = self._build_payload(job_match)
        signature = self._sign_payload(payload)

        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Alert-Type': 'perfect_job_match',
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    logger.info(f"Alert sent successfully for job: {job_match['job']['title']}")
                    return True
                else:
                    logger.warning(f"Webhook returned {response.status_code}, attempt {attempt+1}/{self.max_retries}")

            except requests.RequestException as e:
                logger.error(f"Webhook request failed (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        # All retries failed, try email fallback
        logger.error(f"Webhook failed after {self.max_retries} attempts, falling back to email")
        return self._send_email_fallback(job_match)

    def _build_payload(self, job_match: Dict) -> Dict:
        """Build webhook payload."""
        return {
            "alert_type": "perfect_job_match",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job": {
                "id": job_match['job'].get('id'),
                "title": job_match['job'].get('title'),
                "company": job_match['job'].get('company'),
                "company_tier": job_match['job'].get('company_tier'),
                "location": job_match['job'].get('location'),
                "url": job_match['job'].get('url'),
                "posted_date": job_match['job'].get('posted_date'),
                "salary": job_match['job'].get('salary'),
                "keywords": job_match['job'].get('keywords', []),
            },
            "match_analysis": {
                "score": job_match['match_result'].match_score,
                "priority": job_match['match_result'].application_priority,
                "matched_skills": job_match['match_result'].matched_skills,
                "skill_gaps": job_match['match_result'].skill_gaps,
                "why_perfect": self._generate_reason(job_match),
            }
        }

    def _sign_payload(self, payload: Dict) -> str:
        """Generate HMAC signature for webhook verification."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            self.secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    def _send_email_fallback(self, job_match: Dict) -> bool:
        """Fallback to email if webhook fails."""
        # Import email client
        # Send formatted email with job details
        pass
```

### 4. Alert State Management

**File:** `src/job_finder/storage/alert_state.py`

```python
class AlertStateManager:
    """Tracks which jobs have triggered alerts to prevent duplicates."""

    def __init__(self, config: Dict[str, Any]):
        self.db = FirestoreClient(database_name=config.get('storage', {}).get('database_name'))
        self.collection = "alert_history"
        self.ttl_days = config.get('alerts', {}).get('deduplication', {}).get('ttl_days', 7)

    def has_alerted(self, job_url: str) -> bool:
        """Check if we've already alerted for this job."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.ttl_days)

        query = (
            self.db.collection(self.collection)
            .where("job_url", "==", job_url)
            .where("alerted_at", ">=", cutoff_date)
            .limit(1)
        )

        docs = list(query.stream())
        return len(docs) > 0

    def mark_alerted(self, job_url: str, alert_data: Dict[str, Any]) -> str:
        """Record that we've alerted for this job."""
        doc_data = {
            "job_url": job_url,
            "job_title": alert_data.get("title"),
            "company": alert_data.get("company"),
            "match_score": alert_data.get("score"),
            "alerted_at": datetime.now(timezone.utc),
            "alert_method": alert_data.get("method", "webhook"),
            "success": alert_data.get("success", True),
        }

        doc_ref = self.db.collection(self.collection).add(doc_data)
        return doc_ref[1].id
```

### 5. Configuration

**File:** `config/config.alerts.yaml`

```yaml
alerts:
  enabled: true
  schedule: "0 * * * *"  # Every hour

  # Webhook configuration
  webhook:
    url: "${PORTFOLIO_WEBHOOK_URL}"  # https://jdubz.io/api/notifications/job-alert
    secret_key: "${WEBHOOK_SECRET_KEY}"
    timeout: 10
    retry_attempts: 3

  # Alert criteria (stricter than normal search)
  filters:
    min_score: 90  # vs 80 for normal
    required_priority: "High"
    company_tiers: ["S", "A"]
    max_job_age_hours: 24
    min_core_skills: 3
    core_skills:
      - "Python"
      - "FastAPI"
      - "PostgreSQL"
      - "Docker"
      - "AWS"
      - "React"
      - "TypeScript"

  # Deduplication settings
  deduplication:
    ttl_days: 7  # Don't re-alert for same job within 7 days

  # Email fallback
  fallback_email:
    enabled: true
    recipients: ["your-email@example.com"]
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "${EMAIL_USER}"
    smtp_password: "${EMAIL_PASSWORD}"
```

### 6. Entry Point

**File:** `src/job_finder/run_alerts.py`

```python
#!/usr/bin/env python3
"""Run hourly job alerts."""

import sys
import yaml
from job_finder.alert_service import JobAlertService
from job_finder.logging_config import setup_logging

def main():
    """Run alert service."""
    setup_logging()

    # Load configuration
    with open("config/config.alerts.yaml") as f:
        config = yaml.safe_load(f)

    if not config.get('alerts', {}).get('enabled', False):
        logger.info("Alerts disabled in config, exiting")
        return 0

    # Run alert check
    alert_service = JobAlertService(config)
    stats = alert_service.run_hourly_check()

    logger.info(f"Alert check complete: {stats}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## job-finder-FE Integration

### API Endpoint

**File:** `portfolio/app/api/notifications/job-alert/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getMessaging } from 'firebase-admin/messaging';
import { validateWebhookSignature } from '@/lib/webhook-utils';
import { storeNotification } from '@/lib/firestore';

export async function POST(request: NextRequest) {
  try {
    // Validate webhook signature
    const payload = await request.json();
    const signature = request.headers.get('x-webhook-signature');

    if (!validateWebhookSignature(payload, signature)) {
      return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
    }

    // Store notification in Firestore
    await storeNotification({
      type: 'job_alert',
      job: payload.job,
      matchAnalysis: payload.match_analysis,
      timestamp: payload.timestamp,
      read: false,
    });

    // Send push notification
    await sendPushNotification({
      title: `🎯 Perfect Match: ${payload.job.title}`,
      body: `${payload.job.company} • Score: ${payload.match_analysis.score}/100`,
      data: {
        type: 'job_alert',
        jobId: payload.job.id,
        jobUrl: payload.job.url,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Job alert webhook error:', error);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

async function sendPushNotification(payload: any) {
  const messaging = getMessaging();

  // Get user's FCM token from Firestore
  const userDoc = await admin.firestore()
    .collection('users')
    .doc('jdubz')
    .get();

  const fcmToken = userDoc.data()?.fcmToken;

  if (!fcmToken) {
    console.warn('No FCM token found for user');
    return;
  }

  await messaging.send({
    token: fcmToken,
    notification: {
      title: payload.title,
      body: payload.body,
    },
    data: payload.data,
    apns: {
      payload: {
        aps: {
          sound: 'default',
          badge: 1,
        },
      },
    },
  });
}
```

## Deployment

### Docker Configuration

**File:** `docker-compose.alerts.yml`

```yaml
version: '3.8'

services:
  job-alerts:
    build: .
    command: python -m job_finder.run_alerts
    environment:
      - ALERT_MODE=true
      - WEBHOOK_SECRET_KEY=${WEBHOOK_SECRET_KEY}
      - PORTFOLIO_WEBHOOK_URL=${PORTFOLIO_WEBHOOK_URL}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/.firebase/credentials.json
      - STORAGE_DATABASE_NAME=portfolio-staging
      - PROFILE_DATABASE_NAME=portfolio
    volumes:
      - ./.firebase:/app/.firebase:ro
      - ./config:/app/config:ro
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
```

### Cron Schedule

**Option 1: Docker Cron**
```bash
# Run hourly at minute 0
0 * * * * docker-compose -f docker-compose.alerts.yml up job-alerts
```

**Option 2: GitHub Actions (Recommended)**
```yaml
# .github/workflows/hourly-alerts.yml
name: Hourly Job Alerts

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:  # Allow manual trigger

jobs:
  run-alerts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e .

      - name: Run alert service
        env:
          WEBHOOK_SECRET_KEY: ${{ secrets.WEBHOOK_SECRET_KEY }}
          PORTFOLIO_WEBHOOK_URL: ${{ secrets.PORTFOLIO_WEBHOOK_URL }}
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.FIREBASE_CREDENTIALS }}
        run: |
          echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > .firebase/credentials.json
          python -m job_finder.run_alerts
```

## Testing Strategy

### Unit Tests

**File:** `tests/test_alert_service.py`

```python
def test_perfect_match_detection():
    """Test that 90+ score with High priority is detected as perfect match."""

def test_strict_filtering():
    """Test that only senior roles from Tier S/A pass filters."""

def test_duplicate_suppression():
    """Test that same job doesn't trigger multiple alerts within TTL."""

def test_webhook_payload_structure():
    """Test webhook payload has all required fields."""

def test_webhook_signature():
    """Test HMAC signature generation and validation."""

def test_email_fallback():
    """Test email is sent when webhook fails."""
```

### Integration Tests

```python
def test_end_to_end_alert_flow():
    """Test complete flow from job detection to alert sent."""

def test_webhook_retry_logic():
    """Test webhook retries on failure with exponential backoff."""
```

## Implementation Timeline

### Week 1

**Day 1-2: Core Service**
- [ ] Create `alert_service.py` with main orchestration logic
- [ ] Implement `StrictAlertFilter` class
- [ ] Add configuration schema in `config.alerts.yaml`
- [ ] Write unit tests for filtering logic

**Day 3-4: Webhook Integration**
- [ ] Create `AlertWebhookClient` with retry logic
- [ ] Implement HMAC signature generation
- [ ] Add email fallback mechanism
- [ ] Write tests for webhook client

**Day 5: State Management**
- [ ] Implement `AlertStateManager` for deduplication
- [ ] Add Firestore collection for alert history
- [ ] Test deduplication logic

### Week 2

**Day 1-2: job-finder-FE API**
- [ ] Create `/api/notifications/job-alert` endpoint
- [ ] Set up Firebase Cloud Messaging
- [ ] Implement signature validation
- [ ] Add notification storage to Firestore

**Day 3: Mobile Integration**
- [ ] Register app for push notifications
- [ ] Store FCM token in user profile
- [ ] Handle notification taps (deep linking)
- [ ] Add notifications UI page

**Day 4: Testing & Refinement**
- [ ] End-to-end testing with staging webhook
- [ ] Test push notifications on iOS/Android
- [ ] Verify email fallback works
- [ ] Load testing with multiple alerts

**Day 5: Deployment & Monitoring**
- [ ] Deploy alert service to production
- [ ] Set up GitHub Actions cron job
- [ ] Configure monitoring and logging
- [ ] Document usage and troubleshooting

## Monitoring & Metrics

### Logs to Track
```
[INFO] Starting hourly alert check
[INFO] Loaded 150 jobs from last hour
[INFO] Strict filters: 150 → 12 jobs
[INFO] Found 3 perfect matches (scores: 92, 94, 91)
[INFO] Deduplication: 3 → 2 new matches
[INFO] Alert sent: Senior Backend Engineer at Stripe (score: 94)
[INFO] Alert sent: Staff Engineer at Airbnb (score: 92)
[INFO] Alert check complete: 2 alerts sent
```

### Metrics Dashboard
- Alerts sent per day/week/month
- Average match score of alerted jobs
- Webhook success rate
- Email fallback rate
- Alert-to-application conversion rate

## Future Enhancements

1. **Smart Scheduling**: Run more frequently during business hours (9am-5pm PST)
2. **ML Prediction**: Learn from application patterns to refine "perfect match" criteria
3. **Slack Integration**: Optional Slack channel for alerts
4. **SMS Alerts**: For Tier S companies with 95+ score
5. **Digest Mode**: Daily summary of good (but not perfect) matches (85-89 score)
6. **Alert Preferences**: Configure which companies/roles to prioritize
7. **Snooze Feature**: Temporarily disable alerts for specific companies/roles

## Next Session Checklist

- [ ] Review and approve this plan
- [ ] Create feature branch: `feature/job-alerts`
- [ ] Start with core alert service implementation
- [ ] Set up test Firestore collection for alert history
- [ ] Configure staging webhook URL in portfolio
