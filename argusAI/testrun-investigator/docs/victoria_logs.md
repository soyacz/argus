# VictoriaLogs Integration Module

The `victoria_logs.py` module provides comprehensive functionality for managing log ingestion and querying for AI-Enhanced Test Run Investigation. It integrates with VictoriaLogs to store and query test run logs using LogsQL with optimized stream-based organization.

## Features

- **Stream-Based Organization**: Logs are organized into 'action' and 'events' streams for optimal performance
- **Log Archive Processing**: Download and unpack tar.zst archives containing test logs
- **Background Ingestion**: Stream logs into VictoriaLogs using JSON Stream API with threading
- **Optimized LogsQL Querying**: Query logs with stream filters, time filtering, and result limiting
- **Health Monitoring**: Automatic VictoriaLogs health checking with Docker setup instructions
- **Task Tracking**: Monitor ingestion progress with thread-safe status tracking
- **Error Handling**: Comprehensive error handling with custom exceptions

## Stream Organization

The module uses VictoriaLogs streams to optimize storage and query performance:

- **Action Stream**: Contains actions.log entries with stream fields `stream="action"` and `run_id`
- **Events Stream**: Contains raw_events.log entries with stream fields `stream="events"` and `run_id`

This organization provides:
- Reduced disk space usage through better compression
- Increased query performance with stream filters `{stream="...", run_id="..."}`
- Organized data separation between different log types

## Quick Start

### 1. Start VictoriaLogs

```bash
docker run -d --name victoria-logs -p 9428:9428 \
  -v $(pwd)/cache/victoria-logs-data:/victoria-logs-data \
  victoriametrics/victoria-logs
```

### 2. Basic Usage

```python
from testrun_investigator.victoria_logs import VictoriaLogsHandler

# Initialize handler
handler = VictoriaLogsHandler()

# Ingest logs from a test run
task_id = handler.ingest_logs(
    "https://example.com/logs.tar.zst", 
    "123e4567-e89b-12d3-a456-426614174000"
)

# Check ingestion status
status = handler.check_ingestion_status(task_id)
print(f"Status: {status['status']}")

# Query action logs with stream filter and time filtering
actions = handler.query_actions_log(
    "123e4567-e89b-12d3-a456-426614174000",
    start_time="2025-05-17T04:44:00Z",
    end_time="2025-05-17T04:45:00Z"
)

# Query specific event using stream filter
event = handler.query_raw_events_log(
    "123e4567-e89b-12d3-a456-426614174000",
    "ee0368b3-0b89-4cb1-835d-29460f349bef"
)

# Use new stream-based query method
events = handler.query_logs_by_stream(
    "123e4567-e89b-12d3-a456-426614174000",
    "events",  # or "action"
    limit=100
)
    "ee0368b3-0b89-4cb1-835d-29460f349bef"
)
```

### 3. Convenience Functions

```python
from testrun_investigator.victoria_logs import (
    ingest_logs, 
    query_actions_log, 
    query_raw_events_log,
    query_logs_by_stream
)

# Simplified interface without handler instantiation
task_id = ingest_logs("https://example.com/logs.tar.zst", "run-id")
actions = query_actions_log("run-id", start_time="2025-05-17T04:44:00Z")
event = query_raw_events_log("run-id", "event-id")

# Stream-based querying with convenience function
action_logs = query_logs_by_stream("run-id", "action", limit=50)
event_logs = query_logs_by_stream("run-id", "events", 
                                 start_time="2025-05-17T04:44:00Z")
```

## Configuration

### Environment Variables

- `VICTORIA_LOGS_ENDPOINT`: VictoriaLogs endpoint URL (default: `http://localhost:9428`)

### Cache Structure

```
./cache/
├── victoria-logs-data/          # VictoriaLogs data persistence
└── <run-id>/                    # Per-run cache
    ├── archive.tar.zst          # Downloaded archive
    ├── actions.log              # Extracted action logs
    └── raw_events.log           # Extracted event logs
```

## Log Formats

### Actions Log (actions.log)

JSON lines format with test action information:

```json
{
  "datetime": "2025-05-17T04:44:04.545036Z",
  "status": "info",
  "source": "tester",
  "action": "Finished - start_scylla_server",
  "target": "rolling-upgrade--ubuntu-focal-db-node-407cb58b-3"
}
```

### Raw Events Log (raw_events.log)

JSON lines format with detailed event information:

```json
{
  "base": "DatabaseLogEvent",
  "type": "OVERSIZED_ALLOCATION",
  "event_timestamp": 1747457048.9229765,
  "severity": "ERROR",
  "event_id": "ee0368b3-0b89-4cb1-835d-29460f349bef",
  "node": "rolling-upgrade--ubuntu-focal-db-node-407cb58b-3",
  "line": "<message line>"
}
```

## VictoriaLogs Integration

### Stream Configuration

**Action Stream (actions.log):**
- Stream fields: `stream="action"`, `run_id`
- Time field: `datetime` (RFC3339)
- Message field: `action`
- Optimized for action-based queries and timeline analysis

**Events Stream (raw_events.log):**
- Stream fields: `stream="events"`, `run_id`
- Time field: `event_timestamp` (Unix timestamp)
- Message field: `line`
- Optimized for event-based queries and error analysis

### LogsQL Query Examples

```logsql
-- Query actions using stream filter (optimized performance)
{stream="action", run_id="123e4567-e89b-12d3-a456-426614174000"} _time:[2025-05-17T04:44:00Z,2025-05-17T04:45:00Z]

-- Query events using stream filter (optimized performance)
{stream="events", run_id="123e4567-e89b-12d3-a456-426614174000"} severity="ERROR"

-- Query specific event with stream filter
{stream="events", run_id="123e4567-e89b-12d3-a456-426614174000"} event_id="ee0368b3-0b89-4cb1-835d-29460f349bef" | limit 1

-- Query all logs for a run (less optimal)
run_id="123e4567-e89b-12d3-a456-426614174000"
```

## API Reference

### VictoriaLogsHandler

#### `__init__(endpoint: Optional[str] = None)`

Initialize handler with optional custom endpoint.

#### `ingest_logs(download_url: str, run_id: str) -> str`

Download, unpack, and ingest logs into VictoriaLogs.

**Parameters:**
- `download_url`: URL to tar.zst archive
- `run_id`: UUID string identifying the test run

**Returns:**
- Task ID (UUID string) or Docker command if VictoriaLogs not running

#### `check_ingestion_status(task_id: str) -> Dict[str, Any]`

Check status of background ingestion task.

**Returns:**
```python
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending|completed|failed",
    "error": None  # or error message if failed
}
```

#### `query_actions_log(run_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict[str, Any]]`

Query action log entries using stream filter `{stream="action", run_id="..."}` with optional time filtering.

**Parameters:**
- `run_id`: UUID string identifying the test run
- `start_time`: Optional ISO 8601 timestamp
- `end_time`: Optional ISO 8601 timestamp

#### `query_raw_events_log(run_id: str, event_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> Optional[Dict[str, Any]]`

Query specific event from raw events log using stream filter `{stream="events", run_id="..."}`.

**Returns:**
- Event dictionary or `None` if not found

#### `query_logs_by_stream(run_id: str, stream_type: str, start_time: Optional[str] = None, end_time: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]`

Query logs by stream type with flexible filtering options.

**Parameters:**
- `run_id`: UUID string identifying the test run
- `stream_type`: Stream type ('action' or 'events')
- `start_time`: Optional ISO 8601 timestamp
- `end_time`: Optional ISO 8601 timestamp
- `limit`: Optional limit on number of results

**Returns:**
- List of log entries from the specified stream

## Error Handling

### Custom Exceptions

- `VictoriaLogsError`: Base exception for VictoriaLogs operations
- `VictoriaLogsQueryError`: Query execution failures

### Error Scenarios

- VictoriaLogs not running → Returns Docker command
- Invalid URLs → Logs error, updates task status
- Missing log files → Ignores and continues
- Malformed JSON → Skips lines, logs warnings
- Network issues → Retries with exponential backoff

## Performance Considerations

- **Stream-Based Organization**: Separate streams ('action', 'events') provide optimal compression and query performance
- **Stream Filters**: Use `{stream="...", run_id="..."}` filters for optimized queries that scan fewer log streams
- **Connection Reuse**: Uses `requests.Session` for HTTP efficiency
- **Streaming**: Streams file downloads and log ingestion
- **Batching**: Processes logs in 1000-line batches
- **Threading**: Background ingestion with thread-safe status tracking
- **Retry Logic**: Exponential backoff for transient failures
- **Query Optimization**: Stream filters reduce disk I/O and improve response times

## Testing

Run the comprehensive test suite:

```bash
uv run python -m pytest tests/test_victoria_logs.py -v
```

Run the demo script:

```bash
cd /path/to/testrun-investigator
PYTHONPATH=. uv run python examples/victoria_logs_demo.py
```

## Dependencies

- `zstandard`: For tar.zst archive extraction
- `python-dotenv`: Environment variable management
- `requests`: HTTP client for VictoriaLogs communication

## Example Workflow

1. **Setup VictoriaLogs**:
   ```bash
   docker run -d --name victoria-logs -p 9428:9428 \
     -v $(pwd)/cache/victoria-logs-data:/victoria-logs-data \
     victoriametrics/victoria-logs
   ```

2. **Ingest Test Run Logs**:
   ```python
   handler = VictoriaLogsHandler()
   task_id = handler.ingest_logs(
       "https://s3.example.com/test-logs/run-123.tar.zst",
       "123e4567-e89b-12d3-a456-426614174000"
   )
   ```

3. **Monitor Ingestion**:
   ```python
   while True:
       status = handler.check_ingestion_status(task_id)
       if status['status'] in ['completed', 'failed']:
           break
       time.sleep(5)
   ```

4. **Query and Analyze**:
   ```python
   # Get all error actions
   actions = handler.query_actions_log(run_id)
   errors = [a for a in actions if a.get('status') == 'error']
   
   # Get detailed event information
   for action in errors:
       if 'trace_id' in action:
           event = handler.query_raw_events_log(run_id, action['trace_id'])
           print(f"Error: {event.get('type')} - {event.get('line')}")
   ```

## Best Practices

1. **Always check VictoriaLogs health** before starting ingestion
2. **Use proper UUID validation** for run_id and event_id parameters
3. **Handle ingestion failures gracefully** by checking task status
4. **Use time filtering** in queries to improve performance
5. **Monitor cache directory size** as logs accumulate
6. **Use convenience functions** for simple operations
7. **Implement proper error handling** in your application code
