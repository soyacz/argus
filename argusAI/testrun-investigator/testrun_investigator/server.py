"""
MCP server entrypoint for Test Run Investigator.
"""
import json
from mcp.server.fastmcp import FastMCP

# Handle both direct execution and module import
try:
    from .rag import create_rag_system, RAGSystemError
    from .victoria_logs import VictoriaLogsHandler, VictoriaLogsError, VictoriaLogsQueryError
    from .test_run_info import TestRunInfoHandler, TTestRunInfoError
except ImportError:
    from rag import create_rag_system, RAGSystemError
    from victoria_logs import VictoriaLogsHandler, VictoriaLogsError, VictoriaLogsQueryError
    from test_run_info import TestRunInfoHandler, TTestRunInfoError

mcp = FastMCP("TestRunInvestigator", instructions="""
This MCP server provides tools for investigating test runs.
Each time user asks a question, get instructions for it by invoking get_investigation_instructions.
              """)

# Initialize RAG system
try:
    rag_system = create_rag_system()
except RAGSystemError as e:
    print(f"Warning: RAG system initialization failed: {e}")
    rag_system = None

# Initialize VictoriaLogs handler
victoria_logs_handler = VictoriaLogsHandler()

# Initialize TestRunInfo handler
test_run_info_handler = TestRunInfoHandler()

@mcp.tool()
def get_test_run_info(test_id: str) -> str:
    """
    Get comprehensive test run information from Argus SCT.
    This is typically the first step in investigating a test run and must be followed
    by getting instructions how to investigate fetched test method and nothing more 
    (e.g. investigate upgrade test, investigate longevity test etc.).
    Retrieves test run details including status, events summary, and log links.
    
    Args:
        test_id: UUID string identifying the test run
        
    Returns:
        JSON string containing test run information with log links
    """
    try:
        info = test_run_info_handler.get_test_run_info(test_id)
        
        return json.dumps({
            "status": "success",
            "test_id": test_id,
            "test_run_info": info
        }, indent=2)
        
    except ValueError as e:
        return f"Invalid test_id format: {e}"
    except TTestRunInfoError as e:
        return f"Error retrieving test run information: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@mcp.tool()
def get_investigation_instructions(user_query: str) -> str:
    """
    Get relevant investigation instructions based on a user query using RAG.
    
    This tool uses the RAG (Retrieval-Augmented Generation) system to find
    the most relevant instructions from the knowledge base based on the user's
    query about test failures or investigation needs.
    
    Args:
        user_query: The user's question or description of the issue they're investigating
        
    Returns:
        Relevant instructions for investigating the described issue, or generic
        instructions if no specific match is found
    """
    if not rag_system:
        return "RAG system is not available. Please check the system configuration."
    
    try:
        instructions = rag_system.get_instructions(user_query)
        return instructions
    except RAGSystemError as e:
        return f"Error retrieving instructions: {e}"


@mcp.tool()
def query_actions_log(
    run_id: str,
    start_time: str = None,
    end_time: str = None
) -> str:
    """
    Query actions.log entries for a specific test run.
    
    Retrieves action log entries with optional time range filtering.
    First checks if logs are already ingested for the run_id.
    
    Args:
        run_id: UUID string identifying the test run
        start_time: Optional ISO 8601 timestamp for range start (e.g., '2025-05-17T04:44:00Z')
        end_time: Optional ISO 8601 timestamp for range end
        
    Returns:
        JSON string containing action log entries or status information
    """
    try:
        results = victoria_logs_handler.query_actions_log(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time
        )
        
        if not results:
            return f"No action logs found for run_id '{run_id}'. Logs may not be ingested yet. Use ingest_logs endpoint to download and ingest logs first."
        
        # Format actions with limited fields using format strings to reduce tokens
        formatted_actions = []
        for action in results:
            # Extract only required fields: _time, source, _msg, _target, trace_id, metadata
            time_val = action.get('_time', '')
            source_val = action.get('source', '')
            msg_val = action.get('_msg', '')
            target_val = action.get('_target', action.get('target', ''))
            trace_id_val = action.get('trace_id', '')
            metadata_val = action.get('metadata', {})
            
            # Use format string to reduce token count
            formatted_action = f"T:{time_val}|S:{source_val}|M:{msg_val}"
            if target_val:
                formatted_action += f"|TG:{target_val}"
            if trace_id_val:
                formatted_action += f"|TR:{trace_id_val}"
            if metadata_val:
                formatted_action += f"|META:{json.dumps(metadata_val, separators=(',', ':'))}"
            
            formatted_actions.append(formatted_action)
        
        return json.dumps({
            "status": "success",
            "run_id": run_id,
            "count": len(results),
            "actions": formatted_actions
        }, indent=2)
        
    except ValueError as e:
        return f"Invalid parameters: {e}"
    except VictoriaLogsQueryError as e:
        return f"Query error: {e}"
    except VictoriaLogsError as e:
        return f"VictoriaLogs error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@mcp.tool()
def query_raw_events_log(
    run_id: str,
    event_id: str,
    start_time: str = None,
    end_time: str = None
) -> str:
    """
    Query raw_events.log for a specific event.
    
    Retrieves a specific event from the raw events log with optional time range filtering.
    
    Args:
        run_id: UUID string identifying the test run
        event_id: UUID string identifying the specific event
        start_time: Optional ISO 8601 timestamp for range start (e.g., '2025-05-17T04:44:00Z')
        end_time: Optional ISO 8601 timestamp for range end
        
    Returns:
        JSON string containing the event log entry or status information
    """
    try:
        result = victoria_logs_handler.query_raw_events_log(
            run_id=run_id,
            event_id=event_id,
            start_time=start_time,
            end_time=end_time
        )
        
        if not result:
            return f"Event '{event_id}' not found for run_id '{run_id}'. Logs may not be ingested yet or event may not exist. Use ingest_logs endpoint to download and ingest logs first."
        
        # Remove unwanted fields: _stream_id, _stream, stream, run_id
        filtered_event = {k: v for k, v in result.items() 
                         if k not in ['_stream_id', '_stream', 'stream', 'run_id']}
        
        return json.dumps({
            "status": "success",
            "run_id": run_id,
            "event_id": event_id,
            "event": filtered_event
        }, indent=2)
        
    except ValueError as e:
        return f"Invalid parameters: {e}"
    except VictoriaLogsQueryError as e:
        return f"Query error: {e}"
    except VictoriaLogsError as e:
        return f"VictoriaLogs error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@mcp.tool()
def ingest_logs(download_url: str, run_id: str) -> str:
    """
    Download and ingest log archives into VictoriaLogs.
    
    Downloads a tar.zst archive containing test run logs, unpacks it, and ingests
    both actions.log and raw_events.log files into VictoriaLogs using proper stream
    configuration. The ingestion runs in the background and can be monitored.
    
    Args:
        download_url: URL to download the tar.zst archive containing logs
        run_id: UUID string identifying the test run
        
    Returns:
        JSON string containing task information or Docker setup instructions
    """
    try:
        result = victoria_logs_handler.ingest_logs(download_url, run_id)
        
        # Check if result is a Docker command (VictoriaLogs not running)
        if result.startswith("docker run"):
            return json.dumps({
                "status": "victoria_logs_not_running",
                "message": "VictoriaLogs is not running. Please start VictoriaLogs first.",
                "docker_command": result,
                "instructions": "Run the provided Docker command to start VictoriaLogs, then try again."
            }, indent=2)
        
        # Result is a task ID
        return json.dumps({
            "status": "ingestion_started",
            "task_id": result,
            "run_id": run_id,
            "message": f"Log ingestion started for run {run_id}. Use check_ingestion_status with task_id to monitor progress."
        }, indent=2)
        
    except ValueError as e:
        return f"Invalid parameters: {e}"
    except VictoriaLogsError as e:
        return f"VictoriaLogs error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@mcp.tool()
def check_ingestion_status(task_id: str) -> str:
    """
    Check the status of a background log ingestion task.
    
    Args:
        task_id: UUID string identifying the ingestion task
        
    Returns:
        JSON string containing task status information
    """
    try:
        status = victoria_logs_handler.check_ingestion_status(task_id)
        
        return json.dumps({
            "status": "success",
            "task_status": status
        }, indent=2)
        
    except ValueError as e:
        return f"Task not found: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run()
