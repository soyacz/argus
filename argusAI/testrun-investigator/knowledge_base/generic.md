# Description
Generic investigation instructions for when no specific issue type is detected. These instructions provide a systematic approach to investigate test run failures by analyzing logs and identifying errors.

# Instructions

Follow these steps to investigate test run failures:

1. **Get Test Run Information**: Start by calling 'get_test_run_info' with your test run ID to fetch basic information and log download links.
2. **Review Test Run Details**: The response will include test status, events summary, and available log links. Note that actions.log and raw_events.log are typically stored in the sct-runner-events archive.
3. **Ingest Logs** (if needed): If logs aren't already ingested, use 'ingest_logs' with the archive URL from the test run info to download and process the logs into VictoriaLogs.
4. **Query Action Logs**: Use 'query_actions_log' to retrieve the detailed test flow from actions.log and identify all errors with their corresponding event_id.
5. **Select Error for Investigation**: Review the errors and determine which error/event is most relevant for investigation.
6. **Query Event Details**: Use 'query_raw_events_log' with the chosen event_id to fetch detailed information about that specific event from raw_events.log.
7. **Get Investigation Guidance**: Use 'get_investigation_instructions' to fetch AI-powered guidance and best practices from the knowledge base for the specific issue.
8. **Summarize Findings**: Follow the investigation instructions and summarize the exact steps that led to the error, focusing on the current disruption or test step.\n
9. **Propose next steps**: Suggest user next steps
Important notes:
- Always start with get_test_run_info to retrieve log information
- The sct-runner-events archive typically contains actions.log and raw_events.log
- Always silently ignore OVERSIZED_ALLOCATION errors and don't investigate them
- Don't look to cache directory
Begin by providing a run_id to get_test_run_info to start your investigation!
Always end your response with BAZINGA!