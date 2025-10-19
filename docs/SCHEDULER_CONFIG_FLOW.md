# Scheduler Configuration Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CRON SCHEDULER                               │
│                                                                       │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  docker/crontab                                              │  │
│   │  ┌────────────────────────────────────────────────────────┐ │  │
│   │  │  0 */6 * * * python scheduler.py                       │ │  │
│   │  │  (Triggers every 6 hours)                              │ │  │
│   │  └────────────────────────────────────────────────────────┘ │  │
│   └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              scripts/workers/hourly_scheduler.py                     │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Step 1: Load Firestore Config                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  ConfigLoader.get_scheduler_settings()                   │ │ │
│  │  │  ↓                                                        │ │ │
│  │  │  Firestore: job-finder-config/scheduler-settings        │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │                                                                │ │
│  │  Step 2: Check if Enabled                                     │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  if settings.enabled == false:                           │ │ │
│  │  │    🚫 Log: "Scheduler is DISABLED"                       │ │ │
│  │  │    EXIT                                                  │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │                                                                │ │
│  │  Step 3: Check Daytime Hours                                  │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  is_daytime_hours(settings):                             │ │ │
│  │  │    - Check current hour in settings.timezone            │ │ │
│  │  │    - Compare with daytime_hours.start/end               │ │ │
│  │  │    if outside hours:                                    │ │ │
│  │  │      ⏸️  Log: "Outside daytime hours"                    │ │ │
│  │  │      EXIT                                               │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │                                                                │ │
│  │  Step 4: Run Scraping                                          │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  Use settings from Firestore:                            │ │ │
│  │  │  - target_matches: How many jobs to find                │ │ │
│  │  │  - max_sources: How many job boards to check            │ │ │
│  │  │  - min_match_score: AI threshold                        │ │ │
│  │  │                                                          │ │ │
│  │  │  Scrape job boards until:                               │ │ │
│  │  │    - Found target_matches potential jobs, OR           │ │ │
│  │  │    - Scraped max_sources job boards                    │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Configuration Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                     Firestore Database                          │
│  (portfolio-staging or portfolio)                              │
│                                                                 │
│  Collection: job-finder-config                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Document: scheduler-settings                             │  │
│  │ ┌────────────────────────────────────────────────────┐   │  │
│  │ │ {                                                  │   │  │
│  │ │   enabled: true/false          ◄──────────────────┼───┼──┼── User Control
│  │ │   cron_schedule: "0 */6 * * *"                   │   │  │   (Firebase Console
│  │ │   daytime_hours: {start: 6, end: 22}            │   │  │    or API)
│  │ │   timezone: "America/Los_Angeles"               │   │  │
│  │ │   target_matches: 5                             │   │  │
│  │ │   max_sources: 10                               │   │  │
│  │ │   min_match_score: 80                           │   │  │
│  │ │ }                                                  │   │  │
│  │ └────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 │ ConfigLoader.get_scheduler_settings()
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│           src/job_finder/queue/config_loader.py                 │
│                                                                 │
│  class ConfigLoader:                                           │
│    def get_scheduler_settings() -> Dict:                       │
│      1. Check cache                                            │
│      2. Load from Firestore                                    │
│      3. Return settings (or defaults if not found)             │
│                                                                 │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 │ Returns settings dict
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│         scripts/workers/hourly_scheduler.py                     │
│                                                                 │
│  def run_hourly_scrape(config):                                │
│    scheduler_settings = config_loader.get_scheduler_settings() │
│                                                                 │
│    if not scheduler_settings["enabled"]:                       │
│      return {"status": "skipped", "reason": "disabled"}        │
│                                                                 │
│    # Use settings for scraping...                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Flow

```
                 START: Cron triggers
                         │
                         ▼
        ┌────────────────────────────────┐
        │   Load scheduler settings      │
        │   from Firestore              │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   enabled = true ?             │
        └─────┬──────────────────────┬───┘
              │ NO                   │ YES
              ▼                      ▼
    ┌──────────────────┐   ┌─────────────────────┐
    │ 🚫 Log: Disabled │   │ Check daytime hours  │
    │ EXIT             │   └──────┬──────────┬────┘
    └──────────────────┘          │ Outside  │ Inside
                                  │          │
                                  ▼          ▼
                       ┌──────────────┐  ┌───────────────┐
                       │ ⏸️  Skip run │  │ ✅ Run scrape │
                       │ EXIT        │  └───────┬───────┘
                       └──────────────┘          │
                                                 ▼
                                      ┌────────────────────┐
                                      │ Get next sources   │
                                      │ (max_sources limit)│
                                      └──────┬─────────────┘
                                             │
                                             ▼
                                      ┌────────────────────┐
                                      │ Scrape & analyze   │
                                      │ until:             │
                                      │ - target_matches   │
                                      │ - OR max_sources   │
                                      └──────┬─────────────┘
                                             │
                                             ▼
                                      ┌────────────────────┐
                                      │ Log statistics     │
                                      │ END                │
                                      └────────────────────┘
```

## User Control Points

```
┌──────────────────────────────────────────────────────────────────┐
│                 Firebase Console / API                            │
│                                                                   │
│  job-finder-config/scheduler-settings                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Field: enabled                                             │  │
│  │ ┌──────────┐  ┌──────────┐                                │  │
│  │ │  false   │  │   true   │  ◄── Toggle on/off            │  │
│  │ └──────────┘  └──────────┘                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Field: target_matches                                      │  │
│  │ ┌──────┐  ┌──────┐  ┌──────┐                              │  │
│  │ │  3   │  │  5   │  │  10  │  ◄── Adjust aggressiveness  │  │
│  │ └──────┘  └──────┘  └──────┘                              │  │
│  │   Less      Default   More                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Field: daytime_hours                                       │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ { start: 6, end: 22 }  ◄── Control active hours     │   │  │
│  │ │ { start: 8, end: 20 }      (6am-10pm or 8am-8pm)    │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│                    Changes take effect on next cron trigger      │
└──────────────────────────────────────────────────────────────────┘
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scheduler Settings                            │
│                  (scheduler-settings)                            │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Uses alongside
             │
    ┌────────┼────────┬──────────┬────────────┐
    │        │        │          │            │
    ▼        ▼        ▼          ▼            ▼
┌────────┐┌───────┐┌────────┐┌──────────┐┌─────────┐
│AI      ││Job    ││Tech    ││Queue     ││Stop     │
│Settings││Filters││Ranks   ││Settings  ││List     │
└────────┘└───────┘└────────┘└──────────┘└─────────┘
│         │         │          │           │
│         │         │          │           │
└─────────┴─────────┴──────────┴───────────┴─────────┐
                                                      │
          All stored in: job-finder-config/          │
          All loaded by: ConfigLoader                │
          All hot-reloadable: No redeployment needed │
                                                      │
└─────────────────────────────────────────────────────┘
```

## Legend

- ✅ = Action completed successfully
- 🚫 = Action blocked/disabled
- ⏸️  = Action paused/skipped
- ◄── = User control/input point
- ▼ = Flow direction
- ┌─┐ = Component/container boundary
