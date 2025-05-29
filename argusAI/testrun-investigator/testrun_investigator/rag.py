#!/usr/bin/env python3
# Python version: 3.10

"""
RAG (Retrieval-Augmented Generation) Module for AI-Enhanced Test Run Investigation

This module implements a comprehensive RAG system that indexes markdown files from
the ./knowledge_base directory, creates embeddings for description sections using ChromaDB's
default ONNX-based embedding model, and provides intelligent instruction retrieval
based on user queries.

Key Features:
- Automatic indexing of markdown files with #Description and #Instructions sections
- Persistent vector storage using ChromaDB in ./cache directory
- Real-time file monitoring and hot reload capabilities
- Similarity-based instruction retrieval with configurable threshold
- Comprehensive error handling and logging

Usage:
    from testrun_investigator.rag import RAGSystem
    
    rag = RAGSystem()
    instructions = rag.get_instructions("What caused the test failure?")

Dependencies:
    - chromadb: Vector database with default ONNX embedding model
    - watchdog: File system monitoring
    - hashlib: Checksum computation (standard library)
    - logging: Error and event logging (standard library)
"""

import hashlib
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


# Module-level constants
DOCS_DIR = os.getenv("RAG_DIR", "./knowledge_base")
CACHE_DIR = "./cache"
COLLECTION_NAME = "instructions"
SIMILARITY_THRESHOLD = 0.3
GENERIC_INSTRUCTION_FILE = os.path.join(DOCS_DIR, "generic.md")
FALLBACK_INSTRUCTION = (
    "No specific instructions found. Proceed with standard query processing "
    "using your default knowledge and reasoning capabilities."
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvalidMarkdownError(Exception):
    """Custom exception for invalid markdown file structure."""
    pass


class RAGSystemError(Exception):
    """Custom exception for RAG system-specific errors."""
    pass


class MarkdownFileHandler(FileSystemEventHandler):
    """
    File system event handler for monitoring markdown files in the docs directory.
    
    Handles file creation, modification, and deletion events to maintain
    up-to-date embeddings in the ChromaDB collection.
    """
    
    def __init__(self, rag_system: 'RAGSystem') -> None:
        """
        Initialize the file handler.
        
        Args:
            rag_system: Reference to the RAGSystem instance for updating embeddings
        """
        self.rag_system = rag_system
        self._debounce_timer: Optional[threading.Timer] = None
        self._pending_files: set = set()
        
    def _debounced_update(self) -> None:
        """Process pending file updates after debounce delay."""
        if self._pending_files:
            files_to_process = self._pending_files.copy()
            self._pending_files.clear()
            
            for file_path in files_to_process:
                try:
                    if os.path.exists(file_path):
                        self.rag_system._process_single_file(file_path)
                    else:
                        self.rag_system._remove_file_from_db(file_path)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
    
    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._schedule_update(event.src_path)
    
    def on_created(self, event) -> None:
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._schedule_update(event.src_path)
    
    def on_deleted(self, event) -> None:
        """Handle file deletion events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._schedule_update(event.src_path)
    
    def _schedule_update(self, file_path: str) -> None:
        """
        Schedule a debounced update for the given file.
        
        Args:
            file_path: Path to the file that needs updating
        """
        self._pending_files.add(file_path)
        
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(1.0, self._debounced_update)
        self._debounce_timer.start()


class RAGSystem:
    """
    Retrieval-Augmented Generation system for intelligent instruction retrieval.
    
    This class manages the complete RAG pipeline including file indexing,
    embedding generation and storage, file monitoring, and similarity-based
    instruction retrieval.
    
    Attributes:
        _client: ChromaDB persistent client for vector storage
        _collection: ChromaDB collection for instruction embeddings
        _observer: File system observer for hot reload functionality
        _file_handler: Event handler for file system changes
    """
    
    def __init__(self) -> None:
        """
        Initialize the RAG system.
        
        Sets up ChromaDB client, creates necessary directories, loads existing
        data, indexes documents, and starts file monitoring.
        
        Raises:
            RAGSystemError: If initialization fails
        """
        try:
            self._setup_directories()
            self._initialize_chromadb()
            self._index_knowledge_base()
            self._start_file_watcher()
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            raise RAGSystemError(f"RAG system initialization failed: {e}")
    
    def _setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        Path(DOCS_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    def _initialize_chromadb(self) -> None:
        """
        Initialize ChromaDB client and collection.
        
        Raises:
            RAGSystemError: If ChromaDB initialization fails
        """
        try:
            self._client = chromadb.PersistentClient(
                path=CACHE_DIR,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Test run investigation instructions"}
            )
            
            logger.info(f"ChromaDB initialized with {self._collection.count()} existing embeddings")
            
        except Exception as e:
            raise RAGSystemError(f"Failed to initialize ChromaDB: {e}")
    
    def _parse_markdown_file(self, file_path: str) -> Tuple[str, str]:
        """
        Parse a markdown file to extract Description and Instructions sections.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Tuple of (description, instructions) content
            
        Raises:
            InvalidMarkdownError: If required sections are missing
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Markdown file not found: {file_path}")
        except Exception as e:
            raise InvalidMarkdownError(f"Error reading file {file_path}: {e}")
        
        # Extract Description section
        description_match = re.search(
            r'#\s*Description\s*\n(.*?)(?=\n#|\Z)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        # Extract Instructions section
        instructions_match = re.search(
            r'#\s*Instructions\s*\n(.*?)(?=\n#|\Z)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if not description_match:
            raise InvalidMarkdownError(
                f"No #Description section found in {file_path}"
            )
        
        if not instructions_match:
            raise InvalidMarkdownError(
                f"No #Instructions section found in {file_path}"
            )
        
        description = description_match.group(1).strip()
        instructions = instructions_match.group(1).strip()
        
        if not description:
            raise InvalidMarkdownError(
                f"Empty #Description section in {file_path}"
            )
        
        if not instructions:
            raise InvalidMarkdownError(
                f"Empty #Instructions section in {file_path}"
            )
        
        return description, instructions
    
    def _compute_checksum(self, text: str) -> str:
        """
        Compute SHA-256 checksum for given text.
        
        Args:
            text: Text content to compute checksum for
            
        Returns:
            Hexadecimal string representation of the checksum
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_existing_metadata(self, file_path: str) -> Optional[Dict]:
        """
        Get existing metadata for a file from ChromaDB.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Metadata dictionary if found, None otherwise
        """
        try:
            results = self._collection.get(
                where={"file_path": file_path},
                include=["metadatas"]
            )
            
            if results['metadatas']:
                return results['metadatas'][0]
            
        except Exception as e:
            logger.warning(f"Error retrieving metadata for {file_path}: {e}")
        
        return None
    
    def _process_single_file(self, file_path: str) -> None:
        """
        Process a single markdown file for embedding generation/update.
        
        Args:
            file_path: Path to the markdown file to process
        """
        try:
            description, instructions = self._parse_markdown_file(file_path)
            current_checksum = self._compute_checksum(description)
            
            # Check if file needs updating
            existing_metadata = self._get_existing_metadata(file_path)
            
            if (existing_metadata and 
                existing_metadata.get('description_checksum') == current_checksum):
                logger.debug(f"File {file_path} is up to date, skipping")
                return
            
            # Remove existing embedding if it exists
            if existing_metadata:
                self._remove_file_from_db(file_path)
            
            # Add new embedding
            doc_id = f"doc_{hashlib.md5(file_path.encode()).hexdigest()}"
            
            self._collection.add(
                documents=[description],
                metadatas=[{
                    "file_path": file_path,
                    "description_checksum": current_checksum
                }],
                ids=[doc_id]
            )
            
            logger.info(f"Updated embedding for {file_path}")
            
        except InvalidMarkdownError as e:
            logger.warning(f"Skipping invalid markdown file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def _remove_file_from_db(self, file_path: str) -> None:
        """
        Remove a file's embedding from ChromaDB.
        
        Args:
            file_path: Path to the file whose embedding should be removed
        """
        try:
            results = self._collection.get(
                where={"file_path": file_path},
                include=["metadatas"]
            )
            
            if results['ids']:
                self._collection.delete(ids=results['ids'])
                logger.info(f"Removed embedding for deleted file: {file_path}")
                
        except Exception as e:
            logger.error(f"Error removing file {file_path} from database: {e}")
    
    def _index_knowledge_base(self) -> None:
        """
        Index all markdown files in the knowledge_base directory.
        
        Scans the knowledge_base directory recursively for .md files and processes
        each one to generate or update embeddings.
        """
        docs_path = Path(DOCS_DIR)
        
        if not docs_path.exists():
            logger.warning(f"knowledge_base directory {DOCS_DIR} does not exist")
            return
        
        # Get all existing file paths from ChromaDB
        try:
            existing_results = self._collection.get(include=["metadatas"])
            existing_files = {
                metadata['file_path'] 
                for metadata in existing_results['metadatas']
            }
        except Exception as e:
            logger.error(f"Error retrieving existing files from database: {e}")
            existing_files = set()
        
        # Find all current markdown files
        current_files = set()
        for md_file in docs_path.rglob("*.md"):
            file_path = str(md_file)
            current_files.add(file_path)
            self._process_single_file(file_path)
        
        # Remove embeddings for deleted files
        deleted_files = existing_files - current_files
        for deleted_file in deleted_files:
            self._remove_file_from_db(deleted_file)
        
        logger.info(f"Indexed {len(current_files)} markdown files")
    
    def _start_file_watcher(self) -> None:
        """
        Start file system monitoring for hot reload functionality.
        
        Sets up a watchdog observer to monitor the docs directory for
        file changes and automatically update embeddings.
        """
        if not Path(DOCS_DIR).exists():
            logger.warning(f"Cannot start file watcher: {DOCS_DIR} does not exist")
            return
        
        try:
            self._file_handler = MarkdownFileHandler(self)
            self._observer = Observer()
            self._observer.schedule(
                self._file_handler,
                DOCS_DIR,
                recursive=True
            )
            self._observer.start()
            logger.info(f"Started file watcher for {DOCS_DIR}")
            
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
    
    def _read_instructions_from_file(self, file_path: str) -> str:
        """
        Read the Instructions section from a markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Content of the Instructions section
            
        Raises:
            InvalidMarkdownError: If Instructions section cannot be read
        """
        try:
            _, instructions = self._parse_markdown_file(file_path)
            return instructions
        except Exception as e:
            logger.error(f"Error reading instructions from {file_path}: {e}")
            raise InvalidMarkdownError(f"Cannot read instructions from {file_path}: {e}")
    
    def _load_generic_instructions(self) -> str:
        """
        Load generic investigation instructions from the generic.md file.
        
        Returns:
            Generic instructions content, or fallback text if file is not available
        """
        try:
            if os.path.exists(GENERIC_INSTRUCTION_FILE):
                _, instructions = self._parse_markdown_file(GENERIC_INSTRUCTION_FILE)
                return instructions
            else:
                logger.warning(f"Generic instructions file not found: {GENERIC_INSTRUCTION_FILE}")
                return FALLBACK_INSTRUCTION
        except Exception as e:
            logger.error(f"Error loading generic instructions: {e}")
            return FALLBACK_INSTRUCTION

    def get_instructions(self, user_prompt: str) -> str:
        """
        Retrieve the most relevant instructions based on a user prompt.
        
        This is the main endpoint for the RAG system. It must be called before
        processing any user query to retrieve context-specific instructions.
        The function uses ChromaDB's default ONNX-based embedding model to:
        
        1. Generate an embedding for the user prompt
        2. Query the vector database for the most similar description
        3. Return corresponding instructions if similarity >= 0.9
        4. Fall back to generic instructions if no match meets the threshold
        
        Args:
            user_prompt: The user's query or prompt text
            
        Returns:
            Instructions text from the most relevant markdown file, or
            generic instructions if no match meets the similarity threshold
            
        Raises:
            RAGSystemError: If the query process fails
        """
        if not user_prompt or not user_prompt.strip():
            logger.warning("Empty user prompt provided")
            return self._load_generic_instructions()
        
        try:
            # Query ChromaDB for similar descriptions
            results = self._collection.query(
                query_texts=[user_prompt.strip()],
                n_results=1,
                include=["metadatas", "distances"]
            )
            
            # Check if we have results
            if not results['metadatas'] or not results['metadatas'][0]:
                logger.info("No documents found in collection")
                return self._load_generic_instructions()
            
            # Get the best match
            metadata = results['metadatas'][0][0]
            distance = results['distances'][0][0]
            
            # Convert distance to similarity (ChromaDB uses cosine distance)
            similarity = 1.0 - distance
            
            logger.debug(f"Best match: {metadata['file_path']} (similarity: {similarity:.3f})")
            
            # Check similarity threshold
            if similarity >= SIMILARITY_THRESHOLD:
                file_path = metadata['file_path']
                try:
                    instructions = self._read_instructions_from_file(file_path)
                    logger.info(f"Retrieved instructions from {file_path}")
                    return instructions
                except InvalidMarkdownError as e:
                    logger.error(f"Error reading instructions: {e}")
                    return self._load_generic_instructions()
            else:
                logger.info(
                    f"Best match similarity {similarity:.3f} below threshold "
                    f"{SIMILARITY_THRESHOLD}, returning generic instructions"
                )
                return self._load_generic_instructions()
                
        except Exception as e:
            logger.error(f"Error during instruction retrieval: {e}")
            raise RAGSystemError(f"Failed to retrieve instructions: {e}")
    
    def get_collection_stats(self) -> Dict[str, int]:
        """
        Get statistics about the ChromaDB collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self._collection.count()
            return {"total_documents": count}
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"total_documents": 0}
    
    def __del__(self) -> None:
        """Cleanup resources when the RAG system is destroyed."""
        if hasattr(self, '_observer') and self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=1.0)
            except Exception as e:
                logger.error(f"Error stopping file observer: {e}")


# Convenience function for easy import and usage
def create_rag_system() -> RAGSystem:
    """
    Create and return a new RAGSystem instance.
    
    Returns:
        Initialized RAGSystem instance
        
    Raises:
        RAGSystemError: If initialization fails
    """
    return RAGSystem()


if __name__ == "__main__":
    # Example usage and testing
    rag = create_rag_system()
    
    # Print collection stats
    stats = rag.get_collection_stats()
    print(f"Collection contains {stats['total_documents']} documents")
    
    # Example query
    test_prompt = "What caused the test failure in the recent run?"
    instructions = rag.get_instructions(test_prompt)
    print(f"\nQuery: {test_prompt}")
    print(f"Instructions: {instructions}")
