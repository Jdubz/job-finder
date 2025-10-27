"""Tests for configuration loader."""

from unittest.mock import MagicMock, patch

import pytest

from job_finder.job_queue.config_loader import ConfigLoader


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client."""
    with patch("job_finder.job_queue.config_loader.FirestoreClient") as mock_client:
        yield mock_client


@pytest.fixture
def config_loader(mock_firestore_client):
    """Create config loader with mocked Firestore."""
    mock_db = MagicMock()
    mock_firestore_client.get_client.return_value = mock_db
    loader = ConfigLoader(database_name="test-db")
    return loader


def test_get_stop_list(config_loader):
    """Test loading stop list from Firestore."""
    # Mock Firestore document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "excludedCompanies": ["BadCorp", "ScamInc"],
        "excludedKeywords": ["commission only", "unpaid"],
        "excludedDomains": ["spam.com"],
    }

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load stop list
    stop_list = config_loader.get_stop_list()

    # Assertions
    assert len(stop_list["excludedCompanies"]) == 2
    assert "BadCorp" in stop_list["excludedCompanies"]
    assert len(stop_list["excludedKeywords"]) == 2
    assert "commission only" in stop_list["excludedKeywords"]
    assert len(stop_list["excludedDomains"]) == 1

    # Verify Firestore calls
    config_loader.db.collection.assert_called_with("job-finder-config")
    config_loader.db.collection.return_value.document.assert_called_with("stop-list")


def test_get_stop_list_not_found(config_loader):
    """Test stop list when document doesn't exist."""
    # Mock non-existent document
    mock_doc = MagicMock()
    mock_doc.exists = False

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load stop list
    stop_list = config_loader.get_stop_list()

    # Should return empty lists
    assert stop_list["excludedCompanies"] == []
    assert stop_list["excludedKeywords"] == []
    assert stop_list["excludedDomains"] == []


def test_get_queue_settings(config_loader):
    """Test loading queue settings from Firestore."""
    # Mock Firestore document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "maxRetries": 5,
        "retryDelaySeconds": 120,
        "processingTimeout": 600,
    }

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load settings
    settings = config_loader.get_queue_settings()

    # Assertions
    assert settings["maxRetries"] == 5
    assert settings["retryDelaySeconds"] == 120
    assert settings["processingTimeout"] == 600


def test_get_queue_settings_defaults(config_loader):
    """Test queue settings with default values."""
    # Mock non-existent document
    mock_doc = MagicMock()
    mock_doc.exists = False

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load settings
    settings = config_loader.get_queue_settings()

    # Should return defaults
    assert settings["maxRetries"] == 3
    assert settings["retryDelaySeconds"] == 60
    assert settings["processingTimeout"] == 300


def test_get_ai_settings(config_loader):
    """Test loading AI settings from Firestore."""
    # Mock Firestore document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "provider": "openai",
        "model": "gpt-4",
        "minMatchScore": 80,
        "costBudgetDaily": 100.0,
    }

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load settings
    settings = config_loader.get_ai_settings()

    # Assertions
    assert settings["provider"] == "openai"
    assert settings["model"] == "gpt-4"
    assert settings["minMatchScore"] == 80
    assert settings["costBudgetDaily"] == 100.0


def test_get_ai_settings_defaults(config_loader):
    """Test AI settings with default values."""
    # Mock non-existent document
    mock_doc = MagicMock()
    mock_doc.exists = False

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load settings
    settings = config_loader.get_ai_settings()

    # Should return defaults
    assert settings["provider"] == "claude"
    assert settings["model"] == "claude-3-haiku-20240307"
    assert settings["minMatchScore"] == 70


def test_cache_refresh(config_loader):
    """Test cache refresh functionality."""
    # Mock Firestore document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"excludedCompanies": ["Test"]}

    config_loader.db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Load stop list twice (should use cache)
    config_loader.get_stop_list()
    config_loader.get_stop_list()

    # Should only call Firestore once
    assert config_loader.db.collection.return_value.document.return_value.get.call_count == 1

    # Refresh cache
    config_loader.refresh_cache()

    # Load again (should call Firestore)
    config_loader.get_stop_list()

    # Should call Firestore twice now (once before refresh, once after)
    assert config_loader.db.collection.return_value.document.return_value.get.call_count == 2
