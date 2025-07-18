# MiMinions Local Data Management System

A comprehensive local file system data management solution for MiMinions that provides hash-based storage, master index files, transaction logging, and support for multiple file types.

## Features

### Core Capabilities
- **Hash-based Storage**: Files are stored using SHA-256 hashes for automatic deduplication
- **Master Index**: Comprehensive metadata tracking with search capabilities
- **Transaction Logging**: Complete audit trail of all operations
- **Multi-file Type Support**: Built-in handlers for text, markdown, and CSV files
- **User Directory Management**: Creates and manages `.miminions` folder in user's home directory

### Key Components

#### 1. LocalDataManager
Main interface for the data management system.

```python
from miminions.data.local import LocalDataManager

# Initialize with default location (~/.miminions)
manager = LocalDataManager()

# Or specify custom location
manager = LocalDataManager("/path/to/data", author="username")
```

#### 2. Storage Backend
Hash-based file storage with automatic deduplication.

- Files stored in 2-level directory structure (`ab/cd/abcd1234...`)
- Automatic deduplication based on SHA-256 hashes
- Efficient retrieval by hash

#### 3. Master Index
Comprehensive metadata management.

- File metadata including name, path, tags, type, description, author, dates
- Fast search by name, type, tags, author
- Automatic file rotation for large indices
- Access tracking and statistics

#### 4. Transaction Log
Complete audit trail of all operations.

- Records read, write, update, delete operations
- Automatic log rotation when size limits exceeded
- Query by file, user, time range, operation type
- Self-contained log format with headers

#### 5. File Handlers
Extensible file type support.

- **TextFileHandler**: Plain text files (.txt, .log, etc.)
- **MarkdownFileHandler**: Markdown files with header extraction
- **CSVFileHandler**: CSV files with structure analysis
- **FileHandlerRegistry**: Pluggable handler system

## Quick Start

### Basic Usage

```python
from miminions.data.local import LocalDataManager

# Initialize
manager = LocalDataManager(author="your_name")

# Add content directly
file_id = manager.add_content(
    content="Hello, World!",
    name="greeting.txt",
    description="A simple greeting",
    tags=["greeting", "text"]
)

# Add a physical file
file_id = manager.add_file(
    "/path/to/document.pdf",
    description="Important document",
    tags=["document", "important"]
)

# Retrieve content
content = manager.get_content(file_id)

# Search files
files = manager.search_files(tags=["important"])
files = manager.search_files(file_type="text")
files = manager.search_files(name_pattern="document")

# Get statistics
stats = manager.get_stats()
print(f"Total files: {stats['index']['total_files']}")
```

### File Operations

```python
# Extract file to disk
manager.extract_file(file_id, "/path/to/destination.txt")

# Update metadata
manager.update_metadata(file_id, {
    "description": "Updated description",
    "tags": ["new", "tags"]
})

# Delete file
manager.delete_file(file_id, remove_storage=True)
```

### Activity Tracking

```python
# Get recent activity
activity = manager.get_recent_activity(limit=10)
for record in activity:
    print(f"{record.timestamp}: {record.transaction_type.value}")

# Get file history
history = manager.get_file_history(file_id)
```

### Backup and Restore

```python
# Create backup
manager.backup_system("/path/to/backup")

# Restore from backup
manager.restore_from_backup("/path/to/backup")
```

## Directory Structure

The system creates the following structure in the `.miminions` directory:

```
~/.miminions/
├── index/
│   ├── master_index.json       # Current index file
│   ├── master_index_001.json   # Rotated index files
│   └── ...
├── logs/
│   ├── transaction.log         # Current transaction log
│   ├── transaction_001.log     # Rotated log files
│   └── ...
├── data/
│   ├── ab/cd/abcd1234...      # Hash-based file storage
│   └── ...
└── metadata/
    ├── file_types.json
    └── tags.json
```

## Supported File Types

### Text Files (.txt, .log, etc.)
- Character, word, and line counting
- Encoding detection
- Content preview

### Markdown Files (.md, .markdown, etc.)
- Header extraction and analysis
- Code block detection
- Link and table detection
- Automatic tagging based on content

### CSV Files (.csv)
- Column and row counting
- Header detection
- Delimiter detection
- Data type inference

### Extensible Handler System
Add support for new file types by implementing the `FileHandler` interface:

```python
from miminions.data.local import FileHandler

class CustomFileHandler(FileHandler):
    def get_file_type(self) -> str:
        return "custom"
    
    def can_handle(self, file_path, mime_type=None) -> bool:
        return file_path.suffix.lower() == '.custom'
    
    def extract_metadata(self, file_path) -> dict:
        # Extract custom metadata
        return {"custom_field": "value"}
    
    def get_content_preview(self, file_path, max_chars=500) -> str:
        # Return content preview
        return "Custom content preview"

# Register the handler
manager.file_handlers.register(CustomFileHandler())
```

## API Reference

### LocalDataManager

#### Core Methods
- `add_content(content, name, file_type="text", description="", tags=None, author=None)` - Add content directly
- `add_file(file_path, name=None, description="", tags=None, author=None)` - Add physical file
- `get_file(file_id, author=None)` - Get file metadata
- `get_content(file_id, author=None, encoding="utf-8")` - Get file content as string
- `get_binary_content(file_id, author=None)` - Get file content as bytes
- `extract_file(file_id, destination, author=None)` - Extract file to disk
- `update_metadata(file_id, updates, author=None)` - Update file metadata
- `delete_file(file_id, author=None, remove_storage=True)` - Delete file

#### Search Methods
- `search_files(name_pattern=None, file_type=None, tags=None, author=None)` - Search files
- `list_files()` - List all files
- `get_tags()` - Get all unique tags
- `get_file_types()` - Get all file types
- `get_authors()` - Get all authors

#### System Methods
- `get_stats()` - Get system statistics
- `get_recent_activity(limit=100)` - Get recent activity
- `get_file_history(file_id)` - Get file transaction history
- `backup_system(backup_path)` - Create system backup
- `restore_from_backup(backup_path)` - Restore from backup

### FileMetadata

File metadata structure:
```python
{
    "id": "unique-file-id",
    "original_name": "filename.txt",
    "original_path": "/path/to/original/file",
    "file_hash": "sha256-hash",
    "file_type": "text",
    "size_bytes": 1024,
    "tags": ["tag1", "tag2"],
    "description": "File description",
    "author": "username",
    "created_at": "2023-07-18T10:30:00",
    "updated_at": "2023-07-18T10:30:00",
    "access_count": 5,
    "last_accessed": "2023-07-18T15:45:00"
}
```

## Error Handling

The system provides comprehensive error handling:

- `FileNotFoundError` - When source files don't exist
- `ValueError` - For invalid operations or parameters
- Graceful degradation for corrupted index or log files
- Automatic recovery from partial failures

## Performance Considerations

- **Deduplication**: Identical content is stored only once
- **Indexing**: Fast searches using in-memory indices
- **Streaming**: Large files are processed in chunks
- **Rotation**: Automatic rotation of large index and log files
- **Caching**: Frequently accessed metadata is cached

## Testing

Run the test suite:

```bash
# Unit tests
python -m pytest tests/test_data_management.py -v

# End-to-end tests
python -m pytest tests/test_data_management_e2e.py -v

# All tests
python -m pytest tests/ -v
```

Run the example:

```bash
python examples/data_management/basic_usage.py
```

## Advanced Usage

### Custom Configuration

```python
# Custom storage location and settings
manager = LocalDataManager(
    base_dir="/custom/path/.miminions",
    author="custom_user"
)

# Access internal components
storage = manager.storage
index = manager.index
transaction_log = manager.transaction_log
```

### Batch Operations

```python
# Add multiple files efficiently
file_ids = []
for file_path in file_paths:
    file_id = manager.add_file(file_path, tags=["batch"])
    file_ids.append(file_id)

# Batch search and operations
batch_files = manager.search_files(tags=["batch"])
for file_meta in batch_files:
    manager.update_metadata(file_meta.id, {"processed": True})
```

### Integration with Existing Systems

```python
# Integrate with file watchers
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DataManagerHandler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager
    
    def on_created(self, event):
        if not event.is_directory:
            self.manager.add_file(event.src_path, tags=["auto-added"])

# Monitor directory
observer = Observer()
observer.schedule(DataManagerHandler(manager), "/path/to/watch", recursive=True)
observer.start()
```

## License

This module is part of the MiMinions project and follows the same license terms.

## Contributing

1. Implement new file handlers for additional formats
2. Add new search capabilities
3. Improve performance optimizations
4. Add new metadata extraction features
5. Enhance backup/restore functionality

For more information, see the main MiMinions documentation.