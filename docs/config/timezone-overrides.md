# Timezone Override Configuration

**Last Updated**: 2025-10-20
**Related**: BUG-2 — Timezone Detection for Global Companies

## Overview

The timezone override system prevents globally distributed companies from receiving timezone penalties when posting remote job opportunities. Without overrides, these companies might be unfairly penalized even though their remote roles don't require specific timezone alignment.

## How It Works

### Override Priority

The timezone detection system follows this priority order:

1. **Timezone Overrides** (NEW) - Check `config/company/timezone_overrides.json`
2. **Team Location** - Location mentioned in job description
3. **Job Location** - Explicit job posting location
4. **Company HQ** - Headquarters location (small/medium companies only)
5. **None** - Unknown timezone (no penalty)

### Configuration File

**Location**: `config/company/timezone_overrides.json`

**Structure**:
```json
{
  "$schema": "../../schemas/timezone_overrides.schema.json",
  "version": "1.0.0",
  "last_updated": "2025-10-20",
  "description": "Companies that should not receive timezone penalties",
  "overrides": [
    {
      "company_name": "GitLab",
      "timezone": "unknown",
      "reason": "All-remote company with globally distributed teams",
      "source": "manual",
      "added_date": "2025-10-20"
    }
  ],
  "patterns": [
    {
      "regex": ".*\\bRemote-First\\b.*",
      "timezone": "unknown",
      "reason": "Companies self-identifying as remote-first",
      "source": "pattern",
      "added_date": "2025-10-20"
    }
  ]
}
```

### Field Descriptions

#### Override Entry

- **company_name** (required): Exact company name to match (case-insensitive)
- **timezone** (required): Timezone override value
  - `"unknown"` - No timezone penalty (recommended for global companies)
  - `"pacific"`, `"eastern"`, `"central"`, `"mountain"` - Force specific timezone
- **reason** (optional): Human-readable explanation for the override
- **source** (optional): How this override was added (`manual`, `analytics`, `user-report`)
- **added_date** (optional): When this override was added (YYYY-MM-DD format)

#### Pattern Entry

- **regex** (required): Regular expression pattern to match against company name and description
- **timezone** (required): Timezone override value (same as above)
- **reason** (optional): Explanation for the pattern
- **source** (optional): Pattern source (`pattern`, `heuristic`)
- **added_date** (optional): When pattern was added

## Adding New Overrides

### When to Add an Override

Add a timezone override when:

1. **Company is globally distributed** - Teams in multiple timezones with no central HQ dependency
2. **All-remote company** - No physical offices, employees work from anywhere
3. **False penalties identified** - Analytics show timezone penalties for companies that shouldn't have them
4. **User reports** - Job seekers report unfair scoring for known remote-first companies

### Step-by-Step Process

1. **Verify the Need**
   ```bash
   # Run analytics to identify false penalties
   python scripts/analytics/timezone_false_penalties.py --env staging
   ```

2. **Add Override Entry**

   Edit `config/company/timezone_overrides.json`:
   ```json
   {
     "company_name": "Automattic",
     "timezone": "unknown",
     "reason": "All-remote company (WordPress.com, Tumblr)",
     "source": "analytics",
     "added_date": "2025-10-20"
   }
   ```

3. **Test the Override**
   ```bash
   # Run timezone tests to verify
   pytest tests/test_timezone_utils.py::TestTimezoneOverrides -v

   # Test with real job data (if available)
   python scripts/test_timezone_override.py --company "Automattic"
   ```

4. **Update Last Modified Date**

   Update the `last_updated` field at the top of the config file.

5. **Commit Changes**
   ```bash
   git add config/company/timezone_overrides.json
   git commit -m "config(timezone): add override for Automattic

   All-remote company should not receive timezone penalties.

   Closes #XX"
   ```

### Pattern-Based Overrides

For companies that follow naming conventions or self-identify in certain ways:

```json
{
  "regex": ".*\\bRemote-Only\\b.*",
  "timezone": "unknown",
  "reason": "Companies explicitly stating 'Remote-Only' policy",
  "source": "pattern",
  "added_date": "2025-10-20"
}
```

**Common Patterns**:
- `".*\\bRemote-First\\b.*"` - Matches "Remote-First" anywhere in company info
- `".*\\bAll-Remote\\b.*"` - Matches "All-Remote"
- `".*\\bDistributed Team\\b.*"` - Matches "Distributed Team"

## Validation

### Schema Validation

The loader validates:
- Required fields present (`company_name`, `timezone`)
- Valid timezone values (`unknown`, `pacific`, `eastern`, `central`, `mountain`)
- Valid regex patterns (compile test)

### Runtime Checks

```python
from job_finder.config.timezone_overrides import get_timezone_overrides

# Get cached configuration
overrides = get_timezone_overrides()

# Check if company has override
override = overrides.get_override("GitLab", "All-remote company")
# Returns: "unknown"

# Check if company is global (timezone='unknown')
is_global = overrides.is_global_company("Zapier")
# Returns: True
```

### Reload Configuration

To reload after making changes (useful in development):

```python
from job_finder.config.timezone_overrides import reload_timezone_overrides

# Force reload
reload_timezone_overrides()
```

## Monitoring

### Check Override Usage

```bash
# Check logs for override hits
gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder"
  AND labels.environment="staging"
  AND textPayload:"Timezone override"' \
  --limit 20 \
  --freshness 1h
```

### Analytics

Run before/after analytics to measure impact:

```bash
# Before adding overrides
python scripts/analytics/timezone_false_penalties.py --env staging > before.csv

# After adding overrides
python scripts/analytics/timezone_false_penalties.py --env staging > after.csv

# Compare results
python scripts/analytics/compare_timezone_penalties.py before.csv after.csv
```

## Common Companies

The default configuration includes these globally distributed companies:

- **GitLab** - All-remote since inception
- **Zapier** - Remote-first automation platform
- **Automattic** - WordPress.com, Tumblr (all-remote)
- **Toptal** - Global talent network
- **InVision** - Remote-first design platform
- **Basecamp** - Remote-first project management
- **Doist** - Todoist (all-remote)
- **Buffer** - Social media (all-remote)
- **HashiCorp** - Infrastructure tools (remote-friendly)
- **Stripe** - Global payment platform

## Troubleshooting

### Override Not Working

1. **Check company name spelling**
   ```python
   from job_finder.config.timezone_overrides import get_timezone_overrides
   overrides = get_timezone_overrides()
   print(overrides.overrides.keys())  # List all override keys
   ```

2. **Check case sensitivity** - Matching is case-insensitive, but verify capitalization

3. **Clear cache and reload**
   ```python
   from job_finder.config.timezone_overrides import reload_timezone_overrides
   reload_timezone_overrides()
   ```

4. **Check logs for errors**
   ```bash
   gcloud logging read 'logName="projects/static-sites-257923/logs/job-finder"
     AND textPayload:"timezone"' \
     --limit 50 \
     --freshness 1h
   ```

### Configuration Not Loading

1. **Verify file exists**: `config/company/timezone_overrides.json`
2. **Check JSON syntax**: Use `python -m json.tool config/company/timezone_overrides.json`
3. **Check file permissions**: Ensure file is readable
4. **Review startup logs**: Configuration loads at first use

## Best Practices

1. **Document Reasons** - Always include `reason` field explaining why override was added
2. **Use Analytics** - Base override decisions on data when possible
3. **Keep Patterns Specific** - Avoid overly broad regex patterns
4. **Regular Review** - Periodically review overrides (quarterly recommended)
5. **Test Thoroughly** - Add unit tests for each new override
6. **Version Control** - Commit configuration changes with clear messages

## Related Files

- **Configuration**: `config/company/timezone_overrides.json`
- **Loader**: `src/job_finder/config/timezone_overrides.py`
- **Detection Logic**: `src/job_finder/utils/timezone_utils.py`
- **Tests**: `tests/test_timezone_utils.py::TestTimezoneOverrides`
- **Scoring**: `src/job_finder/ai/matcher.py` (lines 187-201)

## See Also

- [BUG-2 Issue](../issues/bug-2-timezone-detection-global-companies.md)
- [Timezone Utilities Documentation](../utils/timezone-utils.md)
- [Match Scoring Documentation](../ai/match-scoring.md)
