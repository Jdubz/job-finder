# Firestore Data Cleanup Summary

**Date**: October 16, 2025
**Database**: portfolio and portfolio-staging

## Overview

This document summarizes the Firestore data cleanup performed to remove duplicate collections, merge duplicate records, and improve overall data quality.

## Actions Taken

### 1. Collection Analysis

Explored both `portfolio` and `portfolio-staging` databases to understand collection usage and identify issues.

**job-finder-FE Database (Production):**
- `companies` (2 docs) - Used by job-finder-FE app
- `contact-submissions` (13 docs) - Contact form submissions
- `experience-blurbs` (6 docs) - Profile content sections
- `experience-entries` (7 docs) - Work experience entries
- `generator` (16 docs) - Resume generation requests
- `job-listings` (25 docs) - Job source configurations
- `job-matches` (31 docs) - Matched jobs for display

**job-finder-FE-Staging Database (Job Finder):**
- `companies` (21 docs) - Company data with scoring
- `job-listings` (51 docs) - Job source configurations
- `job-matches` (92 docs) - Matched jobs from scraper
- `job-queue` (102 docs) - Queue for processing
- `queue-config` (1 doc) - Queue configuration

### 2. Removed Duplicate Collections

**Collections removed from portfolio-staging:**
1. `contact-submissions` (13 docs) - Duplicate from portfolio
2. `experience-blurbs` (6 docs) - Duplicate from portfolio
3. `experience-entries` (7 docs) - Duplicate from portfolio

**Reason**: These collections are owned by the job-finder-FE app and should only exist in the `portfolio` database, not in `portfolio-staging`.

**Backup location**: `/home/jdubz/Development/legacy-data/`
- `portfolio-staging_contact-submissions.json` (9.6K)
- `portfolio-staging_experience-blurbs.json` (14K)
- `portfolio-staging_experience-entries.json` (19K)

### 3. Merged Duplicate Company Records

**Found and merged**: 1 duplicate company record in `portfolio-staging`

**Details:**
- **Company**: Coinbase Careers
- **Action**: Merged 2 records into 1
- **Strategy**: Kept operational record (with tier/priorityScore) and merged in missing fields from other record
- **Records merged**:
  - Kept: `2tbbkuDLNSFGdWsCy7cz` (had tier/scoring data)
  - Deleted: `h25gAAoksHfCyUH8olzQ`

**Note**: MongoDB Careers duplicate was already resolved in initial cleanup run.

### 4. Removed Duplicate Job Postings

**job-finder-FE Database:**
- Duplicates found: 3
- Records deleted: 3
- Example duplicates:
  - Molina Healthcare - Lead Engineer
  - Novafy - Microsoft Power Platform
  - Edari - ServiceNow Engineer

**job-finder-FE-Staging Database:**
- Duplicates found: 13
- Records deleted: 13
- Primarily MongoDB and We Work Remotely job postings

**Total duplicates removed**: 16 job-matches across both databases

**Strategy**:
- Grouped jobs by URL
- Scored each record by data completeness (company info, description, resume intake, etc.)
- Kept the most complete record, deleted others

## Remaining Data Quality Issues

While we've cleaned up duplicates, some data quality issues remain that require the company info fetcher to resolve:

### job-finder-FE Database
- **Empty company info**: 21 jobs (68%)
- **Missing/Unknown locations**: 4 jobs (13%)

### job-finder-FE-Staging Database
- **Empty company info**: 40 jobs (43%)
- **Missing/Unknown locations**: 4 jobs (4%)

These issues occur when:
1. Company website is not provided in the job posting
2. Company info fetcher hasn't run yet for that company
3. Company website doesn't have clear about/mission/culture sections

## Database Structure Recommendations

### Current State
- **portfolio** database: Production data for job-finder-FE web app
- **portfolio-staging** database: Staging/dev data for Job Finder pipeline

### Shared Collections (Present in Both)
- `companies` - Different data: portfolio has about/industry, staging has tier/scoring
- `job-listings` - Different subsets of job sources
- `job-matches` - Different sets of matched jobs

### Job Finder Exclusive Collections (portfolio-staging only)
- `job-queue` - Processing queue
- `queue-config` - Queue configuration

### job-finder-FE Exclusive Collections (portfolio only)
- `contact-submissions` - Contact form data
- `experience-blurbs` - Profile content
- `experience-entries` - Work experience
- `generator` - Resume generation

## Scripts Created

1. **scripts/database/explore_firestore.py** - Explore and analyze Firestore collections
2. **scripts/database/cleanup_firestore.py** - Main cleanup script (backs up and removes duplicates)
3. **scripts/database/merge_company_duplicates.py** - Merge duplicate company records
4. **scripts/database/cleanup_job_matches.py** - Analyze and clean up job-matches

All scripts are now located in the `scripts/database/` directory.

## Next Steps

1. **Run company info fetcher** for jobs with empty company info
2. **Monitor for new duplicates** as the queue system processes jobs
3. **Consider**: Consolidating `companies` data between databases or establishing clear ownership
4. **Consider**: Whether `job-listings` should be unified or remain separate

## Files Backed Up

All removed data has been backed up to `/home/jdubz/Development/legacy-data/`:
- `portfolio-staging_contact-submissions.json`
- `portfolio-staging_experience-blurbs.json`
- `portfolio-staging_experience-entries.json`

These backups can be restored if needed.

## Summary Statistics

| Action | Count |
|--------|-------|
| Collections removed | 3 |
| Documents backed up | 26 |
| Company duplicates merged | 1 |
| Job-matches duplicates removed | 16 |
| **Total documents cleaned** | **20** |

## Data Quality Improvement

**Before Cleanup:**
- Duplicate collections: 3
- Duplicate company records: 2
- Duplicate job postings: 16
- Total redundant documents: 21 (across 26 documents in duplicate collections)

**After Cleanup:**
- Duplicate collections: 0 ✓
- Duplicate company records: 0 ✓
- Duplicate job postings: 0 ✓
- Data backed up: Yes ✓

The Firestore databases are now cleaner, with no duplicate collections or records. Data quality issues related to missing company info can be resolved by running the company info fetcher.
