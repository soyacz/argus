#!/usr/bin/env python3
"""
Tests for the Test Run Information module.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from uuid import UUID

from testrun_investigator.test_run_info import TestRunInfoHandler, TTestRunInfoError


class TestTestRunInfoHandler:
    """Test cases for TestRunInfoHandler."""
    
    def test_get_argus_client_no_token(self):
        """Test client initialization without ARGUS_TOKEN."""
        handler = TestRunInfoHandler()
        
        # Clear any existing environment variable
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(TTestRunInfoError) as excinfo:
                handler._get_argus_client()
            
            assert "ARGUS_TOKEN environment variable is required" in str(excinfo.value)
            assert "https://argus.scylladb.com/profile/" in str(excinfo.value)
    
    @patch.dict(os.environ, {"ARGUS_TOKEN": "test-token", "ARGUS_URL": "https://test.example.com/"})
    @patch('testrun_investigator.test_run_info.ArgusSCTClient')
    def test_get_argus_client_with_env_vars(self, mock_client):
        """Test client initialization with environment variables."""
        handler = TestRunInfoHandler()
        
        # Mock the client
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        client = handler._get_argus_client()
        
        # Verify client was created with correct parameters
        mock_client.assert_called_once_with(
            auth_token="test-token",
            base_url="https://test.example.com/",
            run_id=UUID("e38b303f-df9b-4aac-b9d8-930cfd45306b")
        )
        assert client == mock_instance
    
    @patch.dict(os.environ, {"ARGUS_TOKEN": "test-token"})
    @patch('testrun_investigator.test_run_info.ArgusSCTClient')
    def test_get_argus_client_default_url(self, mock_client):
        """Test client initialization with default URL."""
        handler = TestRunInfoHandler()
        
        # Clear the cached client
        handler._get_argus_client.cache_clear()
        
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        client = handler._get_argus_client()
        
        # Verify default URL is used
        mock_client.assert_called_once_with(
            auth_token="test-token",
            base_url="https://argus.scylladb.com/",
            run_id=UUID("e38b303f-df9b-4aac-b9d8-930cfd45306b")
        )
    
    def test_extract_log_links(self):
        """Test log link extraction from test run data."""
        handler = TestRunInfoHandler()
        
        test_data = {
            "test_id": "123",
            "log_archive": "https://example.com/logs.tar.zst",
            "some_other_field": "value",
            "nested": {
                "sct_runner_log": "https://example.com/sct-runner.tar.gz",
                "other_data": "value"
            }
        }
        
        links = handler._extract_log_links(test_data)
        
        assert "log_archive" in links
        assert links["log_archive"] == "https://example.com/logs.tar.zst"
        assert "nested_sct_runner_log" in links
        assert links["nested_sct_runner_log"] == "https://example.com/sct-runner.tar.gz"
    
    def test_get_test_run_info_no_token(self):
        """Test get_test_run_info without ARGUS_TOKEN."""
        handler = TestRunInfoHandler()
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(TTestRunInfoError) as excinfo:
                handler.get_test_run_info("test-id")
            
            assert "Failed to retrieve test run information" in str(excinfo.value)
            assert "ARGUS_TOKEN environment variable is required" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__])
