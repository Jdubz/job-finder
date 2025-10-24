"""Application-wide constants."""

# Company Information
MIN_COMPANY_PAGE_LENGTH = 200  # Minimum characters for valid company page content
MIN_SPARSE_COMPANY_INFO_LENGTH = 100  # Threshold for "sparse" cached company info

# Text Processing
MAX_INTAKE_TEXT_LENGTH = 500  # Maximum length for intake data text fields
MAX_INTAKE_DESCRIPTION_LENGTH = 2000  # Maximum length for description in intake data
MAX_INTAKE_FIELD_LENGTH = 400  # Maximum length for most intake fields
MAX_DESCRIPTION_PREVIEW_LENGTH = 500  # Max description length to search for remote keywords
MAX_TEXT_OPTIMIZATION_LENGTH = 100  # Only optimize strings longer than this
MAX_COMPANY_INFO_TEXT_LENGTH = 1000  # Maximum length for company info text

# Filtering
DEFAULT_STRIKE_THRESHOLD = 5  # Number of strikes needed to reject a job
DEFAULT_MAX_JOB_AGE_DAYS = 7  # Default maximum job age in days

# Firestore Batch Limits
FIRESTORE_IN_QUERY_MAX = 10  # Maximum number of values in Firestore 'in' query
FIRESTORE_BATCH_WRITE_MAX = 500  # Maximum number of writes per batch

# AI/LLM Settings
CHEAP_MODEL_COST_PER_1K = 0.001  # Cost per 1K tokens for cheap models (Haiku)
EXPENSIVE_MODEL_COST_PER_1K = 0.075  # Cost per 1K tokens for expensive models (Sonnet)

# Scoring Adjustments
PORTLAND_OFFICE_BONUS = 50  # Priority score bonus for Portland office
PORTLAND_MATCH_BONUS = 15  # Match score bonus for Portland-based jobs
TECH_STACK_MAX_POINTS = 100  # Maximum points from tech stack alignment
REMOTE_FIRST_BONUS = 15  # Priority bonus for remote-first companies
AI_ML_FOCUS_BONUS = 10  # Priority bonus for AI/ML-focused companies
LARGE_COMPANY_BONUS = 10  # Match score bonus for large companies
SMALL_COMPANY_PENALTY = -5  # Match score penalty for small companies/startups

# Timezone Adjustments
SAME_TIMEZONE_BONUS = 5  # Bonus for same timezone
TIMEZONE_1_2HR_PENALTY = -2  # Penalty for 1-2 hour difference
TIMEZONE_3_4HR_PENALTY = -5  # Penalty for 3-4 hour difference
TIMEZONE_5_8HR_PENALTY = -10  # Penalty for 5-8 hour difference
TIMEZONE_9PLUS_PENALTY = -15  # Penalty for 9+ hour difference

# Company Size Thresholds
LARGE_COMPANY_EMPLOYEE_THRESHOLD = 10000  # Employees for "large" company
SMALL_COMPANY_EMPLOYEE_THRESHOLD = 100  # Employees for "small" company

# Match Score Thresholds
MIN_MATCH_SCORE = 80  # Minimum match score to accept job
HIGH_PRIORITY_THRESHOLD = 85  # Score threshold for high priority
MEDIUM_PRIORITY_THRESHOLD = 70  # Score threshold for medium priority

# Company Priority Tiers
TIER_S_THRESHOLD = 150  # Points needed for S-tier company
TIER_A_THRESHOLD = 100  # Points needed for A-tier company
TIER_B_THRESHOLD = 70  # Points needed for B-tier company
TIER_C_THRESHOLD = 50  # Points needed for C-tier company
# Below 50 = Tier D

# Queue/Pipeline
GRANULAR_PIPELINE_MEMORY_KB = 100  # Average memory per granular pipeline step
MONOLITHIC_PIPELINE_MEMORY_KB = 585  # Memory for old monolithic pipeline

# Scraping
DEFAULT_REQUEST_TIMEOUT = 30  # HTTP request timeout in seconds
DEFAULT_RATE_LIMIT_DELAY = 2  # Delay between requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests
MAX_HTML_SAMPLE_LENGTH = 20000  # Maximum HTML length for AI selector discovery
MAX_HTML_SAMPLE_LENGTH_SMALL = 15000  # Smaller HTML sample for faster processing

# Health Tracking
MAX_CONSECUTIVE_FAILURES = 5  # Failures before auto-disabling source
SOURCE_HEALTH_CHECK_INTERVAL = 3600  # Seconds between health checks

# Caching
COMPANY_INFO_CACHE_TTL = 86400  # Company info cache TTL in seconds (24 hours)
SOURCE_CONFIG_CACHE_TTL = 3600  # Source config cache TTL in seconds (1 hour)

# Logging
MAX_COMPANY_NAME_LOG_LENGTH = 50  # Maximum company name length in logs (default)
MIN_COMPANY_NAME_TRUNCATE_LENGTH = 3  # Minimum length for truncation ellipsis
