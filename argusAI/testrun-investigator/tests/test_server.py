"""
Unit tests for the MCP server integration with RAG system.

This test suite covers:
- MCP server tool functionality
- RAG system integration
- Error handling for server endpoints
- Tool parameter validation
"""

import os
import tempfile
import shutil
from unittest.mock import patch
import pytest

from testrun_investigator.server import (
    get_investigation_instructions,
    rag_system
)
from testrun_investigator.rag import RAGSystemError


class TestMCPServerTools:
    """Test suite for MCP server tool functionality."""
    
    def test_get_investigation_instructions_with_rag(self):
        """Test investigation instructions tool with working RAG system."""
        query = "API endpoint timeout issues"
        
        with patch('testrun_investigator.server.rag_system') as mock_rag:
            mock_rag.get_instructions.return_value = "Mock instructions for API issues"
            
            result = get_investigation_instructions(query)
            
            mock_rag.get_instructions.assert_called_once_with(query)
            assert result == "Mock instructions for API issues"
    
    def test_get_investigation_instructions_without_rag(self):
        """Test investigation instructions tool when RAG system is unavailable."""
        with patch('testrun_investigator.server.rag_system', None):
            result = get_investigation_instructions("test query")
            
            assert "RAG system is not available" in result
    
    def test_get_investigation_instructions_with_rag_error(self):
        """Test investigation instructions tool when RAG system raises error."""
        with patch('testrun_investigator.server.rag_system') as mock_rag:
            mock_rag.get_instructions.side_effect = RAGSystemError("Test error")
            
            result = get_investigation_instructions("test query")
            
            assert "Error retrieving instructions: Test error" in result


class TestMCPServerIntegration:
    """Integration tests for MCP server with real RAG system."""
    
    @pytest.fixture
    def temp_test_environment(self):
        """Set up temporary test environment for integration tests."""
        temp_dir = tempfile.mkdtemp()
        docs_dir = os.path.join(temp_dir, "test_docs")
        cache_dir = os.path.join(temp_dir, "test_cache")
        
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Create test documentation
        test_doc = os.path.join(docs_dir, "integration_test.md")
        with open(test_doc, 'w') as f:
            f.write("""# Description
Integration test document for MCP server testing with API endpoint failures.

# Instructions
1. Check API endpoint configuration
2. Verify authentication credentials
3. Test network connectivity
4. Review error logs
""")
        
        yield {
            'temp_dir': temp_dir,
            'docs_dir': docs_dir,
            'cache_dir': cache_dir
        }
        
        shutil.rmtree(temp_dir)
    
    def test_full_mcp_rag_integration(self, temp_test_environment):
        """Test full integration between MCP server tools and RAG system."""
        docs_dir = temp_test_environment['docs_dir']
        cache_dir = temp_test_environment['cache_dir']
        
        # Patch the RAG system directories
        with patch('testrun_investigator.rag.DOCS_DIR', docs_dir), \
             patch('testrun_investigator.rag.CACHE_DIR', cache_dir):
            
            # Force reimport to get new RAG system with test directories
            import importlib
            import testrun_investigator.server
            importlib.reload(testrun_investigator.server)
            
            try:
                # Test instruction retrieval with relevant query
                instruction_result = testrun_investigator.server.get_investigation_instructions(
                    "API endpoint failures authentication credentials network connectivity"
                )
                
                # Should return either specific instructions or generic fallback
                assert isinstance(instruction_result, str)
                assert len(instruction_result) > 0
                
                # Test with empty query
                empty_result = testrun_investigator.server.get_investigation_instructions("")
                assert "No specific instructions found" in empty_result
                
                # Test with very specific query that should match
                specific_result = testrun_investigator.server.get_investigation_instructions(
                    "Integration test document MCP server testing API endpoint failures"
                )
                assert isinstance(specific_result, str)
                
            finally:
                # Cleanup RAG system
                if hasattr(testrun_investigator.server, 'rag_system') and \
                   testrun_investigator.server.rag_system and \
                   hasattr(testrun_investigator.server.rag_system, '_observer'):
                    observer = testrun_investigator.server.rag_system._observer
                    if observer:
                        observer.stop()
                        observer.join(timeout=1.0)

    def test_mcp_server_initialization_failure_handling(self):
        """Test MCP server behavior when RAG system initialization fails."""
        with patch('testrun_investigator.server.rag_system', None):
            # Test that functions handle missing RAG system gracefully
            result = get_investigation_instructions("test query")
            assert result == "RAG system is not available. Please check the system configuration."


class TestMCPServerRobustness:
    """Test suite for MCP server robustness and error handling."""
    
    def test_investigation_instructions_with_various_inputs(self):
        """Test investigation instructions tool with various input types."""
        test_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a" * 1000,  # Very long string
            "Special chars: !@#$%^&*()",  # Special characters
            "Unicode: 测试 🚀 émoji",  # Unicode characters
            None,  # This should be handled by the MCP framework
        ]
        
        with patch('testrun_investigator.server.rag_system') as mock_rag:
            mock_rag.get_instructions.return_value = "Mock response"
            
            for test_input in test_cases[:-1]:  # Exclude None as it's framework-handled
                result = get_investigation_instructions(test_input)
                assert isinstance(result, str)
                assert len(result) > 0
    
    def test_concurrent_rag_requests(self):
        """Test behavior under concurrent requests (simulated)."""
        import threading
        import time
        
        results = []
        errors = []
        
        # Set up mock outside of threads
        with patch('testrun_investigator.server.rag_system') as mock_rag:
            def make_request(query_id):
                try:
                    # Simulate some processing time
                    time.sleep(0.1)
                    mock_rag.get_instructions.return_value = f"Response for query {query_id}"
                    
                    result = get_investigation_instructions(f"Test query {query_id}")
                    results.append(result)
                except Exception as e:
                    errors.append(e)
            
            # Create multiple threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 10
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_memory_usage_with_large_responses(self):
        """Test memory handling with large RAG responses."""
        large_response = "Large response content. " * 10000  # ~250KB response
        
        with patch('testrun_investigator.server.rag_system') as mock_rag:
            mock_rag.get_instructions.return_value = large_response
            
            result = get_investigation_instructions("Large response test")
            
            assert result == large_response
            assert len(result) > 200000  # Verify it's actually large


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
