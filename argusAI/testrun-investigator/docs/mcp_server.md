# MCP Server for Test Run Investigation

This MCP (Model Context Protocol) server provides comprehensive log querying and ingestion capabilities for test run investigation using Victoria logs.

## Features

- **Log Querying**: Query actions and events logs by stream, run_id, and date range
- **Log Ingestion**: Download and ingest log archives with progress tracking  
- **Smart Detection**: Automatically detects if logs are missing and guides users to ingest them
- **RAG Integration**: Get AI-powered investigation instructions from the knowledge base

## Available Tools

### Core Victoria Logs Tools

#### `query_logs_by_stream(run_id, stream_type, start_time=None, end_time=None, limit=None)`
Query logs by stream type (action or events) for a specific test run.
- `run_id`: UUID identifying the test run
- `stream_type`: 'action' or 'events'  
- `start_time`: Optional ISO 8601 timestamp (e.g., '2025-05-17T04:44:00Z')
- `end_time`: Optional ISO 8601 timestamp
- `limit`: Optional limit on results

#### `query_actions_log(run_id, start_time=None, end_time=None)`
Query actions.log entries for a specific test run.
- Returns all action log entries with optional time filtering

#### `query_raw_events_log(run_id, event_id, start_time=None, end_time=None)`
Query raw_events.log for a specific event.
- `event_id`: UUID identifying the specific event

#### `ingest_logs(download_url, run_id)`
Download and ingest log archives into VictoriaLogs.
- `download_url`: URL to tar.zst archive containing logs
- `run_id`: UUID identifying the test run
- Returns task_id for monitoring or Docker setup instructions

#### `check_ingestion_status(task_id)`
Check the status of a background log ingestion task.
- Returns status information (pending, completed, failed)

### RAG Tools

#### `get_investigation_instructions(user_query)`
Get relevant investigation instructions based on a user query.
- Uses RAG system to find relevant troubleshooting guidance

## Usage Examples

### Basic Log Querying
```python
# Query action logs for a test run
result = query_logs_by_stream("run-uuid", "action", limit=10)

# Query specific time range
result = query_actions_log("run-uuid", "2025-05-17T04:44:00Z", "2025-05-17T05:00:00Z")

# Query specific event
result = query_raw_events_log("run-uuid", "event-uuid")
```

### Log Ingestion Workflow
```python
# Start ingestion
result = ingest_logs("https://example.com/logs.tar.zst", "run-uuid")
# Returns: {"status": "ingestion_started", "task_id": "task-uuid", ...}

# Monitor progress  
status = check_ingestion_status("task-uuid")
# Returns: {"status": "success", "task_status": {"status": "completed", ...}}

# Query logs after ingestion
logs = query_logs_by_stream("run-uuid", "action")
```

### Missing Logs Detection
The server automatically detects when logs haven't been ingested:
```
No logs found for run_id 'xyz'. Logs may not be ingested yet. 
Use ingest_logs endpoint to download and ingest logs first.
```

### Investigation Assistance
```python
# Get AI guidance for specific issues
instructions = get_investigation_instructions("Database connection failures")
# Returns relevant troubleshooting steps from knowledge base
```

## Running the Server

```bash
cd /path/to/testrun-investigator
PYTHONPATH=. uv run python testrun_investigator/server.py
```

## Response Format

All tools return JSON strings with structured responses:
```json
{
  "status": "success|error",
  "run_id": "uuid",
  "count": 123,
  "logs": [...],
  "message": "descriptive message"
}
```

## Victoria Logs Integration

The server integrates with Victoria logs using:
- **Stream Organization**: Actions in 'action' stream, events in 'events' stream
- **Stream Fields**: `stream` and `run_id` for optimal query performance
- **JSON Stream API**: For efficient log ingestion
- **LogsQL**: Advanced query language with stream filters

## Error Handling

The server provides comprehensive error handling:
- Parameter validation (UUID format, timestamps, stream types)
- Victoria logs connectivity checks
- Missing logs detection with user guidance
- Detailed error messages for troubleshooting
