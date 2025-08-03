"""
Master index management for local data storage.

Manages metadata about stored files including name, path, tags, type,
description, author, and creation date.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field


@dataclass
class FileMetadata:
    """Metadata for a stored file."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_name: str = ""
    original_path: str = ""
    file_hash: str = ""
    file_type: str = ""
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    description: str = ""
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    last_accessed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """Create from dictionary."""
        return cls(**data)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow().isoformat()
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def increment_access(self) -> None:
        """Increment access count and update last accessed time."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow().isoformat()


class MasterIndex:
    """Master index for managing file metadata."""
    
    def __init__(self, index_dir: Path, max_entries_per_file: int = 10000):
        """
        Initialize master index.
        
        Args:
            index_dir: Directory for index files
            max_entries_per_file: Maximum entries per index file before rotation
        """
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_entries_per_file = max_entries_per_file
        self.current_index_file = self.index_dir / "master_index.json"
        
        # In-memory index for fast access
        self._index: Dict[str, FileMetadata] = {}
        self._hash_to_id: Dict[str, str] = {}  # file_hash -> file_id mapping
        self._loaded_files: Set[Path] = set()
        
        self._load_index()
    
    def _get_next_index_filename(self) -> Path:
        """Get the next available index filename for rotation."""
        counter = 1
        while True:
            filename = f"master_index_{counter:03d}.json"
            filepath = self.index_dir / filename
            if not filepath.exists():
                return filepath
            counter += 1
    
    def _load_index(self) -> None:
        """Load index files into memory."""
        # Load current index file
        if self.current_index_file.exists():
            self._load_index_file(self.current_index_file)
        
        # Load all historical index files
        for index_file in self.index_dir.glob("master_index_*.json"):
            if index_file not in self._loaded_files:
                self._load_index_file(index_file)
    
    def _load_index_file(self, index_file: Path) -> None:
        """Load a specific index file."""
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old and new format
            if isinstance(data, dict):
                if 'metadata' in data:
                    # New format with metadata wrapper
                    entries = data.get('entries', {})
                else:
                    # Old format - direct entries
                    entries = data
            else:
                entries = {}
            
            for file_id, metadata_dict in entries.items():
                metadata = FileMetadata.from_dict(metadata_dict)
                self._index[file_id] = metadata
                if metadata.file_hash:
                    self._hash_to_id[metadata.file_hash] = file_id
            
            self._loaded_files.add(index_file)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Could not load index file {index_file}: {e}")
    
    def _save_current_index(self) -> None:
        """Save current index to file."""
        # Check if we need to rotate
        if len(self._index) > self.max_entries_per_file:
            self._rotate_index()
        
        # Prepare data for saving
        index_data = {
            'metadata': {
                'version': '1.0',
                'created_at': datetime.utcnow().isoformat(),
                'total_entries': len(self._index),
                'max_entries_per_file': self.max_entries_per_file
            },
            'entries': {
                file_id: metadata.to_dict() 
                for file_id, metadata in self._index.items()
            }
        }
        
        # Write to temporary file first, then rename (atomic operation)
        temp_file = self.current_index_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        temp_file.replace(self.current_index_file)
    
    def _rotate_index(self) -> None:
        """Rotate current index file and start a new one."""
        if self.current_index_file.exists():
            # Move current index to historical location
            next_filename = self._get_next_index_filename()
            self.current_index_file.rename(next_filename)
            self._loaded_files.add(next_filename)
        
        # The current index will be recreated with fewer entries if needed
        # For simplicity, we keep all entries in memory and just rotate the file
    
    def add_file(self, metadata: FileMetadata) -> str:
        """
        Add file metadata to index.
        
        Args:
            metadata: File metadata to add
            
        Returns:
            File ID of added metadata
        """
        self._index[metadata.id] = metadata
        if metadata.file_hash:
            self._hash_to_id[metadata.file_hash] = metadata.id
        
        self._save_current_index()
        return metadata.id
    
    def update_file(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update file metadata.
        
        Args:
            file_id: ID of file to update
            updates: Dictionary of field updates
            
        Returns:
            True if file was updated, False if not found
        """
        if file_id not in self._index:
            return False
        
        metadata = self._index[file_id]
        
        # Update fields
        for field, value in updates.items():
            if hasattr(metadata, field):
                setattr(metadata, field, value)
        
        metadata.updated_at = datetime.utcnow().isoformat()
        
        # Update hash mapping if hash changed
        if 'file_hash' in updates:
            # Remove old hash mapping
            old_hash = None
            for hash_key, mapped_id in self._hash_to_id.items():
                if mapped_id == file_id:
                    old_hash = hash_key
                    break
            
            if old_hash:
                del self._hash_to_id[old_hash]
            
            # Add new hash mapping
            if updates['file_hash']:
                self._hash_to_id[updates['file_hash']] = file_id
        
        self._save_current_index()
        return True
    
    def get_file(self, file_id: str) -> Optional[FileMetadata]:
        """
        Get file metadata by ID.
        
        Args:
            file_id: File ID
            
        Returns:
            File metadata or None if not found
        """
        return self._index.get(file_id)
    
    def get_file_by_hash(self, file_hash: str) -> Optional[FileMetadata]:
        """
        Get file metadata by hash.
        
        Args:
            file_hash: File hash
            
        Returns:
            File metadata or None if not found
        """
        file_id = self._hash_to_id.get(file_hash)
        if file_id:
            return self._index.get(file_id)
        return None
    
    def remove_file(self, file_id: str) -> bool:
        """
        Remove file metadata from index.
        
        Args:
            file_id: ID of file to remove
            
        Returns:
            True if file was removed, False if not found
        """
        if file_id not in self._index:
            return False
        
        metadata = self._index[file_id]
        
        # Remove from hash mapping
        if metadata.file_hash and metadata.file_hash in self._hash_to_id:
            del self._hash_to_id[metadata.file_hash]
        
        # Remove from index
        del self._index[file_id]
        
        self._save_current_index()
        return True
    
    def search_files(self, 
                     name_pattern: Optional[str] = None,
                     file_type: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     author: Optional[str] = None) -> List[FileMetadata]:
        """
        Search files by various criteria.
        
        Args:
            name_pattern: Pattern to match in filename (case-insensitive)
            file_type: Exact file type match
            tags: List of tags (all must be present)
            author: Author name (case-insensitive)
            
        Returns:
            List of matching file metadata
        """
        results = []
        
        for metadata in self._index.values():
            # Check name pattern
            if name_pattern and name_pattern.lower() not in metadata.original_name.lower():
                continue
            
            # Check file type
            if file_type and metadata.file_type != file_type:
                continue
            
            # Check tags (all must be present)
            if tags and not all(tag in metadata.tags for tag in tags):
                continue
            
            # Check author
            if author and author.lower() not in metadata.author.lower():
                continue
            
            results.append(metadata)
        
        # Sort by creation date (newest first)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results
    
    def list_all_files(self) -> List[FileMetadata]:
        """
        List all files in index.
        
        Returns:
            List of all file metadata, sorted by creation date
        """
        files = list(self._index.values())
        files.sort(key=lambda x: x.created_at, reverse=True)
        return files
    
    def get_all_tags(self) -> Set[str]:
        """
        Get all unique tags in the index.
        
        Returns:
            Set of all tags
        """
        all_tags = set()
        for metadata in self._index.values():
            all_tags.update(metadata.tags)
        return all_tags
    
    def get_file_types(self) -> Set[str]:
        """
        Get all file types in the index.
        
        Returns:
            Set of all file types
        """
        return {metadata.file_type for metadata in self._index.values() if metadata.file_type}
    
    def get_authors(self) -> Set[str]:
        """
        Get all authors in the index.
        
        Returns:
            Set of all authors
        """
        return {metadata.author for metadata in self._index.values() if metadata.author}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index statistics
        """
        total_files = len(self._index)
        total_size = sum(metadata.size_bytes for metadata in self._index.values())
        
        file_types = {}
        for metadata in self._index.values():
            if metadata.file_type:
                file_types[metadata.file_type] = file_types.get(metadata.file_type, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_types': file_types,
            'total_tags': len(self.get_all_tags()),
            'total_authors': len(self.get_authors()),
            'index_files_loaded': len(self._loaded_files)
        }