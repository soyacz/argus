# Test Run Investigator

AI-Enhanced Test Run Investigation for Scylla Cluster Test (SCT)

## Overview
Test Run Investigator is an intelligent assistant for investigating failures in Scylla Cluster Test (SCT) runs. It enables users to interactively query and analyze test runs, review SCT steps, analyze database node behavior, and retrieve relevant metrics. The system combines Retrieval-Augmented Generation (RAG), a Model Context Protocol (MCP) server, and integrations with Argus, Victoria Logs, Prometheus, and a local Knowledge Base.

## Features
- Interactive AI agent for SCT test run investigation
- Supports user-driven and proactive analysis
- Integrates with Argus (test metadata), Victoria Logs (logs), Prometheus (metrics), and a Knowledge Base (markdown docs)
- Uses RAG (via ChromaDB) to enhance responses with relevant documentation
- Caches logs, metrics, and findings for efficient repeated queries
- Asynchronous download and ingestion of logs/metrics

## Architecture
```
graph TD
    A[Agent\ne.g., GitHub Copilot] -->|MCP| B[TestRun Investigator]
    B --> |HTTP| C[Argus]
    B --> |HTTP| D[Victoria Logs]
    B --> |HTTP| E[Prometheus Metrics]
    B --> |RAG| F[Knowledge base\n.md files]
    B --> G[History \nExisting findings]
```

- **Agent**: Interacts with Test Run Investigator via MCP
- **Test Run Investigator**: Central component connecting to all data sources
- **Data Sources**: Argus (test metadata), Victoria Logs (logs), Prometheus (metrics), Knowledge Base (instructions)
- **History**: Stores analysis findings for reuse

## Core Components

### VictoriaLogs Integration
The `victoria_logs.py` module provides comprehensive log management capabilities:

- **Log Ingestion**: Download and ingest tar.zst archives containing `actions.log` and `raw_events.log`
- **Background Processing**: Stream logs into VictoriaLogs using JSON Stream API with threading
- **LogsQL Querying**: Query logs with time filtering and stream organization by run_id
- **Health Monitoring**: Automatic VictoriaLogs health checking with Docker setup instructions

```python
from testrun_investigator.victoria_logs import VictoriaLogsHandler

handler = VictoriaLogsHandler()
task_id = handler.ingest_logs("https://example.com/logs.tar.zst", "run-id")
actions = handler.query_actions_log("run-id", start_time="2025-05-17T04:44:00Z")
```

See [VictoriaLogs Documentation](docs/victoria_logs.md) for detailed usage and examples.

### RAG System
The RAG (Retrieval-Augmented Generation) system uses ChromaDB to provide context-aware responses based on the knowledge base.

### MCP Server
The MCP (Model Context Protocol) server provides comprehensive endpoints for log investigation:

- **Log Querying**: Query actions and events logs by stream, run_id, and date range
- **Log Ingestion**: Download and ingest log archives with progress tracking
- **Smart Detection**: Automatically detects missing logs and guides users
- **RAG Integration**: AI-powered investigation instructions from knowledge base

```python
# Example MCP tool usage
query_logs_by_stream("run-id", "action", limit=10)
ingest_logs("https://example.com/logs.tar.zst", "run-id")
get_investigation_instructions("database connection failures")
```

See [MCP Server Documentation](docs/mcp_server.md) for detailed endpoint reference.

## Getting Started

### Prerequisites
- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd testrun-investigator
   ```

2. Install dependencies using uv:
   ```bash
   uv sync
   ```

3. Set up VictoriaLogs (for log ingestion and querying):
   ```bash
   # Start VictoriaLogs with Docker
   docker run -d --name victoria-logs -p 9428:9428 \
     -v $(pwd)/cache/victoria-logs-data:/victoria-logs-data \
     victoriametrics/victoria-logs \
     -retentionPeriod=30d
   
   # Verify VictoriaLogs is running
   curl http://localhost:9428/health
   ```

4. Configure environment variables for Argus integration:
   ```bash
   # Create .env file or configure in MCP client
   echo "VICTORIA_LOGS_ENDPOINT=http://localhost:9428" > .env
   echo "RAG_KNOWLEDGE_BASE_DIR=./knowledge_base" >> .env
   echo "ARGUS_TOKEN=your-token-from-profile" >> .env
   echo "ARGUS_URL=https://argus.scylladb.com/" >> .env
   ```
   
   **Note**: Get your ARGUS_TOKEN from [https://argus.scylladb.com/profile/](https://argus.scylladb.com/profile/)

### Running the Project

#### As an MCP Server
To start the Test Run Investigator as an MCP (Model Context Protocol) server:

```bash
uv run python testrun_investigator/server.py
```

This command starts the MCP server that can be integrated with AI agents like GitHub Copilot or other MCP-compatible clients.

#### Development Mode
For development and testing purposes:

```bash
# Run tests
uv run pytest

```

### VS Code Integration
The project includes VS Code MCP configuration in `.vscode/mcp.json`. When using with VS Code and MCP-compatible extensions, the server will automatically start using the configured command.

Example MCP configuration:
```json
{
    "servers": {
        "testrun-investigator": {
            "command": "uv",
            "args": [
                "--directory",
                "<path_to_repo>/testrun-investigator",
                "run",
                "python",
                "testrun_investigator/server.py"
            ],
            "env": {
                "ARGUS_TOKEN": "your-token-from-argus-profile-page",
                "ARGUS_URL": "https://argus.scylladb.com/",
                "VICTORIA_LOGS_ENDPOINT": "http://localhost:9428",
                "RAG_KNOWLEDGE_BASE_DIR": "./knowledge_base"
            }
        }
    }
}
```

**Important**: Replace `your-token-from-argus-profile-page` with your actual token from [https://argus.scylladb.com/profile/](https://argus.scylladb.com/profile/)

## Tech Stack
- **Language**: Python 3.10+, with type hints
- **Package Management**: uv
- **Core Libraries**: mcp[cli], chromadb, requests, httpx, pydantic, rich, typer, scylladb-driver, prometheus-api-client

## Data Sources
- **Argus**: Test metadata, run information, and log download links via REST API
- **Victoria Logs**: SCT logs (actions.log, raw_events.log), database logs  
- **Prometheus**: Metrics during test execution
- **Knowledge Base**: Markdown files, accessed via RAG

## New Investigation Workflow
1. **Get Test Run Info**: Start with `get_test_run_info(test_id)` to fetch basic information and cache log links
2. **Review Test Details**: Examine test status, events summary, and available log download URLs
3. **Ingest Logs**: Use cached sct-runner-events archive URL with `ingest_logs()` if logs aren't already available
4. **Query Logs**: Use `query_actions_log()` and `query_raw_events_log()` for detailed investigation
5. **Get AI Guidance**: Use `get_investigation_instructions()` for expert analysis recommendations

## Operational Workflow
1. **Initialization**: MCP server instructs Agent to use RAG for relevant instructions
2. **User Query**: User asks about a test run (e.g., cause of failure)
3. **Instruction Retrieval**: Agent fetches instructions from Knowledge Base
4. **Data Retrieval & Analysis**: Agent gathers data from cache or sources, performs analysis
5. **Response Generation**: Agent responds, updates cache

## Caching
- Downloads and findings are cached on disk for performance
- Reuses existing findings for repeated queries

## Future Roadmap
- Integrate Knowledge Base into Argus for easier editing
- Enable real-time investigation by connecting to running SCT instances

## Contributing
- Use type hints and follow PEP8
- Write docstrings for all public functions/classes
- Use pytest for testing; mock external services in unit tests
- Never hardcode credentials
