"""
Local data manager for MiMinions.

Main interface for local file system data management with master index,
transaction logs, and hash-based storage.
"""

import getpass
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .storage import StorageBackend
from .index import MasterIndex, FileMetadata
from .transaction_log import TransactionLog, TransactionType
from .file_handlers import FileHandlerRegistry, FileHandler


class LocalDataManager:
    """
    Local data management system for MiMinions.
    
    Provides comprehensive local file system data management with:
    - Master index files for metadata tracking
    - Transaction logs for audit trails
    - Hash-based file storage for deduplication
    - Support for multiple file types
    """
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None, author: Optional[str] = None):
        """
        Initialize local data manager.
        
        Args:
            base_dir: Base directory for data storage (defaults to ~/.miminions)
            author: Default author name (defaults to current user)
        """
        # Setup directory structure
        if base_dir is None:
            home_dir = Path.home()
            base_dir = home_dir / ".miminions"
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup default author
        self.default_author = author or getpass.getuser()
        
        # Initialize components
        self.storage = StorageBackend(self.base_dir)
        self.index = MasterIndex(self.base_dir / "index")
        self.transaction_log = TransactionLog(self.base_dir / "logs")
        self.file_handlers = FileHandlerRegistry()
        
        # Log initialization
        from .transaction_log import TransactionRecord
        self.transaction_log._write_transaction_record(
            TransactionRecord(
                id=f"init_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.utcnow().isoformat(),
                transaction_type=TransactionType.CREATE_INDEX,
                author=self.default_author,
                details={"base_dir": str(self.base_dir)}
            )
        )
    
    def add_file(self, 
                 file_path: Union[str, Path],
                 name: Optional[str] = None,
                 description: str = "",
                 tags: Optional[List[str]] = None,
                 author: Optional[str] = None) -> str:
        """
        Add a file to the data management system.
        
        Args:
            file_path: Path to the file to add
            name: Custom name for the file (defaults to filename)
            description: Description of the file
            tags: List of tags for the file
            author: Author of the file (defaults to default author)
            
        Returns:
            File ID of the added file
            
        Raises:
            FileNotFoundError: If the source file doesn't exist
            ValueError: If file cannot be processed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Store file content and get hash
        try:
            file_hash = self.storage.store_file(file_path)
        except Exception as e:
            self.transaction_log.log_write(
                file_id="unknown",
                file_name=str(file_path),
                author=author or self.default_author,
                success=False,
                error_message=str(e)
            )
            raise ValueError(f"Failed to store file: {e}")
        
        # Get file handler and extract metadata
        handler = self.file_handlers.get_handler(file_path)
        if handler:
            try:
                extracted_metadata = handler.extract_metadata(file_path)
                file_type = handler.get_file_type()
                default_tags = handler.get_default_tags(file_path)
            except Exception as e:
                extracted_metadata = {"error": str(e)}
                file_type = "unknown"
                default_tags = []
        else:
            extracted_metadata = {}
            file_type = "binary"
            default_tags = ["binary"]
        
        # Combine tags
        all_tags = list(set((tags or []) + default_tags))
        
        # Create metadata
        metadata = FileMetadata(
            original_name=name or file_path.name,
            original_path=str(file_path.absolute()),
            file_hash=file_hash,
            file_type=file_type,
            size_bytes=file_path.stat().st_size,
            tags=all_tags,
            description=description,
            author=author or self.default_author
        )
        
        # Add to index
        file_id = self.index.add_file(metadata)
        
        # Log the operation
        self.transaction_log.log_write(
            file_id=file_id,
            file_hash=file_hash,
            file_name=metadata.original_name,
            author=metadata.author,
            details={
                "original_path": metadata.original_path,
                "file_type": file_type,
                "size_bytes": metadata.size_bytes,
                "tags": all_tags,
                "extracted_metadata": extracted_metadata
            }
        )
        
        return file_id
    
    def add_content(self,
                    content: Union[str, bytes],
                    name: str,
                    file_type: str = "text",
                    description: str = "",
                    tags: Optional[List[str]] = None,
                    author: Optional[str] = None,
                    encoding: str = "utf-8") -> str:
        """
        Add content directly to the data management system.
        
        Args:
            content: Content to store
            name: Name for the content
            file_type: Type of the content
            description: Description of the content
            tags: List of tags
            author: Author of the content
            encoding: Text encoding (for string content)
            
        Returns:
            File ID of the added content
        """
        # Store content and get hash
        try:
            file_hash = self.storage.store_content(content, encoding)
        except Exception as e:
            self.transaction_log.log_write(
                file_id="unknown",
                file_name=name,
                author=author or self.default_author,
                success=False,
                error_message=str(e)
            )
            raise ValueError(f"Failed to store content: {e}")
        
        # Calculate size
        if isinstance(content, str):
            size_bytes = len(content.encode(encoding))
        else:
            size_bytes = len(content)
        
        # Create metadata
        metadata = FileMetadata(
            original_name=name,
            original_path="",  # No original path for direct content
            file_hash=file_hash,
            file_type=file_type,
            size_bytes=size_bytes,
            tags=tags or [file_type],
            description=description,
            author=author or self.default_author
        )
        
        # Add to index
        file_id = self.index.add_file(metadata)
        
        # Log the operation
        self.transaction_log.log_write(
            file_id=file_id,
            file_hash=file_hash,
            file_name=name,
            author=metadata.author,
            details={
                "content_type": "direct",
                "file_type": file_type,
                "size_bytes": size_bytes,
                "encoding": encoding if isinstance(content, str) else "binary"
            }
        )
        
        return file_id
    
    def get_file(self, file_id: str, author: Optional[str] = None) -> Optional[FileMetadata]:
        """
        Get file metadata by ID.
        
        Args:
            file_id: File ID
            author: User requesting the file (for logging)
            
        Returns:
            File metadata or None if not found
        """
        metadata = self.index.get_file(file_id)
        
        if metadata:
            # Update access count
            metadata.increment_access()
            self.index.update_file(file_id, {
                "access_count": metadata.access_count,
                "last_accessed": metadata.last_accessed
            })
            
            # Log the read operation
            self.transaction_log.log_read(
                file_id=file_id,
                file_hash=metadata.file_hash,
                file_name=metadata.original_name,
                author=author or self.default_author
            )
        
        return metadata
    
    def get_content(self, file_id: str, author: Optional[str] = None, encoding: str = "utf-8") -> Optional[str]:
        """
        Get file content by ID.
        
        Args:
            file_id: File ID
            author: User requesting the content
            encoding: Text encoding to use
            
        Returns:
            File content as string or None if not found
        """
        metadata = self.get_file(file_id, author)
        if not metadata:
            return None
        
        return self.storage.retrieve_content(metadata.file_hash, encoding)
    
    def get_binary_content(self, file_id: str, author: Optional[str] = None) -> Optional[bytes]:
        """
        Get file content as bytes by ID.
        
        Args:
            file_id: File ID
            author: User requesting the content
            
        Returns:
            File content as bytes or None if not found
        """
        metadata = self.get_file(file_id, author)
        if not metadata:
            return None
        
        return self.storage.retrieve_binary_content(metadata.file_hash)
    
    def extract_file(self, file_id: str, destination: Union[str, Path], author: Optional[str] = None) -> bool:
        """
        Extract a file to a destination path.
        
        Args:
            file_id: File ID
            destination: Destination path
            author: User performing the extraction
            
        Returns:
            True if file was extracted successfully
        """
        metadata = self.get_file(file_id, author)
        if not metadata:
            return False
        
        success = self.storage.retrieve_file(metadata.file_hash, destination)
        
        if success:
            self.transaction_log.log_read(
                file_id=file_id,
                file_hash=metadata.file_hash,
                file_name=metadata.original_name,
                author=author or self.default_author,
                details={"action": "extract", "destination": str(destination)}
            )
        
        return success
    
    def update_metadata(self, file_id: str, updates: Dict[str, Any], author: Optional[str] = None) -> bool:
        """
        Update file metadata.
        
        Args:
            file_id: File ID
            updates: Dictionary of updates
            author: User performing the update
            
        Returns:
            True if metadata was updated successfully
        """
        success = self.index.update_file(file_id, updates)
        
        if success:
            metadata = self.index.get_file(file_id)
            self.transaction_log.log_update(
                file_id=file_id,
                file_hash=metadata.file_hash if metadata else None,
                file_name=metadata.original_name if metadata else None,
                author=author or self.default_author,
                details={"updates": updates}
            )
        
        return success
    
    def delete_file(self, file_id: str, author: Optional[str] = None, remove_storage: bool = True) -> bool:
        """
        Delete a file from the system.
        
        Args:
            file_id: File ID
            author: User performing the deletion
            remove_storage: Whether to remove the actual stored file
            
        Returns:
            True if file was deleted successfully
        """
        metadata = self.index.get_file(file_id)
        if not metadata:
            return False
        
        # Remove from index
        index_success = self.index.remove_file(file_id)
        
        # Optionally remove from storage
        storage_success = True
        if remove_storage and metadata.file_hash:
            storage_success = self.storage.delete_file(metadata.file_hash)
        
        success = index_success and storage_success
        
        # Log the operation
        self.transaction_log.log_delete(
            file_id=file_id,
            file_hash=metadata.file_hash,
            file_name=metadata.original_name,
            author=author or self.default_author,
            details={"remove_storage": remove_storage},
            success=success
        )
        
        return success
    
    def search_files(self, 
                     name_pattern: Optional[str] = None,
                     file_type: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     author: Optional[str] = None) -> List[FileMetadata]:
        """
        Search files by various criteria.
        
        Args:
            name_pattern: Pattern to match in filename
            file_type: File type to filter by
            tags: Tags to filter by (all must be present)
            author: Author to filter by
            
        Returns:
            List of matching file metadata
        """
        return self.index.search_files(name_pattern, file_type, tags, author)
    
    def list_files(self) -> List[FileMetadata]:
        """List all files in the system."""
        return self.index.list_all_files()
    
    def get_tags(self) -> List[str]:
        """Get all unique tags in the system."""
        return sorted(self.index.get_all_tags())
    
    def get_file_types(self) -> List[str]:
        """Get all file types in the system."""
        return sorted(self.index.get_file_types())
    
    def get_authors(self) -> List[str]:
        """Get all authors in the system."""
        return sorted(self.index.get_authors())
    
    def get_recent_activity(self, limit: int = 100) -> List:
        """Get recent activity from transaction log."""
        return self.transaction_log.get_recent_activity(limit)
    
    def get_file_history(self, file_id: str) -> List:
        """Get transaction history for a specific file."""
        return self.transaction_log.get_file_history(file_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dictionary with system statistics
        """
        index_stats = self.index.get_stats()
        storage_stats = self.storage.get_storage_stats()
        log_stats = self.transaction_log.get_log_stats()
        
        return {
            "base_directory": str(self.base_dir),
            "default_author": self.default_author,
            "index": index_stats,
            "storage": storage_stats,
            "transaction_log": log_stats,
            "supported_file_types": self.file_handlers.get_supported_extensions()
        }
    
    def backup_system(self, backup_path: Union[str, Path]) -> bool:
        """
        Create a backup of the entire data management system.
        
        Args:
            backup_path: Path where backup should be created
            
        Returns:
            True if backup was successful
        """
        backup_path = Path(backup_path)
        
        try:
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy entire base directory
            backup_data_dir = backup_path / "miminions_backup"
            if backup_data_dir.exists():
                shutil.rmtree(backup_data_dir)
            
            shutil.copytree(self.base_dir, backup_data_dir)
            
            # Create backup metadata
            backup_metadata = {
                "backup_created": datetime.utcnow().isoformat(),
                "source_directory": str(self.base_dir),
                "backup_directory": str(backup_data_dir),
                "stats": self.get_stats()
            }
            
            with open(backup_path / "backup_info.json", 'w') as f:
                import json
                json.dump(backup_metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def restore_from_backup(self, backup_path: Union[str, Path]) -> bool:
        """
        Restore system from a backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            True if restore was successful
        """
        backup_path = Path(backup_path)
        backup_data_dir = backup_path / "miminions_backup"
        
        if not backup_data_dir.exists():
            return False
        
        try:
            # Remove current directory
            if self.base_dir.exists():
                shutil.rmtree(self.base_dir)
            
            # Restore from backup
            shutil.copytree(backup_data_dir, self.base_dir)
            
            # Reinitialize components
            self.storage = StorageBackend(self.base_dir)
            self.index = MasterIndex(self.base_dir / "index")
            self.transaction_log = TransactionLog(self.base_dir / "logs")
            
            return True
            
        except Exception as e:
            print(f"Restore failed: {e}")
            return False