"""Tests for FirestoreClient singleton."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from job_finder.exceptions import ConfigurationError, InitializationError
from job_finder.storage.firestore_client import FirestoreClient


@pytest.fixture(autouse=True)
def reset_firestore_client():
    """Reset FirestoreClient singleton state before each test."""
    FirestoreClient.reset_instances()
    yield
    FirestoreClient.reset_instances()


@pytest.fixture
def mock_credentials_path(tmp_path):
    """Create a temporary credentials file."""
    creds_file = tmp_path / "serviceAccountKey.json"
    creds_file.write_text(
        '{"type": "service_account", "project_id": "test-project", '
        '"private_key_id": "test", "private_key": "test", "client_email": "test@test.com"}'
    )
    return str(creds_file)


class TestFirestoreClient:
    """Test FirestoreClient singleton functionality."""

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_creates_new_instance(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that get_client creates a new instance for first call."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Get client
        client = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )

        # Verify Firebase Admin initialized
        mock_firebase.initialize_app.assert_called_once()

        # Verify Firestore client created
        mock_firestore.Client.assert_called_once_with(
            project="test-project", database="portfolio-staging"
        )

        # Verify client returned
        assert client == mock_client

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_returns_cached_instance(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that get_client returns cached instance for subsequent calls."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Get client twice
        client1 = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )
        client2 = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )

        # Verify same instance returned (singleton)
        assert client1 is client2

        # Verify Firestore client only created once
        assert mock_firestore.Client.call_count == 1

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_different_databases(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that different databases get different client instances."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client_staging = MagicMock()
        mock_client_prod = MagicMock()
        mock_firestore.Client.side_effect = [mock_client_staging, mock_client_prod]

        # Get clients for different databases
        client_staging = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )
        client_prod = FirestoreClient.get_client(
            database_name="portfolio", credentials_path=mock_credentials_path
        )

        # Verify different instances
        assert client_staging is not client_prod

        # Verify both created
        assert mock_firestore.Client.call_count == 2

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_with_env_credentials(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path, monkeypatch
    ):
        """Test that get_client uses GOOGLE_APPLICATION_CREDENTIALS env var."""
        # Set environment variable
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", mock_credentials_path)

        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Get client without passing credentials_path
        client = FirestoreClient.get_client(database_name="portfolio-staging")

        # Verify client created
        assert client == mock_client
        mock_creds.Certificate.assert_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch("job_finder.storage.firestore_client.firebase_admin")
    def test_get_client_missing_credentials(self, mock_firebase):
        """Test that get_client raises error when credentials not found."""
        mock_firebase.get_app.side_effect = ValueError("No app")
        with pytest.raises(ConfigurationError, match="Firebase credentials not found"):
            FirestoreClient.get_client(database_name="portfolio-staging")

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_missing_credentials_file(self, mock_creds, mock_firebase):
        """Test that get_client raises error when credentials file doesn't exist."""
        mock_firebase.get_app.side_effect = ValueError("No app")

        with pytest.raises(ConfigurationError, match="Credentials file not found"):
            FirestoreClient.get_client(
                database_name="portfolio-staging", credentials_path="/nonexistent/path.json"
            )

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_default_database(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that get_client handles default database correctly."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Get client for default database
        client = FirestoreClient.get_client(
            database_name="(default)", credentials_path=mock_credentials_path
        )

        # Verify Firestore client created without database parameter
        mock_firestore.Client.assert_called_once_with(project="test-project")
        assert client == mock_client

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_firebase_admin_already_initialized(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that Firebase Admin is not re-initialized if already exists."""
        # Setup mocks - Firebase Admin already initialized
        mock_firebase.get_app.return_value = Mock()  # No exception = already initialized
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Get client
        client = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )

        # Verify Firebase Admin NOT re-initialized
        mock_firebase.initialize_app.assert_not_called()

        # But client still created
        assert client == mock_client

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_client_initialization_error(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that get_client raises RuntimeError on initialization failure."""
        # Setup mocks to raise exception
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_creds.Certificate.side_effect = Exception("Failed to load credentials")

        # Verify RuntimeError raised
        with pytest.raises(InitializationError, match="Failed to initialize Firebase Admin"):
            FirestoreClient.get_client(
                database_name="portfolio-staging", credentials_path=mock_credentials_path
            )

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_reset_instances(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that reset_instances clears cached clients."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_firestore.Client.side_effect = [mock_client1, mock_client2]

        # Get client
        client1 = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )

        # Reset instances
        FirestoreClient.reset_instances()

        # Need to reset Firebase initialized flag for next call
        mock_firebase.get_app.side_effect = ValueError("No app")

        # Get client again
        client2 = FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )

        # Verify different instances (not cached)
        assert client1 is not client2

        # Verify client created twice
        assert mock_firestore.Client.call_count == 2

    @patch("job_finder.storage.firestore_client.firebase_admin")
    @patch("job_finder.storage.firestore_client.gcloud_firestore")
    @patch("job_finder.storage.firestore_client.credentials")
    def test_get_all_databases(
        self, mock_creds, mock_firestore, mock_firebase, mock_credentials_path
    ):
        """Test that get_all_databases returns all active database names."""
        # Setup mocks
        mock_firebase.get_app.side_effect = ValueError("No app")
        mock_cred = Mock()
        mock_cred.project_id = "test-project"
        mock_creds.Certificate.return_value = mock_cred
        mock_firestore.Client.return_value = MagicMock()

        # Get clients for multiple databases
        FirestoreClient.get_client(
            database_name="portfolio-staging", credentials_path=mock_credentials_path
        )
        FirestoreClient.get_client(
            database_name="portfolio", credentials_path=mock_credentials_path
        )

        # Get all databases
        databases = FirestoreClient.get_all_databases()

        # Verify both databases listed
        assert "portfolio-staging" in databases
        assert "portfolio" in databases
        assert len(databases) == 2
