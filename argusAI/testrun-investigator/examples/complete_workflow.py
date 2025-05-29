#!/usr/bin/env python3
"""
Complete MCP Server Usage Example
Demonstrates the full workflow for investigating test runs using Victoria logs.
"""

import json
import uuid

def example_workflow():
    """Example workflow for test run investigation."""
    
    print("=== MCP Server Complete Workflow Example ===\n")
    
    # Import the MCP server functions
    from testrun_investigator.server import (
        query_logs_by_stream,
        query_actions_log,
        query_raw_events_log,
        ingest_logs,
        check_ingestion_status,
        get_investigation_instructions
    )
    
    
    # Step 2: Try to query logs for a new run (will fail - logs not ingested)
    new_run_id = str(uuid.uuid4())
    print(f"Step 2: Attempting to query logs for new run: {new_run_id}")
    result = query_logs_by_stream(new_run_id, "action", limit=5)
    print("Result:", result)
    print("\n" + "="*80 + "\n")
    
    # Step 3: Ingest logs for a new run (will show ingestion started)
    print("Step 3: Starting log ingestion for new run")
    archive_url = "https://example.com/test-logs.tar.zst"
    result = ingest_logs(archive_url, new_run_id)
    
    try:
        ingestion_data = json.loads(result)
        if ingestion_data.get("status") == "ingestion_started":
            task_id = ingestion_data["task_id"]
            print(f"✓ Ingestion started with task_id: {task_id}")
            
            # Step 4: Check ingestion status
            print(f"\nStep 4: Checking ingestion status for task {task_id}")
            status_result = check_ingestion_status(task_id)
            print("Status:", status_result)
        else:
            print("Ingestion result:", result)
    except json.JSONDecodeError:
        print("Ingestion result:", result)
    
    print("\n" + "="*80 + "\n")
    
    # Step 5: Query existing logs (from cache)
    existing_run_id = "0477f9f0-63ee-44ef-9d38-e5eeee8ed4aa"
    print(f"Step 5: Querying existing logs for run: {existing_run_id}")
    
    # Query actions with limit
    print("Querying action logs (limit 3):")
    result = query_logs_by_stream(existing_run_id, "action", limit=3)
    data = json.loads(result)
    print(f"Found {data['count']} action entries")
    
    # Query events with limit  
    print("Querying event logs (limit 2):")
    result = query_logs_by_stream(existing_run_id, "events", limit=2)
    data = json.loads(result)
    print(f"Found {data['count']} event entries")
    
    # Query full actions log
    print("Querying full actions log:")
    result = query_actions_log(existing_run_id)
    data = json.loads(result)
    print(f"Total actions in run: {data['count']}")
    
    print("\n" + "="*80 + "\n")
    
    # Step 6: Get investigation guidance
    print("Step 6: Getting AI investigation guidance")
    issues = [
        "database connection timeout",
        "API endpoint returning 500 errors", 
        "UI component not loading"
    ]
    
    for issue in issues:
        print(f"\nIssue: {issue}")
        guidance = get_investigation_instructions(issue)
        print(f"Guidance: {guidance[:100]}...")
    
    print("\n" + "="*80 + "\n")
    
    print("🎉 Complete workflow demonstrated!")
    print("\nKey capabilities shown:")
    print("✓ Automatic missing log detection with user guidance")
    print("✓ Log ingestion with background processing and status tracking")
    print("✓ Flexible log querying by stream, run_id, time range, and limits")
    print("✓ AI-powered investigation instructions via RAG")
    print("✓ Comprehensive error handling and validation")
    print("✓ JSON structured responses for easy integration")
    
    print(f"\nThe MCP server is ready to investigate test failures!")
    print("Use 'PYTHONPATH=. uv run python testrun_investigator/server.py' to start the server.")

if __name__ == "__main__":
    example_workflow()
