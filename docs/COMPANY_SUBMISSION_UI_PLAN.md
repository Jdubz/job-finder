# Company Submission UI Requirements

## Overview

This document outlines the UI requirements for adding companies to the job-finder queue and monitoring their processing status in the job-finder-FE project.

**Backend Reference**: See [CLAUDE.md](../CLAUDE.md) for the granular company pipeline architecture.

## Data Flow
```
job-finder-FE UI → Firestore (job-queue) → Job Finder Worker → Firestore (companies)
                                            ↓
                    UI monitors queue item status
```

## Required Features

### 1. Company Submission Form

**Purpose**: Allow admins to submit a company for analysis

**Location**: New admin route

**Required Fields**:
- Company Name (text, required)
- Company Website URL (text, required)
- Source (dropdown with options: manual_submission, user_request, automated_scan)

**Validation Requirements**:
- Company name: minimum 2 characters
- Website URL: must be valid HTTP/HTTPS URL
- Check Firestore for duplicate URLs in pending/processing queue items
- Show error if duplicate found

**Submission Behavior**:
- Create new queue item in Firestore `job-queue` collection
- Set `type` to "company"
- Set `company_sub_task` to "fetch" (first pipeline step)
- Set `status` to "pending"
- On success: redirect to queue monitor
- On error: show error message inline

### 2. Company Queue Monitor

**Purpose**: View status of submitted companies in real-time

**Location**: New admin route

**Display Requirements**:
- Show list of company queue items from Firestore
- Real-time updates using Firestore listener
- Order by creation date (newest first)
- Limit to 50 most recent items

**Per Queue Item Display**:
- Company name
- Website URL
- Current status (pending, processing, success, failed, skipped)
- Current pipeline step (fetch, extract, analyze, save)
- Timestamp (created/updated)
- Error message if failed

**Pipeline Step Indicator**:
- Visual representation of 4 steps: fetch → extract → analyze → save
- Highlight current step
- Show completed steps differently

**Filtering Options**:
- Filter by status (all, pending, processing, success, failed)

**Actions**:
- View details button (links to company details)
- Retry button for failed items (updates status to "pending")

### 3. Company Details View

**Purpose**: View detailed information about a processed company

**Location**: New admin route with company ID parameter

**Data Sources**:
- Company data from `companies` collection in Firestore
- Latest queue item from `job-queue` collection

**Display Sections**:

**Basic Info**:
- Company name
- Website URL
- About text
- Culture/values text
- Mission statement

**Analysis Results**:
- Priority tier (S, A, B, C, D)
- Priority score
- Detected tech stack (list of technologies)
- Headquarters location
- Company size category

**Job Board**:
- Detected job board URL (if found)
- Link to view source discovery status

**Processing History**:
- List of all queue items for this company
- Show status, timestamps, error messages

## Routes to Add

- `/admin/companies/submit` - Company submission form
- `/admin/companies/queue` - Queue monitoring view
- `/admin/companies/[companyId]` - Company details view

## Navigation

Add new section to admin sidebar:
- Link to submission form
- Link to queue monitor

## Firestore Collections Used

**Read/Write**:
- `job-queue` - Create new company items, read for monitoring

**Read Only**:
- `companies` - View processed company data

## Security Requirements

- All routes require admin authentication
- Only admins can create company queue items
- Only admins can retry failed queue items

## Error Handling

**Invalid URL**:
- Show inline error: "Please enter a valid URL starting with http:// or https://"

**Duplicate Company**:
- Show error: "This company is already in the queue"
- Provide link to queue monitor

**Network/Firestore Errors**:
- Show error: "Failed to submit. Please try again"
- Log error for debugging

**Permission Denied**:
- Redirect to home page
- Show message: "You don't have permission to access this feature"

## User Experience

**Success Flow**:
1. Admin fills out submission form
2. Clicks submit button
3. Form validates and checks for duplicates
4. Creates queue item in Firestore
5. Redirects to queue monitor with success message
6. Monitor shows new item with "pending" status
7. Real-time updates show progression through pipeline steps
8. On completion, can view company details

**Error Flow**:
1. Admin fills out form with invalid data
2. Clicks submit
3. Sees validation error inline
4. Corrects issue and resubmits

## Future Considerations

Not included in initial implementation:
- Bulk upload functionality
- Email notifications
- Editing submitted companies
- Deleting from queue
- Advanced filtering/search
- Export functionality
