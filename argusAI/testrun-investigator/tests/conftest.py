"""
Pytest configuration and shared fixtures.

This file contains pytest configuration and fixtures that are shared
across multiple test modules.
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "test_docs"


@pytest.fixture
def isolated_temp_dir():
    """
    Create an isolated temporary directory for each test.
    
    This fixture ensures each test gets a clean temporary directory
    and automatically cleans up after the test completes.
    """
    temp_dir = tempfile.mkdtemp(prefix="testrun_investigator_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_documents():
    """
    Provide standard test documents for RAG testing.
    
    Returns a dictionary mapping filenames to document content.
    """
    return {
        "api_test.md": """# Description
Test document for API endpoint failures and troubleshooting.

# Instructions
1. Check API endpoint URL and HTTP method
2. Verify authentication headers and tokens
3. Test with curl or similar tool
4. Review server logs for errors
""",
        "database_test.md": """# Description
Database connection testing and troubleshooting procedures.

# Instructions
1. Verify database server is running
2. Check connection string configuration
3. Test database credentials
4. Review connection timeout settings
""",
        "ui_test.md": """# Description
UI component testing and element interaction troubleshooting.

# Instructions
1. Check if elements exist in DOM
2. Verify element selectors
3. Add explicit waits for dynamic content
4. Check browser console for errors
""",
        "network_test.md": """# Description
Network connectivity testing and troubleshooting guide.

# Instructions
1. Test basic network connectivity
2. Verify DNS resolution
3. Check proxy and firewall settings
4. Monitor network latency and packet loss
""",
    }


@pytest.fixture
def setup_test_docs(isolated_temp_dir, test_documents):
    """
    Set up test documents in an isolated directory.
    
    Creates test markdown files in the provided temporary directory
    and returns the directory path.
    """
    docs_dir = os.path.join(isolated_temp_dir, "knowledge_base")
    os.makedirs(docs_dir, exist_ok=True)
    
    for filename, content in test_documents.items():
        file_path = os.path.join(docs_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return docs_dir


@pytest.fixture
def mock_rag_environment(isolated_temp_dir):
    """
    Set up a complete mock RAG environment.
    
    Creates both docs and cache directories and returns their paths.
    """
    docs_dir = os.path.join(isolated_temp_dir, "docs")
    cache_dir = os.path.join(isolated_temp_dir, "cache")
    
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    
    return {
        "docs_dir": docs_dir,
        "cache_dir": cache_dir,
        "temp_dir": isolated_temp_dir
    }


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark tests in test_server.py as integration tests
        if "test_server" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark tests with "integration" in name as integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark all other tests as unit tests by default
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Environment setup for RAG testing
@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Set up test environment variables.
    
    This fixture runs automatically for all tests and ensures
    a clean test environment.
    """
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test-specific environment variables
    os.environ.pop('RAG_DIR', None)  # Remove RAG_DIR to use default
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
