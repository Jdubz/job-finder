"""Custom exceptions for the job finder application.

This module defines domain-specific exceptions that provide clearer error
handling and better context than generic Python exceptions.
"""


class JobFinderError(Exception):
    """Base exception for all job finder errors.

    All custom exceptions in this module inherit from this base class,
    making it easy to catch all job-finder-specific errors.
    """

    pass


class ConfigurationError(JobFinderError):
    """Raised when there's an error in configuration.

    Examples:
    - Missing required configuration fields
    - Invalid configuration values
    - Missing API keys or credentials
    - Invalid source configuration
    """

    pass


class InitializationError(JobFinderError):
    """Raised when a component fails to initialize properly.

    Examples:
    - Firestore client not initialized
    - Firebase Admin SDK initialization failed
    - Manager not initialized before use
    - Profile not loaded before processing
    """

    pass


class QueueProcessingError(JobFinderError):
    """Raised when queue item processing fails.

    Examples:
    - Unknown queue item type
    - Unknown sub-task type
    - Missing required pipeline state
    - Invalid queue item structure
    """

    pass


class AIProviderError(JobFinderError):
    """Raised when AI provider operations fail.

    Examples:
    - API key not configured
    - API request failed
    - Invalid provider type
    - Model not available
    """

    pass


class StorageError(JobFinderError):
    """Raised when storage operations fail.

    Examples:
    - Firestore not initialized
    - Failed to save document
    - Failed to query collection
    - Database connection error
    """

    pass


class ProfileError(JobFinderError):
    """Raised when profile operations fail.

    Examples:
    - Profile file not found
    - Invalid profile data
    - Missing required profile fields
    - Profile validation failed
    """

    pass


class ScraperError(JobFinderError):
    """Raised when scraping operations fail.

    Examples:
    - Missing required scraper configuration
    - Failed to fetch page
    - Selector not found
    - Invalid scraper type
    """

    pass
