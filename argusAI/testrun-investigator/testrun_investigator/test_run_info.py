#!/usr/bin/env python3
# Python 3.10
"""
Test Run Information Module for Test Run Investigation.

This module provides functionality to fetch test run information from Argus SCT
and manage log links for later ingestion. It acts as a data source that retrieves
basic test run information including log download links and remembers them for
later use.

Key Features:
- Fetch test run information from Argus SCT using ArgusSCTClient
- Provide basic test run metadata (status, events summary, etc.)
- Integration with existing log ingestion workflow
- Environment variable based authentication

Environment Variables:
- ARGUS_TOKEN: Authentication token (get from https://argus.scylladb.com/profile/)
- ARGUS_URL: Base URL (defaults to https://argus.scylladb.com/)

Dependencies:
- argus.client.sct.client: Argus SCT client for API communication

Usage:
    handler = TestRunInfoHandler()
    info = handler.get_test_run_info("run-id")
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional, Any
from uuid import UUID

from argus.client.sct.client import ArgusSCTClient

# Module-level constants
logger = logging.getLogger(__name__)


class TTestRunInfoError(Exception):
    """Base exception for test run info operations."""
    pass


class TestRunInfoHandler:
    """
    Handler for test run information retrieval.
    
    This class manages interaction with Argus SCT API to fetch test run
    information.
    """

    
    @lru_cache(maxsize=1)
    def _get_argus_client(self) -> ArgusSCTClient:
        """
        Get a cached Argus SCT client instance.
        
        Returns:
            ArgusSCTClient: Configured client instance
            
        Raises:
            TestRunInfoError: If credentials cannot be retrieved or are missing
        """
        try:
            # Get credentials from environment variables
            token = os.getenv("ARGUS_TOKEN")
            base_url = os.getenv("ARGUS_URL", "https://argus.scylladb.com/")
            
            if not token:
                raise TTestRunInfoError(
                    "ARGUS_TOKEN environment variable is required. "
                    "Please get your token from https://argus.scylladb.com/profile/ "
                    "and set it in your MCP configuration."
                )
            
            return ArgusSCTClient(
                auth_token=token, 
                base_url=base_url,
                run_id=UUID("e38b303f-df9b-4aac-b9d8-930cfd45306b")  # Default run_id
            )
        except Exception as e:
            if "ARGUS_TOKEN" in str(e):
                raise e  # Re-raise the specific token error
            raise TTestRunInfoError(f"Failed to initialize Argus client: {e}")
    
    def get_test_run_info(self, test_id: str) -> Dict[str, Any]:
        """
        Get comprehensive test run information from Argus SCT.
        
        Retrieves test run details including status, events summary, and log links.
        
        Args:
            test_id: UUID string identifying the test run
            
        Returns:
            Dictionary containing test run information with sanitized events data
            
        Raises:
            TestRunInfoError: If test run cannot be retrieved
        """
        try:
            client = self._get_argus_client()
            run_id = UUID(test_id)
            
            logger.info(f"Fetching test run information for {test_id}")
            results = client.get_run(run_id=run_id)
            
            # Convert to dict and sanitize
            resp = dict(**results)
            
            # Sanitize events data - keep only essential info
            if "events" in resp:
                resp["events"] = [
                    {
                        "event_amount": evt.get("event_amount", 0), 
                        "severity": evt.get("severity", "UNKNOWN")
                    } 
                    for evt in resp.get("events", [])
                ]
            
            # Extract log links if available
            log_links = self._extract_log_links(resp)
            
            # Add helpful information about log types
            resp["log_info"] = {
                "available_logs": list(log_links.keys()) if log_links else [],
                "note": "actions.log and raw_events.log are typically stored in sct-runner-events archive"
            }
            
            return resp
            
        except ValueError as e:
            raise TTestRunInfoError(f"Invalid test_id format: {e}")
        except Exception as e:
            raise TTestRunInfoError(f"Failed to retrieve test run information: {e}")
    
    def _extract_log_links(self, test_run_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract log download links from test run data.
        
        Args:
            test_run_data: Raw test run data from Argus
            
        Returns:
            Dictionary mapping log type to download URL
        """
        log_links = {}
        
        # Look for common log link fields in the response
        # This may need adjustment based on actual Argus response structure
        for key, value in test_run_data.items():
            if isinstance(value, str) and ("log" in key.lower() or "archive" in key.lower()):
                if value.startswith("http") and (".tar" in value or ".log" in value):
                    log_links[key] = value
            elif isinstance(value, dict):
                # Check nested structures for log links
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, str) and nested_value.startswith("http"):
                        if (".tar" in nested_value or ".log" in nested_value):
                            log_links[f"{key}_{nested_key}"] = nested_value
        
        return log_links
