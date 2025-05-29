#!/usr/bin/env python3
"""
Tests for VictoriaLogs integration module.

This test suite verifies the functionality of the victoria_logs module,
including log ingestion, querying, and error handling.
"""

import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from testrun_investigator.victoria_logs import (
    VictoriaLogsHandler,
    VictoriaLogsError,
    VictoriaLogsQueryError,
    ingest_logs,
    check_ingestion_status,
    query_actions_log,
    query_raw_events_log,
    query_logs_by_stream
)


class TestVictoriaLogsHandler:
    """Test suite for VictoriaLogsHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = VictoriaLogsHandler("http://localhost:9428")
        self.test_run_id = str(uuid.uuid4())
        self.test_event_id = str(uuid.uuid4())
    
    def test_init_default_endpoint(self):
        """Test handler initialization with default endpoint."""
        with patch.dict(os.environ, {'VICTORIA_LOGS_ENDPOINT': 'http://test:9428'}):
            handler = VictoriaLogsHandler()
            assert handler.endpoint == 'http://test:9428'
    
    def test_init_custom_endpoint(self):
        """Test handler initialization with custom endpoint."""
        handler = VictoriaLogsHandler("http://custom:9428")
        assert handler.endpoint == "http://custom:9428"
    
    @patch('requests.Session.get')
    def test_check_victoria_logs_running(self, mock_get):
        """Test VictoriaLogs health check when service is running."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        assert self.handler._check_victoria_logs() is True
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_check_victoria_logs_not_running(self, mock_get):
        """Test VictoriaLogs health check when service is not running."""
        mock_get.side_effect = requests.RequestException("Connection refused")
        
        assert self.handler._check_victoria_logs() is False
    
    def test_get_docker_command(self):
        """Test Docker command generation."""
        expected = (
            "docker run -d --name victoria-logs -p 9428:9428 "
            "-v $(pwd)/cache/victoria-logs-data:/victoria-logs-data "
            "victoriametrics/victoria-logs"
        )
        assert self.handler._get_docker_command() == expected
    
    @patch('requests.Session.get')
    def test_ingest_logs_victoria_logs_not_running(self, mock_get):
        """Test ingest_logs when VictoriaLogs is not running."""
        mock_get.side_effect = requests.RequestException("Connection refused")
        
        result = self.handler.ingest_logs("http://example.com/logs.tar.zst", self.test_run_id)
        
        assert result.startswith("docker run")
        assert "victoria-logs" in result
    
    def test_ingest_logs_invalid_run_id(self):
        """Test ingest_logs with invalid run_id."""
        with pytest.raises(ValueError, match="Invalid run_id UUID"):
            self.handler.ingest_logs("http://example.com/logs.tar.zst", "invalid-uuid")
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._check_victoria_logs')
    @patch('threading.Thread')
    def test_ingest_logs_success(self, mock_thread, mock_check):
        """Test successful ingest_logs operation."""
        mock_check.return_value = True
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        result = self.handler.ingest_logs("http://example.com/logs.tar.zst", self.test_run_id)
        
        # Should return a UUID task ID
        uuid.UUID(result)  # Will raise if not valid UUID
        
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    def test_check_ingestion_status_not_found(self):
        """Test check_ingestion_status with non-existent task."""
        with pytest.raises(ValueError, match="Task ID not found"):
            self.handler.check_ingestion_status("non-existent-task-id")
    
    def test_check_ingestion_status_success(self):
        """Test successful check_ingestion_status operation."""
        task_id = str(uuid.uuid4())
        self.handler._update_task_status(task_id, 'completed')
        
        status = self.handler.check_ingestion_status(task_id)
        
        assert status['task_id'] == task_id
        assert status['status'] == 'completed'
        assert status['error'] is None
    
    def test_query_actions_log_invalid_run_id(self):
        """Test query_actions_log with invalid run_id."""
        with pytest.raises(ValueError, match="Invalid run_id UUID"):
            self.handler.query_actions_log("invalid-uuid")
    
    def test_query_actions_log_invalid_timestamp(self):
        """Test query_actions_log with invalid timestamp."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp"):
            self.handler.query_actions_log(self.test_run_id, start_time="invalid-time")
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._execute_query')
    def test_query_actions_log_success(self, mock_execute):
        """Test successful query_actions_log operation."""
        mock_execute.return_value = [{'action': 'test', 'status': 'info'}]
        
        result = self.handler.query_actions_log(
            self.test_run_id,
            start_time="2025-05-17T04:44:00Z",
            end_time="2025-05-17T04:45:00Z"
        )
        
        assert len(result) == 1
        assert result[0]['action'] == 'test'
        
        # Verify query construction with stream filter
        expected_query = (
            f'{{stream="action", run_id="{self.test_run_id}"}} '
            '_time:[2025-05-17T04:44:00Z,2025-05-17T04:45:00Z]'
        )
        mock_execute.assert_called_once_with(expected_query)
    
    def test_query_raw_events_log_invalid_uuids(self):
        """Test query_raw_events_log with invalid UUIDs."""
        with pytest.raises(ValueError, match="Invalid UUID"):
            self.handler.query_raw_events_log("invalid-run-id", self.test_event_id)
        
        with pytest.raises(ValueError, match="Invalid UUID"):
            self.handler.query_raw_events_log(self.test_run_id, "invalid-event-id")
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._execute_query')
    def test_query_raw_events_log_success(self, mock_execute):
        """Test successful query_raw_events_log operation."""
        mock_execute.return_value = [{'event_id': self.test_event_id, 'type': 'ERROR'}]
        
        result = self.handler.query_raw_events_log(
            self.test_run_id,
            self.test_event_id,
            start_time="2025-05-17T04:44:00Z"
        )
        
        assert result is not None
        assert result['event_id'] == self.test_event_id
        
        # Verify query construction with stream filter
        expected_query = (
            f'{{stream="events", run_id="{self.test_run_id}"}} event_id:"{self.test_event_id}" '
            '_time:[2025-05-17T04:44:00Z,] | limit 1'
        )
        mock_execute.assert_called_once_with(expected_query)
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._execute_query')
    def test_query_raw_events_log_not_found(self, mock_execute):
        """Test query_raw_events_log when event is not found."""
        mock_execute.return_value = []
        
        result = self.handler.query_raw_events_log(self.test_run_id, self.test_event_id)
        
        assert result is None
    
    @patch('requests.Session.post')
    def test_execute_query_success(self, mock_post):
        """Test successful query execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Mock JSONL response (newline-delimited JSON)
        mock_response.text = '{"test": "data1"}\n{"test": "data2"}'
        mock_post.return_value = mock_response
        
        result = self.handler._execute_query('test query')
        
        assert result == [{'test': 'data1'}, {'test': 'data2'}]
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_execute_query_failure(self, mock_post):
        """Test query execution failure."""
        mock_post.side_effect = requests.RequestException("Query failed")
        
        with pytest.raises(VictoriaLogsQueryError, match="Query execution failed"):
            self.handler._execute_query('test query')
    
    @patch('requests.Session.post')
    def test_execute_query_jsonl_edge_cases(self, mock_post):
        """Test JSONL parsing with edge cases."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Test empty response
        mock_response.text = ""
        mock_post.return_value = mock_response
        result = self.handler._execute_query('test query')
        assert result == []
        
        # Test response with empty lines and malformed JSON
        mock_response.text = '{"valid": "json"}\n\n{"another": "valid"}\ninvalid json line\n{"final": "valid"}'
        result = self.handler._execute_query('test query')
        # Should return only the valid JSON lines, skipping invalid ones
        assert len(result) == 3
        assert result[0] == {"valid": "json"}
        assert result[1] == {"another": "valid"}
        assert result[2] == {"final": "valid"}
        
        # Test response with only whitespace
        mock_response.text = "   \n  \n  "
        result = self.handler._execute_query('test query')
        assert result == []
    
    def test_validate_iso8601_timestamp_valid(self):
        """Test ISO 8601 timestamp validation with valid timestamps."""
        valid_timestamps = [
            "2025-05-17T04:44:00Z",
            "2025-05-17T04:44:00.123Z",
            "2025-05-17T04:44:00",
            "2025-05-17T04:44:00.123"
        ]
        
        for timestamp in valid_timestamps:
            # Should not raise
            self.handler._validate_iso8601_timestamp(timestamp)
    
    def test_validate_iso8601_timestamp_invalid(self):
        """Test ISO 8601 timestamp validation with invalid timestamps."""
        invalid_timestamps = [
            "2025-05-17",
            "04:44:00",
            "2025-05-17 04:44:00",
            "invalid-timestamp"
        ]
        
        for timestamp in invalid_timestamps:
            with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp"):
                self.handler._validate_iso8601_timestamp(timestamp)
    
    def test_update_task_status_thread_safety(self):
        """Test task status updates are thread-safe."""
        task_id = str(uuid.uuid4())
        
        def update_status(status):
            self.handler._update_task_status(task_id, status)
        
        # Start multiple threads updating the same task
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_status, args=(f'status_{i}',))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Task should exist with one of the statuses
        status = self.handler.check_ingestion_status(task_id)
        assert status['task_id'] == task_id
        assert status['status'].startswith('status_')

    def test_query_logs_by_stream_invalid_run_id(self):
        """Test query_logs_by_stream with invalid run_id."""
        with pytest.raises(ValueError, match="Invalid run_id UUID"):
            self.handler.query_logs_by_stream("invalid-uuid", "action")

    def test_query_logs_by_stream_invalid_stream_type(self):
        """Test query_logs_by_stream with invalid stream type."""
        with pytest.raises(ValueError, match="Invalid stream_type"):
            self.handler.query_logs_by_stream(self.test_run_id, "invalid_stream")

    def test_query_logs_by_stream_invalid_timestamp(self):
        """Test query_logs_by_stream with invalid timestamp."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp"):
            self.handler.query_logs_by_stream(self.test_run_id, "action", start_time="invalid-time")

    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._execute_query')
    def test_query_logs_by_stream_action_success(self, mock_execute):
        """Test successful query_logs_by_stream operation for action stream."""
        mock_execute.return_value = [{'action': 'test', 'status': 'info'}]
        
        result = self.handler.query_logs_by_stream(
            self.test_run_id,
            "action",
            start_time="2025-05-17T04:44:00Z",
            end_time="2025-05-17T04:45:00Z",
            limit=100
        )
        
        assert len(result) == 1
        assert result[0]['action'] == 'test'
        
        # Verify query construction with stream filter
        expected_query = (
            f'{{stream="action", run_id="{self.test_run_id}"}} '
            '_time:[2025-05-17T04:44:00Z,2025-05-17T04:45:00Z] | limit 100'
        )
        mock_execute.assert_called_once_with(expected_query)

    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler._execute_query')
    def test_query_logs_by_stream_events_success(self, mock_execute):
        """Test successful query_logs_by_stream operation for events stream."""
        mock_execute.return_value = [{'event_id': self.test_event_id, 'type': 'ERROR'}]
        
        result = self.handler.query_logs_by_stream(
            self.test_run_id,
            "events",
            start_time="2025-05-17T04:44:00Z"
        )
        
        assert len(result) == 1
        assert result[0]['event_id'] == self.test_event_id
        
        # Verify query construction with stream filter
        expected_query = (
            f'{{stream="events", run_id="{self.test_run_id}"}} '
            '_time:[2025-05-17T04:44:00Z,]'
        )
        mock_execute.assert_called_once_with(expected_query)


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler')
    def test_ingest_logs_convenience(self, mock_handler_class):
        """Test ingest_logs convenience function."""
        mock_handler = Mock()
        mock_handler.ingest_logs.return_value = "task-id"
        mock_handler_class.return_value = mock_handler
        
        result = ingest_logs("http://example.com/logs.tar.zst", str(uuid.uuid4()))
        
        assert result == "task-id"
        mock_handler_class.assert_called_once_with(None)
        mock_handler.ingest_logs.assert_called_once()
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler')
    def test_check_ingestion_status_convenience(self, mock_handler_class):
        """Test check_ingestion_status convenience function."""
        mock_handler = Mock()
        mock_handler.check_ingestion_status.return_value = {"status": "completed"}
        mock_handler_class.return_value = mock_handler
        
        result = check_ingestion_status("task-id")
        
        assert result == {"status": "completed"}
        mock_handler_class.assert_called_once_with(None)
        mock_handler.check_ingestion_status.assert_called_once_with("task-id")
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler')
    def test_query_actions_log_convenience(self, mock_handler_class):
        """Test query_actions_log convenience function."""
        mock_handler = Mock()
        mock_handler.query_actions_log.return_value = [{"action": "test"}]
        mock_handler_class.return_value = mock_handler
        
        result = query_actions_log(str(uuid.uuid4()))
        
        assert result == [{"action": "test"}]
        mock_handler_class.assert_called_once_with(None)
        mock_handler.query_actions_log.assert_called_once()
    
    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler')
    def test_query_raw_events_log_convenience(self, mock_handler_class):
        """Test query_raw_events_log convenience function."""
        mock_handler = Mock()
        mock_handler.query_raw_events_log.return_value = {"event_id": "test"}
        mock_handler_class.return_value = mock_handler
        
        result = query_raw_events_log(str(uuid.uuid4()), str(uuid.uuid4()))
        
        assert result == {"event_id": "test"}
        mock_handler_class.assert_called_once_with(None)
        mock_handler.query_raw_events_log.assert_called_once()

    @patch('testrun_investigator.victoria_logs.VictoriaLogsHandler')
    def test_query_logs_by_stream_convenience(self, mock_handler_class):
        """Test query_logs_by_stream convenience function."""
        mock_handler = Mock()
        mock_handler.query_logs_by_stream.return_value = [{"action": "test"}]
        mock_handler_class.return_value = mock_handler
        
        result = query_logs_by_stream(str(uuid.uuid4()), "action")
        
        assert result == [{"action": "test"}]
        mock_handler_class.assert_called_once_with(None)
        mock_handler.query_logs_by_stream.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
