"""
Local data management module for MiMinions.

Provides local file system data management with master index files,
transaction logs, and hash-based storage.
"""

from .manager import LocalDataManager
from .index import MasterIndex, FileMetadata
from .transaction_log import TransactionLog, TransactionRecord, TransactionType
from .file_handlers import FileHandler, TextFileHandler, MarkdownFileHandler, CSVFileHandler, FileHandlerRegistry
from .storage import StorageBackend

__all__ = [
    "LocalDataManager",
    "MasterIndex", 
    "FileMetadata",
    "TransactionLog",
    "TransactionRecord",
    "TransactionType", 
    "FileHandler",
    "TextFileHandler",
    "MarkdownFileHandler", 
    "CSVFileHandler",
    "FileHandlerRegistry",
    "StorageBackend"
]