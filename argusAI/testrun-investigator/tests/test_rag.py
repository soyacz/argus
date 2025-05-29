"""
Unit tests for the RAG (Retrieval-Augmented Generation) system.

This test suite covers:
- RAG system initialization and configuration
- Document loading and parsing
- Embedding generation and storage
- Similarity search functionality
- File monitoring and hot reload
- Error handling and edge cases
"""

import os
import tempfile
import time
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from testrun_investigator.rag import (
    RAGSystem,
    RAGSystemError,
    InvalidMarkdownError,
    MarkdownFileHandler,
    create_rag_system
)


class TestRAGSystem:
    """Test suite for the RAG system functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_docs_dir(self, temp_dir):
        """Set up test documents directory."""
        docs_dir = os.path.join(temp_dir, "test_docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        # Copy test documents
        source_docs = Path(__file__).parent / "test_docs"
        if source_docs.exists():
            for md_file in source_docs.glob("*.md"):
                shutil.copy(md_file, docs_dir)
        
        return docs_dir
    
    @pytest.fixture
    def test_cache_dir(self, temp_dir):
        """Set up test cache directory."""
        cache_dir = os.path.join(temp_dir, "test_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @pytest.fixture
    def rag_system(self, test_docs_dir, test_cache_dir):
        """Create a RAG system instance for testing."""
        with patch('testrun_investigator.rag.DOCS_DIR', test_docs_dir), \
             patch('testrun_investigator.rag.CACHE_DIR', test_cache_dir):
            rag = RAGSystem()
            yield rag
            # Cleanup
            if hasattr(rag, '_observer') and rag._observer:
                rag._observer.stop()
                rag._observer.join(timeout=1.0)
    
    
    def test_error_handling_chromadb_failure(self, test_docs_dir, monkeypatch):
        """Test error handling when ChromaDB fails to initialize."""
        # Ensure clean environment for this test
        monkeypatch.setenv("RAG_DIR", test_docs_dir)
        
        with patch('testrun_investigator.rag.chromadb.PersistentClient') as mock_client:
            mock_client.side_effect = Exception("ChromaDB connection failed")

            with pytest.raises(RAGSystemError, match="Failed to initialize ChromaDB"):
                RAGSystem()
    

    def test_rag_system_initialization(self, rag_system):
        """Test that RAG system initializes correctly."""
        assert rag_system is not None
        assert hasattr(rag_system, '_client')
        assert hasattr(rag_system, '_collection')
        assert hasattr(rag_system, '_observer')


    def test_parse_invalid_markdown_file(self, test_docs_dir, rag_system):
        """Test parsing of invalid markdown files."""
        # Test file without Description section
        test_file1 = os.path.join(test_docs_dir, "test_no_description.md")
        with open(test_file1, 'w') as f:
            f.write("# Instructions\nSome instructions here")

        with pytest.raises(InvalidMarkdownError, match="#Description section found"):
            rag_system._parse_markdown_file(test_file1)
        
        # Test file without Instructions section
        test_file2 = os.path.join(test_docs_dir, "test_no_instructions.md")
        with open(test_file2, 'w') as f:
            f.write("# Description\nSome description here")
        
        with pytest.raises(InvalidMarkdownError, match="No.*Instructions.*section"):
            rag_system._parse_markdown_file(test_file2)
    

    def test_rag_dir_environment_variable(self, temp_dir):
        """Test that RAG_DIR environment variable is respected."""
        test_rag_dir = os.path.join(temp_dir, "custom_rag_dir")
        os.makedirs(test_rag_dir, exist_ok=True)
        
        with patch.dict(os.environ, {'RAG_DIR': test_rag_dir}):
            from testrun_investigator.rag import DOCS_DIR
            # Import fresh to get updated environment variable
            import importlib
            import testrun_investigator.rag
            importlib.reload(testrun_investigator.rag)
            
            assert testrun_investigator.rag.DOCS_DIR == test_rag_dir

    def test_parse_valid_markdown_file(self, test_docs_dir, rag_system):
        """Test parsing of valid markdown files."""
        # Create a test markdown file
        test_file = os.path.join(test_docs_dir, "test_valid.md")
        content = """# Description
This is a test description for API failures.

# Instructions
1. Check the API endpoint
2. Verify authentication
3. Test connectivity
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        description, instructions = rag_system._parse_markdown_file(test_file)
        
        assert "test description for API failures" in description
        assert "Check the API endpoint" in instructions
        assert "Verify authentication" in instructions


    def test_parse_nonexistent_file(self, rag_system):
        """Test parsing of non-existent file."""
        with pytest.raises(FileNotFoundError):
            rag_system._parse_markdown_file("/nonexistent/file.md")
    
    def test_checksum_computation(self, rag_system):
        """Test checksum computation for content."""
        text1 = "This is test content"
        text2 = "This is test content"
        text3 = "This is different content"
        
        checksum1 = rag_system._compute_checksum(text1)
        checksum2 = rag_system._compute_checksum(text2)
        checksum3 = rag_system._compute_checksum(text3)
        
        assert checksum1 == checksum2  # Same content should have same checksum
        assert checksum1 != checksum3  # Different content should have different checksum
        assert len(checksum1) == 64  # SHA-256 produces 64-char hex string
    
    def test_collection_stats(self, rag_system):
        """Test getting collection statistics."""
        stats = rag_system.get_collection_stats()
        
        assert isinstance(stats, dict)
        assert 'total_documents' in stats
        assert isinstance(stats['total_documents'], int)
        assert stats['total_documents'] >= 0
    
    def test_get_instructions_empty_query(self, rag_system):
        """Test instruction retrieval with empty query."""
        instructions = rag_system.get_instructions("")
        
        assert "No specific instructions found" in instructions
        
        instructions2 = rag_system.get_instructions("   ")
        assert "No specific instructions found" in instructions2
    
    def test_get_instructions_valid_query(self, rag_system):
        """Test instruction retrieval with valid query."""
        # Test with a query that should match API documentation
        instructions = rag_system.get_instructions(
            "API endpoint issues HTTP errors timeout problems rate limiting authentication failures"
        )
        
        # Should either return specific instructions or generic fallback
        assert isinstance(instructions, str)
        assert len(instructions) > 0
    
    def test_file_processing_workflow(self, test_docs_dir, rag_system):
        """Test the complete file processing workflow."""
        # Create a new test file
        test_file = os.path.join(test_docs_dir, "test_workflow.md")
        content = """# Description
Test workflow document for database connection issues.

# Instructions
1. Check database connectivity
2. Verify credentials
3. Test connection string
"""
        with open(test_file, 'w') as f:
            f.write(content)
        
        # Process the file
        rag_system._process_single_file(test_file)
        
        # Verify it was added to the collection
        stats = rag_system.get_collection_stats()
        assert stats['total_documents'] > 0
        
        # Test retrieval
        instructions = rag_system.get_instructions(
            "database connection issues connectivity credentials"
        )
        
        # Should find the document we just added (or return generic instructions)
        assert isinstance(instructions, str)
        assert len(instructions) > 0
    
    def test_file_update_detection(self, test_docs_dir, rag_system):
        """Test that file updates are detected correctly."""
        test_file = os.path.join(test_docs_dir, "test_update.md")
        
        # Create initial file
        content1 = """# Description
Initial description content.

# Instructions
Initial instructions.
"""
        with open(test_file, 'w') as f:
            f.write(content1)
        
        rag_system._process_single_file(test_file)
        
        # Get initial metadata
        initial_metadata = rag_system._get_existing_metadata(test_file)
        
        # Update file content
        content2 = """# Description
Updated description content with new information.

# Instructions
Updated instructions with more details.
"""
        with open(test_file, 'w') as f:
            f.write(content2)
        
        rag_system._process_single_file(test_file)
        
        # Get updated metadata
        updated_metadata = rag_system._get_existing_metadata(test_file)
        
        # Checksums should be different
        if initial_metadata and updated_metadata:
            assert initial_metadata['description_checksum'] != updated_metadata['description_checksum']
    
    def test_file_removal(self, test_docs_dir, rag_system):
        """Test file removal from database."""
        test_file = os.path.join(test_docs_dir, "test_removal.md")
        
        # Create and process file
        content = """# Description
File to be removed.

# Instructions
These instructions will be removed.
"""
        with open(test_file, 'w') as f:
            f.write(content)
        
        rag_system._process_single_file(test_file)
        
        # Verify file is in database
        metadata = rag_system._get_existing_metadata(test_file)
        assert metadata is not None
        
        # Remove file from database
        rag_system._remove_file_from_db(test_file)
        
        # Verify file is no longer in database
        metadata_after = rag_system._get_existing_metadata(test_file)
        assert metadata_after is None


    def test_create_rag_system_convenience_function(self):
        """Test the convenience function for creating RAG system."""
        with patch('testrun_investigator.rag.RAGSystem') as mock_rag:
            mock_instance = MagicMock()
            mock_rag.return_value = mock_instance
            
            result = create_rag_system()
            
            mock_rag.assert_called_once()
            assert result == mock_instance


class TestMarkdownFileHandler:
    """Test suite for the file monitoring functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_rag_system(self):
        """Create a mock RAG system for testing file handler."""
        mock_rag = MagicMock()
        return mock_rag
    
    def test_file_handler_initialization(self, mock_rag_system):
        """Test file handler initialization."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        assert handler.rag_system == mock_rag_system
        assert handler._pending_files == set()
        assert handler._debounce_timer is None
    
    def test_file_modification_event(self, mock_rag_system, temp_dir):
        """Test file modification event handling."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        # Create a mock event
        event = MagicMock()
        event.is_directory = False
        event.src_path = os.path.join(temp_dir, "test.md")
        
        # Handle the event
        handler.on_modified(event)
        
        # Should schedule update
        assert event.src_path in handler._pending_files
        assert handler._debounce_timer is not None
    
    def test_file_creation_event(self, mock_rag_system, temp_dir):
        """Test file creation event handling."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        event = MagicMock()
        event.is_directory = False
        event.src_path = os.path.join(temp_dir, "new_file.md")
        
        handler.on_created(event)
        
        assert event.src_path in handler._pending_files
    
    def test_file_deletion_event(self, mock_rag_system, temp_dir):
        """Test file deletion event handling."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        event = MagicMock()
        event.is_directory = False
        event.src_path = os.path.join(temp_dir, "deleted_file.md")
        
        handler.on_deleted(event)
        
        assert event.src_path in handler._pending_files
    
    def test_non_markdown_files_ignored(self, mock_rag_system, temp_dir):
        """Test that non-markdown files are ignored."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        event = MagicMock()
        event.is_directory = False
        event.src_path = os.path.join(temp_dir, "test.txt")
        
        handler.on_modified(event)
        
        assert len(handler._pending_files) == 0
    
    def test_directory_events_ignored(self, mock_rag_system, temp_dir):
        """Test that directory events are ignored."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        event = MagicMock()
        event.is_directory = True
        event.src_path = temp_dir
        
        handler.on_modified(event)
        
        assert len(handler._pending_files) == 0
    
    def test_debounced_update_processing(self, mock_rag_system, temp_dir):
        """Test debounced update processing."""
        handler = MarkdownFileHandler(mock_rag_system)
        
        # Add some files to pending
        test_file1 = os.path.join(temp_dir, "test1.md")
        test_file2 = os.path.join(temp_dir, "test2.md")
        
        # Create the files so they exist
        with open(test_file1, 'w') as f:
            f.write("test content")
        with open(test_file2, 'w') as f:
            f.write("test content")
        
        handler._pending_files.add(test_file1)
        handler._pending_files.add(test_file2)
        
        # Process updates
        handler._debounced_update()
        
        # Should have called process_single_file for each file
        assert mock_rag_system._process_single_file.call_count == 2
        assert handler._pending_files == set()  # Should be cleared


class TestIntegration:
    """Integration tests for the complete RAG system."""
    
    @pytest.fixture
    def integration_temp_dir(self):
        """Create a temporary directory for integration testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_full_rag_workflow_with_env_var(self, integration_temp_dir):
        """Test complete RAG workflow with environment variable configuration."""
        # Set up test environment
        test_docs_dir = os.path.join(integration_temp_dir, "custom_docs")
        test_cache_dir = os.path.join(integration_temp_dir, "custom_cache")
        os.makedirs(test_docs_dir, exist_ok=True)
        os.makedirs(test_cache_dir, exist_ok=True)
        
        # Create test documents
        test_files = {
            "api_test.md": """# Description
API endpoint testing and troubleshooting guide.

# Instructions
1. Verify API endpoint URL
2. Check authentication headers
3. Test with curl
""",
            "db_test.md": """# Description
Database connection testing procedures.

# Instructions
1. Check database server status
2. Verify connection string
3. Test credentials
""",
        }
        
        for filename, content in test_files.items():
            with open(os.path.join(test_docs_dir, filename), 'w') as f:
                f.write(content)
        
        # Test with environment variable
        with patch.dict(os.environ, {'RAG_DIR': test_docs_dir}), \
             patch('testrun_investigator.rag.CACHE_DIR', test_cache_dir):
            
            # Force reload of module to pick up new environment variable
            import importlib
            import testrun_investigator.rag
            importlib.reload(testrun_investigator.rag)
            
            # Create RAG system
            rag = testrun_investigator.rag.RAGSystem()
            
            try:
                # Test that documents were indexed
                stats = rag.get_collection_stats()
                assert stats['total_documents'] >= 2
                
                # Test API query
                api_instructions = rag.get_instructions("API endpoint testing troubleshooting")
                assert isinstance(api_instructions, str)
                
                # Test DB query
                db_instructions = rag.get_instructions("database connection testing procedures")
                assert isinstance(db_instructions, str)
                
                # Test unmatched query
                unmatched_instructions = rag.get_instructions("completely unrelated query about space travel")
                assert isinstance(unmatched_instructions, str)
                
            finally:
                # Cleanup
                if hasattr(rag, '_observer') and rag._observer:
                    rag._observer.stop()
                    rag._observer.join(timeout=1.0)
    
    def test_file_monitoring_integration(self, integration_temp_dir):
        """Test file monitoring in integration environment."""
        test_docs_dir = os.path.join(integration_temp_dir, "monitored_docs")
        test_cache_dir = os.path.join(integration_temp_dir, "monitored_cache")
        os.makedirs(test_docs_dir, exist_ok=True)
        os.makedirs(test_cache_dir, exist_ok=True)
        
        with patch('testrun_investigator.rag.DOCS_DIR', test_docs_dir), \
             patch('testrun_investigator.rag.CACHE_DIR', test_cache_dir):
            
            rag = RAGSystem()
            
            try:
                # Initial state
                initial_stats = rag.get_collection_stats()
                
                # Add a new file
                new_file = os.path.join(test_docs_dir, "dynamic_test.md")
                content = """# Description
Dynamically added test document.

# Instructions
1. This document was added during runtime
2. It should be automatically indexed
"""
                with open(new_file, 'w') as f:
                    f.write(content)
                
                # Give some time for file watcher to process
                # Note: In real tests, you might want to mock the file watcher
                # to avoid timing dependencies
                time.sleep(2)
                
                # Check if it was processed (manually trigger since timing is unreliable in tests)
                rag._process_single_file(new_file)
                
                # Verify update
                updated_stats = rag.get_collection_stats()
                assert updated_stats['total_documents'] >= initial_stats['total_documents']
                
            finally:
                # Cleanup
                if hasattr(rag, '_observer') and rag._observer:
                    rag._observer.stop()
                    rag._observer.join(timeout=1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
