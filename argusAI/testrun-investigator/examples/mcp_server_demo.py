#!/usr/bin/env python3
"""
MCP Server Demo for Test Run Investigator

This demo shows how to use the MCP server endpoints for Victoria logs integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testrun_investigator.server import (
    query_logs_by_stream, 
    query_actions_log,
    query_raw_events_log,
    ingest_logs,
    check_ingestion_status,
    get_investigation_instructions
)

def demo_mcp_server():
    """Demonstrate MCP server functionality."""
    
    print("=== Test Run Investigator MCP Server Demo ===\n")
    
    # 2. Demonstrate querying existing logs
    run_id = "0477f9f0-63ee-44ef-9d38-e5eeee8ed4aa"  # Existing run in cache
    
    print("2. Query action logs (limited to 2 entries):")
    result = query_logs_by_stream(run_id, "action", limit=2)
    print(result[:500] + "..." if len(result) > 500 else result)
    print("\n" + "="*60 + "\n")
    
    # 3. Query full actions log
    print("3. Query full actions log:")
    result = query_actions_log(run_id)
    print(f"Actions log contains {result.count('_time')} entries")
    print("Sample entry:")
    print(result[:400] + "..." if len(result) > 400 else result)
    print("\n" + "="*60 + "\n")
    
    # 4. Demonstrate RAG system
    print("4. Get investigation instructions:")
    instructions = get_investigation_instructions("Database connection failures in test runs")
    print(instructions[:300] + "..." if len(instructions) > 300 else instructions)
    print("\n" + "="*60 + "\n")
    
    # 5. Demo ingestion status checking (with non-existent task)
    print("5. Demo functionality with non-existent logs:")
    test_run_id = "test-run-12345"
    result = query_logs_by_stream(test_run_id, "action", limit=1)
    print(result)
    print("\n" + "="*60 + "\n")
    
    print("Demo completed! The MCP server provides:")
    print("✓ Victoria logs querying by stream, run_id, and date range")
    print("✓ Log ingestion from archives with progress tracking")
    print("✓ Intelligent detection of missing logs with user guidance") 
    print("✓ RAG-powered investigation instructions")
    print("✓ Full JSON responses for easy integration")

if __name__ == "__main__":
    demo_mcp_server()
