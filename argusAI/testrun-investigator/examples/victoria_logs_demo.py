#!/usr/bin/env python3
"""
Example usage of the VictoriaLogs integration module.

This script demonstrates how to use the victoria_logs module to:
1. Ingest logs from a test run archive using stream-based organization
2. Check ingestion status
3. Query action logs with stream filters and time filtering
4. Query specific events from raw events log using stream filters
5. Use the new query_logs_by_stream method for flexible querying

Note: This is a demonstration script. In a real scenario, you would
provide actual URLs and valid run/event IDs.

Stream Organization:
- Actions logs are stored in the 'action' stream
- Raw events logs are stored in the 'events' stream
- Stream filters provide optimized query performance
"""

import time
import uuid
from testrun_investigator.victoria_logs import VictoriaLogsHandler

def main():
    """Demonstrate VictoriaLogs functionality."""
    
    # Initialize the handler
    handler = VictoriaLogsHandler()
    
    # Example run ID and event ID (would be real UUIDs in practice)
    run_id = "407cb58b-ddfd-42b8-8cad-dc53e48b96f9"
    event_id = "520eb36a-91f2-4df3-ab07-31b2936ca84b"
    
    print("=== VictoriaLogs Integration Demo ===\n")
    
    # 1. Check if VictoriaLogs is running
    print("1. Checking VictoriaLogs status...")
    if not handler._check_victoria_logs():
        print("❌ VictoriaLogs is not running!")
        print("💡 To start VictoriaLogs, run:")
        print(f"   {handler._get_docker_command()}")
        print("\nDemo continuing with mock operations...\n")
    else:
        print("✅ VictoriaLogs is running and accessible!\n")
    
    # 2. Demonstrate log ingestion (would fail without actual URL/logs)
    print("2. Log Ingestion Example:")
    print(f"   Run ID: {run_id}")
    print("   Archive URL: https://cloudius-jenkins-test.s3.amazonaws.com/407cb58b-ddfd-42b8-8cad-dc53e48b96f9/20250517_050157/sct-runner-events-407cb58b.tar.zst")
    
    try:
        # This would normally start background ingestion
        task_id = handler.ingest_logs("https://cloudius-jenkins-test.s3.amazonaws.com/407cb58b-ddfd-42b8-8cad-dc53e48b96f9/20250517_050157/sct-runner-events-407cb58b.tar.zst", run_id)
        
        if task_id.startswith("docker"):
            print(f"   Result: {task_id}")
        else:
            print(f"   ✅ Ingestion started with task ID: {task_id}")
            
            # Check status multiple times to see ingestion progress
            for i in range(10):  # Wait up to 50 seconds
                status = handler.check_ingestion_status(task_id)
                print(f"   📊 Status check {i+1}: {status['status']}")
                if status['status'] in ['completed', 'failed']:
                    if status['error']:
                        print(f"   ❌ Error: {status['error']}")
                    break
                time.sleep(5)
            else:
                print("   ⏱️ Still running after 50 seconds...")
    
    except Exception as e:
        print(f"   ❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 3. Demonstrate querying actions log with stream filters
    print("3. Actions Log Query Example (using 'action' stream):")
    print(f"   Querying actions for run: {run_id}")
    print("   Time range: 2025-05-24T03:00:00Z to 2025-05-24T04:45:00Z")
    print("   Using stream filter: {stream=\"action\", run_id=\"...\"}")
    
    try:
        actions = handler.query_actions_log(
            run_id,
            start_time="2025-05-15T03:00:00Z",
            end_time="2025-05-24T04:45:00Z"
        )
        print(f"   📋 Found {len(actions)} action log entries")
        
        if actions:
            print("   Sample entry:")
            for key, value in list(actions[0].items())[:3]:
                print(f"     {key}: {value}")
    
    except Exception as e:
        print(f"   ❌ Query failed (expected without data): {e}")
    
    print()
    
    # 4. Demonstrate querying raw events log with stream filters
    print("4. Raw Events Log Query Example (using 'events' stream):")
    print(f"   Querying event: {event_id}")
    print(f"   For run: {run_id}")
    print("   Using stream filter: {stream=\"events\", run_id=\"...\"}")
    
    try:
        event = handler.query_raw_events_log(run_id, event_id)
        
        if event:
            print("   📝 Event found:")
            for key, value in list(event.items())[:3]:
                print(f"     {key}: {value}")
        else:
            print("   📭 No event found (expected without data)")
    
    except Exception as e:
        print(f"   ❌ Query failed (expected without data): {e}")
    
    print()
    
    # 5. Demonstrate new query_logs_by_stream method
    print("5. Stream-Based Query Examples:")
    print("   Using the new query_logs_by_stream method for flexible querying")
    
    try:
        # Query action stream with limit
        print("   • Querying 'action' stream with limit=10:")
        actions = handler.query_logs_by_stream(run_id, "action", limit=10)
        print(f"     📊 Found {len(actions)} action entries")
        
        # Query events stream with time range
        print("   • Querying 'events' stream with time range:")
        events = handler.query_logs_by_stream(
            run_id, 
            "events", 
            start_time="2025-05-24T03:00:00Z",
            end_time="2025-05-24T04:00:00Z"
        )
        print(f"     📊 Found {len(events)} event entries")
        
    except Exception as e:
        print(f"   ❌ Stream query failed (expected without data): {e}")
    
    print()
    
    # 6. Demonstrate convenience functions
    print("6. Using Convenience Functions:")
    print("   These functions provide a simpler interface:")
    
    from testrun_investigator.victoria_logs import (
        ingest_logs, 
        query_actions_log, 
        query_raw_events_log,
        query_logs_by_stream
    )
    
    try:
        # Using convenience functions with stream-based queries
        print("   • ingest_logs() - simplified ingestion with stream organization")
        print("   • query_actions_log() - query 'action' stream without handler")
        print("   • query_raw_events_log() - query 'events' stream without handler")
        print("   • query_logs_by_stream() - flexible stream-based queries")
        
        # Example of querying without time range using convenience functions
        actions = query_actions_log(run_id)
        print(f"   📊 Actions query returned {len(actions)} entries")
        
        # Example of stream-based query using convenience function
        events = query_logs_by_stream(run_id, "events", limit=5)
        print(f"   📊 Events stream query returned {len(events)} entries")
    
    except Exception as e:
        print(f"   ❌ Convenience function failed (expected): {e}")
    
    print("\n=== Demo Complete ===")
    print("\n📚 Key Features Demonstrated:")
    print("  ✓ VictoriaLogs health checking")
    print("  ✓ Stream-based log ingestion ('action' and 'events' streams)")
    print("  ✓ Background log ingestion with task tracking")
    print("  ✓ LogsQL queries with stream filters for optimal performance")
    print("  ✓ Time filtering and result limiting")
    print("  ✓ Stream-based log organization by run_id and stream type")
    print("  ✓ New query_logs_by_stream method for flexible querying")
    print("  ✓ Both class-based and convenience function APIs")
    print("  ✓ Proper error handling and validation")
    print("\n🎯 Stream Benefits:")
    print("  • Reduced disk space usage through better compression")
    print("  • Increased query performance with stream filters")
    print("  • Organized data separation (actions vs events)")
    print("  • Optimal resource usage for large datasets")


if __name__ == "__main__":
    main()
