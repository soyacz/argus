#!/usr/bin/env python3
# Python 3.10
"""
VictoriaLogs Integration Module for Test Run Investigation.

This module provides functionality to manage log ingestion and querying for
AI-Enhanced Test Run Investigation. It handles downloading, unpacking, and
ingesting `actions.log` and `raw_events.log` files into VictoriaLogs using
proper stream configuration, and provides endpoints to query these logs using LogsQL.

Key Features:
- Download and unpack log archives (tar.zst) for test runs
- Ingest logs into VictoriaLogs using JSON Stream API with proper stream fields
- Stream-based log organization: 'action' stream for actions.log, 'events' stream for raw_events.log
- Query logs with LogsQL stream filters for optimal performance
- Background ingestion with task status tracking
- Automatic VictoriaLogs health checking with Docker instructions

Stream Configuration:
- Actions logs are ingested into the 'action' stream with stream fields: stream, run_id
- Raw events logs are ingested into the 'events' stream with stream fields: stream, run_id
- Stream filters {stream="action", run_id="..."} provide optimized query performance

Dependencies:
- zstandard: For unpacking tar.zst archives
- python-dotenv: For environment variable management
- requests: For HTTP communication with VictoriaLogs

Usage:
    handler = VictoriaLogsHandler()
    task_id = handler.ingest_logs("https://example.com/logs.tar.zst", "run-id")
    status = handler.check_ingestion_status(task_id)
    actions = handler.query_actions_log("run-id", start_time="2025-05-17T04:44:00Z")
    events = handler.query_logs_by_stream("run-id", "events", limit=100)
    event = handler.query_raw_events_log("run-id", "event-id")
"""

import json
import logging
import os
import tarfile
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import requests
import zstandard as zstd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
CACHE_DIR = "./cache"
DEFAULT_VICTORIA_LOGS_ENDPOINT = "http://localhost:9428"
VICTORIA_LOGS_DATA_DIR = "./cache/victoria-logs-data"
INGESTION_BATCH_SIZE = 1000
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
REQUEST_TIMEOUT = 30

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VictoriaLogsError(Exception):
    """Base exception for VictoriaLogs operations."""
    pass


class VictoriaLogsQueryError(VictoriaLogsError):
    """Exception raised for VictoriaLogs query failures."""
    pass


class VictoriaLogsHandler:
    """
    Handler for VictoriaLogs operations including log ingestion and querying with stream support.
    
    This class manages the entire lifecycle of log processing for test runs,
    from downloading and unpacking archives to ingesting logs into VictoriaLogs
    using proper stream configuration and providing query capabilities using LogsQL.
    
    Stream Organization:
    - Actions logs (actions.log) are ingested into the 'action' stream
    - Raw events logs (raw_events.log) are ingested into the 'events' stream
    - Each stream uses 'stream' and 'run_id' as stream fields for optimal performance
    
    Attributes:
        endpoint (str): VictoriaLogs endpoint URL
        session (requests.Session): HTTP session for connection reuse
        task_status (Dict[str, Dict]): Thread-safe task status tracking
        task_lock (threading.Lock): Lock for thread-safe task status updates
    """
    
    def __init__(self, endpoint: Optional[str] = None):
        """
        Initialize VictoriaLogs handler.
        
        Args:
            endpoint: VictoriaLogs endpoint URL. If None, reads from
                     VICTORIA_LOGS_ENDPOINT environment variable or uses default.
        """
        self.endpoint = endpoint or os.getenv(
            'VICTORIA_LOGS_ENDPOINT', 
            DEFAULT_VICTORIA_LOGS_ENDPOINT
        )
        self.session = requests.Session()
        self.session.timeout = REQUEST_TIMEOUT
        
        # Thread-safe task status tracking
        self.task_status: Dict[str, Dict[str, Any]] = {}
        self.task_lock = threading.Lock()
        
        # Ensure cache directories exist
        self._ensure_cache_dirs()
    
    def _ensure_cache_dirs(self) -> None:
        """Create necessary cache directories if they don't exist."""
        Path(CACHE_DIR).mkdir(exist_ok=True)
        Path(VICTORIA_LOGS_DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    def _check_victoria_logs(self) -> bool:
        """
        Check if VictoriaLogs is running by sending a health check request.
        
        Returns:
            bool: True if VictoriaLogs is accessible, False otherwise.
        """
        try:
            response = self.session.get(
                f"{self.endpoint}/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"VictoriaLogs health check failed: {e}")
            return False
    
    def _get_docker_command(self) -> str:
        """
        Get Docker command to start VictoriaLogs container.
        
        Returns:
            str: Docker command with proper volume mounting.
        """
        return (
            "docker run -d --name victoria-logs -p 9428:9428 "
            f"-v $(pwd)/cache/victoria-logs-data:/victoria-logs-data "
            "victoriametrics/victoria-logs"
        )
    
    def _download_archive(self, download_url: str, run_id: str) -> Path:
        """
        Download log archive to cache directory.
        
        Args:
            download_url: URL to download the tar.zst archive
            run_id: UUID string identifying the test run
            
        Returns:
            Path: Path to downloaded archive file
            
        Raises:
            VictoriaLogsError: If download fails
        """
        run_cache_dir = Path(CACHE_DIR) / run_id
        run_cache_dir.mkdir(exist_ok=True)
        
        archive_path = run_cache_dir / "archive.tar.zst"
        
        try:
            logger.info(f"Downloading archive from {download_url}")
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Archive downloaded to {archive_path}")
            return archive_path
            
        except requests.RequestException as e:
            error_msg = f"Failed to download archive: {e}"
            logger.error(error_msg)
            raise VictoriaLogsError(error_msg) from e
    
    def _unpack_archive(self, archive_path: Path, run_id: str) -> Path:
        """
        Unpack tar.zst archive to extract log files.
        
        Args:
            archive_path: Path to the tar.zst archive
            run_id: UUID string identifying the test run
            
        Returns:
            Path: Path to extraction directory
            
        Raises:
            VictoriaLogsError: If unpacking fails
        """
        extract_dir = Path(CACHE_DIR) / run_id
        
        try:
            logger.info(f"Unpacking archive {archive_path}")
            
            # Decompress with zstandard
            with open(archive_path, 'rb') as compressed_file:
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(compressed_file) as reader:
                    with tarfile.open(fileobj=reader, mode='r|') as tar:
                        tar.extractall(path=extract_dir)
            
            logger.info(f"Archive unpacked to {extract_dir}")
            return extract_dir
            
        except (zstd.ZstdError, tarfile.TarError, OSError) as e:
            error_msg = f"Failed to unpack archive: {e}"
            logger.error(error_msg)
            raise VictoriaLogsError(error_msg) from e
    
    def _ingest_log_file(self, log_path: Path, log_type: str, run_id: str) -> None:
        """
        Ingest a single log file into VictoriaLogs using JSON Stream API with proper stream configuration.
        
        Args:
            log_path: Path to log file
            log_type: Type of log ('actions' or 'raw_events')
            run_id: UUID string identifying the test run
            
        Raises:
            VictoriaLogsError: If ingestion fails
        """
        if not log_path.exists():
            logger.warning(f"Log file not found: {log_path}")
            return
        
        # Configure ingestion parameters based on log type with proper stream fields
        if log_type == 'actions':
            # Stream configuration for actions log
            # Stream fields should uniquely identify the application instance
            params = {
                '_stream_fields': 'stream,run_id',  # Use stream and run_id to identify log streams
                '_time_field': 'datetime',
                '_msg_field': 'action'
            }
            stream_name = 'action'
        elif log_type == 'raw_events':
            # Stream configuration for events log  
            # Stream fields should uniquely identify the application instance
            params = {
                '_stream_fields': 'stream,run_id',  # Use stream and run_id to identify log streams
                '_time_field': 'event_timestamp', 
                '_msg_field': 'line'
            }
            stream_name = 'events'
        else:
            raise VictoriaLogsError(f"Unknown log type: {log_type}")
        
        ingestion_url = f"{self.endpoint}/insert/jsonline"
        
        try:
            logger.info(f"Ingesting {log_type} log from {log_path}")
            
            with open(log_path, 'r', encoding='utf-8') as f:
                batch_lines = []
                line_count = 0
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse and enhance JSON line with run_id and stream
                        log_entry = json.loads(line)
                        log_entry['run_id'] = run_id
                        log_entry['stream'] = stream_name  # Add stream field for proper stream identification
                        batch_lines.append(json.dumps(log_entry))
                        
                        # Send batch when it reaches the batch size
                        if len(batch_lines) >= INGESTION_BATCH_SIZE:
                            self._send_batch(batch_lines, ingestion_url, params)
                            batch_lines = []
                        
                        line_count += 1
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping malformed JSON line: {line[:100]}... Error: {e}")
                        continue
                
                # Send remaining lines
                if batch_lines:
                    self._send_batch(batch_lines, ingestion_url, params)
                
                logger.info(f"Successfully ingested {line_count} lines from {log_type} log into '{stream_name}' stream")
                
        except OSError as e:
            error_msg = f"Failed to read log file {log_path}: {e}"
            logger.error(error_msg)
            raise VictoriaLogsError(error_msg) from e
    
    def _send_batch(self, batch_lines: List[str], url: str, params: Dict[str, str]) -> None:
        """
        Send a batch of log lines to VictoriaLogs with retry logic.
        
        Args:
            batch_lines: List of JSON lines to send
            url: VictoriaLogs ingestion endpoint URL
            params: Query parameters for the request
            
        Raises:
            VictoriaLogsError: If all retry attempts fail
        """
        batch_data = '\n'.join(batch_lines)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.post(
                    url,
                    params=params,
                    data=batch_data,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                logger.debug(f"Batch of {len(batch_lines)} lines ingested successfully")
                return
                
            except requests.RequestException as e:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"Ingestion attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_time} seconds..."
                )
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait_time)
                else:
                    error_msg = f"Failed to ingest batch after {MAX_RETRIES} attempts: {e}"
                    logger.error(error_msg)
                    raise VictoriaLogsError(error_msg) from e
    
    def _update_task_status(self, task_id: str, status: str, error: Optional[str] = None) -> None:
        """
        Update task status in a thread-safe manner.
        
        Args:
            task_id: UUID string identifying the task
            status: New status ('pending', 'completed', 'failed')
            error: Optional error message if status is 'failed'
        """
        with self.task_lock:
            self.task_status[task_id] = {
                'task_id': task_id,
                'status': status,
                'error': error
            }
    
    def _find_log_files(self, extract_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
        """
        Find actions.log and raw_events.log files in the extraction directory.
        
        The files might be in the root directory or in a subdirectory.
        
        Args:
            extract_dir: Path to the extraction directory
            
        Returns:
            tuple: (actions_log_path, raw_events_log_path) where paths can be None if not found
        """
        actions_log = None
        raw_events_log = None
        
        # Check root directory first
        if (extract_dir / "actions.log").exists():
            actions_log = extract_dir / "actions.log"
        if (extract_dir / "raw_events.log").exists():
            raw_events_log = extract_dir / "raw_events.log"
        
        # If not found in root, search subdirectories
        if actions_log is None or raw_events_log is None:
            for subdir in extract_dir.iterdir():
                if subdir.is_dir():
                    if actions_log is None and (subdir / "actions.log").exists():
                        actions_log = subdir / "actions.log"
                    if raw_events_log is None and (subdir / "raw_events.log").exists():
                        raw_events_log = subdir / "raw_events.log"
                    
                    # Stop searching if both files are found
                    if actions_log is not None and raw_events_log is not None:
                        break
        
        return actions_log, raw_events_log
    
    def _ingestion_worker(self, download_url: str, run_id: str, task_id: str) -> None:
        """
        Background worker function for log ingestion.
        
        Args:
            download_url: URL to download the tar.zst archive
            run_id: UUID string identifying the test run
            task_id: UUID string identifying the ingestion task
        """
        try:
            logger.info(f"Starting ingestion task {task_id} for run {run_id}")
            
            # Download and unpack archive
            archive_path = self._download_archive(download_url, run_id)
            extract_dir = self._unpack_archive(archive_path, run_id)
            
            # Find log files (they might be in subdirectories)
            actions_log, raw_events_log = self._find_log_files(extract_dir)
            
            # Ingest log files (ignore missing files)
            if actions_log:
                self._ingest_log_file(actions_log, 'actions', run_id)
            else:
                logger.warning(f"actions.log not found in {extract_dir}")
            
            if raw_events_log:
                self._ingest_log_file(raw_events_log, 'raw_events', run_id)
            else:
                logger.warning(f"raw_events.log not found in {extract_dir}")
            
            self._update_task_status(task_id, 'completed')
            logger.info(f"Ingestion task {task_id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ingestion task {task_id} failed: {error_msg}")
            self._update_task_status(task_id, 'failed', error_msg)
    
    def ingest_logs(self, download_url: str, run_id: str) -> str:
        """
        Download, unpack, and ingest logs into VictoriaLogs.
        
        This method checks if VictoriaLogs is running, downloads the log archive,
        unpacks it, and starts background ingestion of both actions.log and
        raw_events.log files. The ingestion process runs in a separate thread
        and can be monitored using the returned task ID.
        
        Args:
            download_url: URL to download the tar.zst archive containing logs
            run_id: UUID string identifying the test run
            
        Returns:
            str: Task ID (UUID string) for tracking ingestion progress, or
                 Docker command if VictoriaLogs is not running
                 
        Raises:
            ValueError: If run_id is not a valid UUID string
        """
        # Validate run_id as UUID
        try:
            uuid.UUID(run_id)
        except ValueError as e:
            raise ValueError(f"Invalid run_id UUID: {run_id}") from e
        
        # Check if VictoriaLogs is running
        if not self._check_victoria_logs():
            return self._get_docker_command()
        
        # Generate task ID and start background ingestion
        task_id = str(uuid.uuid4())
        self._update_task_status(task_id, 'pending')
        
        thread = threading.Thread(
            target=self._ingestion_worker,
            args=(download_url, run_id, task_id),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started ingestion task {task_id} for run {run_id}")
        return task_id
    
    def check_ingestion_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a background ingestion task.
        
        Args:
            task_id: UUID string identifying the ingestion task
            
        Returns:
            dict: Dictionary containing task status information with keys:
                - task_id (str): The task identifier
                - status (str): 'pending', 'completed', or 'failed'
                - error (str|None): Error message if status is 'failed'
                
        Raises:
            ValueError: If task_id is not found
        """
        with self.task_lock:
            if task_id not in self.task_status:
                raise ValueError(f"Task ID not found: {task_id}")
            return self.task_status[task_id].copy()
    
    def query_actions_log(
        self, 
        run_id: str, 
        start_time: Optional[str] = None, 
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query actions.log entries for a specific test run using stream filters.
        
        Uses LogsQL stream filters for optimal performance by filtering on the 'action' stream
        and run_id, with optional time range filtering.
        
        Args:
            run_id: UUID string identifying the test run
            start_time: Optional ISO 8601 timestamp for range start
            end_time: Optional ISO 8601 timestamp for range end
            
        Returns:
            List[dict]: List of action log entries as dictionaries
            
        Raises:
            ValueError: If run_id is invalid or timestamps are malformed
            VictoriaLogsQueryError: If query execution fails
        """
        # Validate run_id
        try:
            uuid.UUID(run_id)
        except ValueError as e:
            raise ValueError(f"Invalid run_id UUID: {run_id}") from e
        
        # Validate timestamps if provided
        if start_time:
            self._validate_iso8601_timestamp(start_time)
        if end_time:
            self._validate_iso8601_timestamp(end_time)
        
        # Construct LogsQL query using stream filter for optimal performance
        # Use stream filter to target the 'action' stream specifically
        query = f'{{stream="action", run_id="{run_id}"}}'
        
        if start_time and end_time:
            query += f' _time:[{start_time},{end_time}]'
        elif start_time:
            query += f' _time:[{start_time},]'
        elif end_time:
            query += f' _time:[,{end_time}]'
        
        return self._execute_query(query)
    
    def query_raw_events_log(
        self, 
        run_id: str, 
        event_id: str, 
        start_time: Optional[str] = None, 
        end_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query raw_events.log for a specific event using stream filters.
        
        Uses LogsQL stream filters for optimal performance by filtering on the 'events' stream,
        run_id and event_id, with optional time range filtering.
        
        Args:
            run_id: UUID string identifying the test run
            event_id: UUID string identifying the specific event
            start_time: Optional ISO 8601 timestamp for range start
            end_time: Optional ISO 8601 timestamp for range end
            
        Returns:
            dict|None: Event log entry as dictionary, or None if not found
            
        Raises:
            ValueError: If UUIDs are invalid or timestamps are malformed
            VictoriaLogsQueryError: If query execution fails
        """
        # Validate UUIDs
        try:
            uuid.UUID(run_id)
            uuid.UUID(event_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID: {e}") from e
        
        # Validate timestamps if provided
        if start_time:
            self._validate_iso8601_timestamp(start_time)
        if end_time:
            self._validate_iso8601_timestamp(end_time)
        
        # Construct LogsQL query using stream filter for optimal performance
        # Use stream filter to target the 'events' stream specifically
        query = f'{{stream="events", run_id="{run_id}"}} event_id:"{event_id}"'
        
        if start_time and end_time:
            query += f' _time:[{start_time},{end_time}]'
        elif start_time:
            query += f' _time:[{start_time},]'
        elif end_time:
            query += f' _time:[,{end_time}]'
        
        query += ' | limit 1'
        
        results = self._execute_query(query)
        return results[0] if results else None

    def query_logs_by_stream(
        self,
        run_id: str,
        stream_type: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query logs by stream type (action or events) for a specific test run.
        
        This method provides a general way to query logs from either the 'action' 
        or 'events' stream using stream filters for optimal performance.
        
        Args:
            run_id: UUID string identifying the test run
            stream_type: Stream type ('action' or 'events')
            start_time: Optional ISO 8601 timestamp for range start
            end_time: Optional ISO 8601 timestamp for range end
            limit: Optional limit on number of results returned
            
        Returns:
            List[dict]: List of log entries as dictionaries
            
        Raises:
            ValueError: If run_id is invalid, stream_type is invalid, or timestamps are malformed
            VictoriaLogsQueryError: If query execution fails
        """
        # Validate run_id
        try:
            uuid.UUID(run_id)
        except ValueError as e:
            raise ValueError(f"Invalid run_id UUID: {run_id}") from e
        
        # Validate stream type
        if stream_type not in ['action', 'events']:
            raise ValueError(f"Invalid stream_type: {stream_type}. Must be 'action' or 'events'")
        
        # Validate timestamps if provided
        if start_time:
            self._validate_iso8601_timestamp(start_time)
        if end_time:
            self._validate_iso8601_timestamp(end_time)
        
        # Construct LogsQL query using stream filter for optimal performance
        query = f'{{stream="{stream_type}", run_id="{run_id}"}}'
        
        if start_time and end_time:
            query += f' _time:[{start_time},{end_time}]'
        elif start_time:
            query += f' _time:[{start_time},]'
        elif end_time:
            query += f' _time:[,{end_time}]'
        
        if limit:
            query += f' | limit {limit}'
        
        return self._execute_query(query)
    
    def _validate_iso8601_timestamp(self, timestamp: str) -> None:
        """
        Validate ISO 8601 timestamp format.
        
        Args:
            timestamp: ISO 8601 timestamp string to validate
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        import re
        
        # Basic ISO 8601 pattern (simplified)
        iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$'
        
        if not re.match(iso8601_pattern, timestamp):
            raise ValueError(f"Invalid ISO 8601 timestamp format: {timestamp}")
    
    def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute LogsQL query against VictoriaLogs.
        
        Args:
            query: LogsQL query string
            
        Returns:
            List[dict]: Query results as list of dictionaries
            
        Raises:
            VictoriaLogsQueryError: If query execution fails
        """
        query_url = f"{self.endpoint}/select/logsql/query"
        
        try:
            logger.debug(f"Executing query: {query}")
            
            response = self.session.post(
                query_url,
                data={'query': query},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            
            # Parse JSONL response (newline-delimited JSON)
            try:
                response_text = response.text.strip()
                if not response_text:
                    return []
                
                # VictoriaLogs returns JSONL format (newline-delimited JSON objects)
                results = []
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            result = json.loads(line)
                            results.append(result)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSONL line: {line}, error: {e}")
                            continue
                
                return results
                    
            except Exception as e:
                logger.error(f"Failed to parse query response as JSONL: {e}")
                return []
            
        except requests.RequestException as e:
            error_msg = f"Query execution failed: {e}"
            logger.error(error_msg)
            raise VictoriaLogsQueryError(error_msg) from e
    
    def __del__(self):
        """Clean up resources when handler is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()


# Convenience functions for direct usage
def ingest_logs(download_url: str, run_id: str, endpoint: Optional[str] = None) -> str:
    """
    Convenience function to ingest logs using default handler.
    
    Args:
        download_url: URL to download the tar.zst archive
        run_id: UUID string identifying the test run
        endpoint: Optional VictoriaLogs endpoint override
        
    Returns:
        str: Task ID or Docker command
    """
    handler = VictoriaLogsHandler(endpoint)
    return handler.ingest_logs(download_url, run_id)


def check_ingestion_status(task_id: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to check ingestion status.
    
    Args:
        task_id: UUID string identifying the task
        endpoint: Optional VictoriaLogs endpoint override
        
    Returns:
        dict: Task status information
    """
    handler = VictoriaLogsHandler(endpoint)
    return handler.check_ingestion_status(task_id)


def query_actions_log(
    run_id: str, 
    start_time: Optional[str] = None, 
    end_time: Optional[str] = None,
    endpoint: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to query actions log.
    
    Args:
        run_id: UUID string identifying the test run
        start_time: Optional ISO 8601 timestamp for range start
        end_time: Optional ISO 8601 timestamp for range end
        endpoint: Optional VictoriaLogs endpoint override
        
    Returns:
        List[dict]: Action log entries
    """
    handler = VictoriaLogsHandler(endpoint)
    return handler.query_actions_log(run_id, start_time, end_time)


def query_raw_events_log(
    run_id: str, 
    event_id: str, 
    start_time: Optional[str] = None, 
    end_time: Optional[str] = None,
    endpoint: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to query raw events log.
    
    Args:
        run_id: UUID string identifying the test run
        event_id: UUID string identifying the event
        start_time: Optional ISO 8601 timestamp for range start
        end_time: Optional ISO 8601 timestamp for range end
        endpoint: Optional VictoriaLogs endpoint override
        
    Returns:
        dict|None: Event log entry or None
    """
    handler = VictoriaLogsHandler(endpoint)
    return handler.query_raw_events_log(run_id, event_id, start_time, end_time)


def query_logs_by_stream(
    run_id: str,
    stream_type: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = None,
    endpoint: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to query logs by stream type.
    
    Args:
        run_id: UUID string identifying the test run
        stream_type: Stream type ('action' or 'events')
        start_time: Optional ISO 8601 timestamp for range start
        end_time: Optional ISO 8601 timestamp for range end
        limit: Optional limit on number of results returned
        endpoint: Optional VictoriaLogs endpoint override
        
    Returns:
        List[dict]: List of log entries
    """
    handler = VictoriaLogsHandler(endpoint)
    return handler.query_logs_by_stream(run_id, stream_type, start_time, end_time, limit)
