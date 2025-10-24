"""Centralized Firestore client management with singleton pattern.

This module provides a singleton FirestoreClient that manages Firestore database
connections across the application, eliminating duplication of initialization logic.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as gcloud_firestore

from job_finder.exceptions import ConfigurationError, InitializationError

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Manages Firestore database connections with singleton pattern.

    This class ensures only one Firestore client exists per database name,
    reducing connection overhead and centralizing initialization logic.

    Example:
        >>> client = FirestoreClient.get_client("portfolio-staging")
        >>> collection = client.collection("job-matches")
    """

    _instances: Dict[str, gcloud_firestore.Client] = {}
    _firebase_initialized: bool = False

    @classmethod
    def get_client(
        cls, database_name: str = "portfolio-staging", credentials_path: Optional[str] = None
    ) -> gcloud_firestore.Client:
        """
        Get or create Firestore client for specified database.

        Args:
            database_name: Firestore database name. Use "(default)" for default database.
            credentials_path: Optional path to service account JSON. If not provided,
                            uses GOOGLE_APPLICATION_CREDENTIALS environment variable.

        Returns:
            Firestore client instance for the specified database.

        Raises:
            ValueError: If credentials path is not provided and not in environment.
            FileNotFoundError: If credentials file does not exist at specified path.
            RuntimeError: If Firestore initialization fails.

        Example:
            >>> # Get client for staging database
            >>> staging_client = FirestoreClient.get_client("portfolio-staging")
            >>>
            >>> # Get client for production database
            >>> prod_client = FirestoreClient.get_client("portfolio")
            >>>
            >>> # Both calls return the same client instance for same database
            >>> assert staging_client is FirestoreClient.get_client("portfolio-staging")
        """
        # Return existing client if available (singleton pattern)
        if database_name in cls._instances:
            logger.debug(f"Reusing existing Firestore client for: {database_name}")
            return cls._instances[database_name]

        # Initialize Firebase Admin once (singleton)
        if not cls._firebase_initialized:
            cls._initialize_firebase_admin(credentials_path)
            cls._firebase_initialized = True

        # Create new database client
        client = cls._create_database_client(database_name, credentials_path)

        # Cache and return
        cls._instances[database_name] = client
        logger.info(f"Created new Firestore client for database: {database_name}")

        return client

    @classmethod
    def _initialize_firebase_admin(cls, credentials_path: Optional[str] = None) -> None:
        """
        Initialize Firebase Admin SDK (only once per application).

        Args:
            credentials_path: Optional path to service account JSON.

        Raises:
            ValueError: If credentials not found.
            FileNotFoundError: If credentials file doesn't exist.
        """
        try:
            # Check if already initialized
            firebase_admin.get_app()
            logger.info("Firebase Admin already initialized, reusing existing app")
            return
        except ValueError:
            # Not initialized yet, proceed with initialization
            pass

        # Get credentials path
        creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            raise ConfigurationError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or pass credentials_path parameter."
            )

        if not Path(creds_path).exists():
            raise ConfigurationError(f"Credentials file not found: {creds_path}")

        # Initialize Firebase Admin
        try:
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
            logger.info("Initialized Firebase Admin SDK")
        except Exception as e:
            raise InitializationError(f"Failed to initialize Firebase Admin: {str(e)}") from e

    @classmethod
    def _create_database_client(
        cls, database_name: str, credentials_path: Optional[str] = None
    ) -> gcloud_firestore.Client:
        """
        Create a Firestore client for specified database.

        Args:
            database_name: Firestore database name.
            credentials_path: Optional path to service account JSON.

        Returns:
            Firestore client instance.

        Raises:
            ValueError: If credentials not found.
            FileNotFoundError: If credentials file doesn't exist.
            RuntimeError: If client creation fails.
        """
        # Get credentials path
        creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            raise ConfigurationError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or pass credentials_path parameter."
            )

        if not Path(creds_path).exists():
            raise ConfigurationError(f"Credentials file not found: {creds_path}")

        try:
            # Get project ID from credentials
            cred = credentials.Certificate(creds_path)
            project_id = cred.project_id

            # Create client for specific database
            if database_name == "(default)":
                client = gcloud_firestore.Client(project=project_id)
            else:
                client = gcloud_firestore.Client(project=project_id, database=database_name)

            logger.info(f"Connected to Firestore database: {database_name} in project {project_id}")

            return client

        except Exception as e:
            raise InitializationError(
                f"Failed to create Firestore client for {database_name}: {str(e)}"
            ) from e

    @classmethod
    def reset_instances(cls) -> None:
        """
        Reset all cached client instances.

        This is primarily useful for testing to ensure clean state between tests.
        In production, clients should be reused throughout the application lifetime.

        Warning:
            This will close all existing connections. Only use in tests or during
            graceful shutdown.
        """
        cls._instances.clear()
        cls._firebase_initialized = False
        logger.info("Reset all Firestore client instances")

    @classmethod
    def get_all_databases(cls) -> list[str]:
        """
        Get list of all database names with active clients.

        Returns:
            List of database names that have active client connections.
        """
        return list(cls._instances.keys())
