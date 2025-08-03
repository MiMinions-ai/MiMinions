"""
Storage backend for hash-based file storage.

Manages the physical storage of files using SHA-256 hashes for file naming
and deduplication.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, BinaryIO, Union


class StorageBackend:
    """Hash-based storage backend for local data management."""
    
    def __init__(self, storage_root: Path):
        """
        Initialize storage backend.
        
        Args:
            storage_root: Root directory for storage
        """
        self.storage_root = Path(storage_root)
        self.data_dir = self.storage_root / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _calculate_hash(self, content: Union[bytes, str, BinaryIO]) -> str:
        """
        Calculate SHA-256 hash of content.
        
        Args:
            content: Content to hash (bytes, string, or file-like object)
            
        Returns:
            Hex digest of SHA-256 hash
        """
        hasher = hashlib.sha256()
        
        if isinstance(content, str):
            hasher.update(content.encode('utf-8'))
        elif isinstance(content, bytes):
            hasher.update(content)
        else:
            # File-like object
            for chunk in iter(lambda: content.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _get_storage_path(self, file_hash: str) -> Path:
        """
        Get storage path for a file hash.
        
        Uses 2-level directory structure: ab/cd/abcd1234...
        
        Args:
            file_hash: SHA-256 hash of file
            
        Returns:
            Path where file should be stored
        """
        # Create 2-level directory structure for better filesystem performance
        dir1 = file_hash[:2]
        dir2 = file_hash[2:4]
        
        storage_dir = self.data_dir / dir1 / dir2
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        return storage_dir / file_hash
    
    def store_file(self, source_path: Union[str, Path]) -> str:
        """
        Store a file using its hash as the filename.
        
        Args:
            source_path: Path to source file
            
        Returns:
            SHA-256 hash of the stored file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If file operations fail
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Calculate hash of file content
        with open(source_path, 'rb') as f:
            file_hash = self._calculate_hash(f)
        
        storage_path = self._get_storage_path(file_hash)
        
        # Only copy if file doesn't already exist (deduplication)
        if not storage_path.exists():
            shutil.copy2(source_path, storage_path)
        
        return file_hash
    
    def store_content(self, content: Union[str, bytes], encoding: str = 'utf-8') -> str:
        """
        Store content directly using its hash as the filename.
        
        Args:
            content: Content to store
            encoding: Text encoding (only used for string content)
            
        Returns:
            SHA-256 hash of the stored content
        """
        # Calculate hash
        file_hash = self._calculate_hash(content)
        storage_path = self._get_storage_path(file_hash)
        
        # Only store if file doesn't already exist (deduplication)
        if not storage_path.exists():
            if isinstance(content, str):
                with open(storage_path, 'w', encoding=encoding) as f:
                    f.write(content)
            else:
                with open(storage_path, 'wb') as f:
                    f.write(content)
        
        return file_hash
    
    def retrieve_file(self, file_hash: str, destination_path: Union[str, Path]) -> bool:
        """
        Retrieve a file by its hash and copy to destination.
        
        Args:
            file_hash: SHA-256 hash of file
            destination_path: Where to copy the file
            
        Returns:
            True if file was retrieved successfully, False if not found
        """
        storage_path = self._get_storage_path(file_hash)
        
        if not storage_path.exists():
            return False
        
        destination_path = Path(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(storage_path, destination_path)
        return True
    
    def retrieve_content(self, file_hash: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Retrieve content by its hash as string.
        
        Args:
            file_hash: SHA-256 hash of file
            encoding: Text encoding to use
            
        Returns:
            File content as string, or None if not found
        """
        storage_path = self._get_storage_path(file_hash)
        
        if not storage_path.exists():
            return None
        
        try:
            with open(storage_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Return as binary string if not valid text
            with open(storage_path, 'rb') as f:
                return f.read().decode('latin1')
    
    def retrieve_binary_content(self, file_hash: str) -> Optional[bytes]:
        """
        Retrieve content by its hash as bytes.
        
        Args:
            file_hash: SHA-256 hash of file
            
        Returns:
            File content as bytes, or None if not found
        """
        storage_path = self._get_storage_path(file_hash)
        
        if not storage_path.exists():
            return None
        
        with open(storage_path, 'rb') as f:
            return f.read()
    
    def file_exists(self, file_hash: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_hash: SHA-256 hash of file
            
        Returns:
            True if file exists, False otherwise
        """
        storage_path = self._get_storage_path(file_hash)
        return storage_path.exists()
    
    def get_file_size(self, file_hash: str) -> Optional[int]:
        """
        Get size of stored file.
        
        Args:
            file_hash: SHA-256 hash of file
            
        Returns:
            File size in bytes, or None if not found
        """
        storage_path = self._get_storage_path(file_hash)
        
        if not storage_path.exists():
            return None
        
        return storage_path.stat().st_size
    
    def delete_file(self, file_hash: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_hash: SHA-256 hash of file
            
        Returns:
            True if file was deleted, False if not found
        """
        storage_path = self._get_storage_path(file_hash)
        
        if not storage_path.exists():
            return False
        
        storage_path.unlink()
        
        # Clean up empty directories
        parent_dir = storage_path.parent
        try:
            if not any(parent_dir.iterdir()):
                parent_dir.rmdir()
                grandparent_dir = parent_dir.parent
                if not any(grandparent_dir.iterdir()):
                    grandparent_dir.rmdir()
        except OSError:
            # Directory not empty or other issues - ignore
            pass
        
        return True
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    total_files += 1
                    total_size += file_path.stat().st_size
                except OSError:
                    # File might have been deleted concurrently
                    pass
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'data_directory': str(self.data_dir)
        }