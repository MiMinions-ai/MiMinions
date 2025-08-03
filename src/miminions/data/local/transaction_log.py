"""
Transaction log management for local data storage.

Records all read, write, and removal operations for audit trail and consistency.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, TextIO
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Types of transactions."""
    READ = "read"
    WRITE = "write" 
    UPDATE = "update"
    DELETE = "delete"
    CREATE_INDEX = "create_index"
    ROTATE_LOG = "rotate_log"


@dataclass
class TransactionRecord:
    """Single transaction record."""
    id: str
    timestamp: str
    transaction_type: TransactionType
    file_id: Optional[str] = None
    file_hash: Optional[str] = None
    file_name: Optional[str] = None
    author: Optional[str] = None
    details: Dict[str, Any] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['transaction_type'] = self.transaction_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionRecord':
        """Create from dictionary."""
        if 'transaction_type' in data:
            data['transaction_type'] = TransactionType(data['transaction_type'])
        return cls(**data)


class TransactionLog:
    """Transaction log for recording all data operations."""
    
    def __init__(self, log_dir: Path, max_log_size_mb: int = 100):
        """
        Initialize transaction log.
        
        Args:
            log_dir: Directory for log files
            max_log_size_mb: Maximum log file size before rotation
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        self.current_log_file = self.log_dir / "transaction.log"
        
        # Ensure log file exists
        if not self.current_log_file.exists():
            self._create_new_log()
    
    def _create_new_log(self) -> None:
        """Create a new log file with header."""
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            header = {
                'log_type': 'miminions_transaction_log',
                'version': '1.0',
                'created_at': datetime.utcnow().isoformat(),
                'format': 'jsonlines'
            }
            f.write(json.dumps(header) + '\n')
    
    def _get_next_log_filename(self) -> Path:
        """Get next available log filename for rotation."""
        counter = 1
        while True:
            filename = f"transaction_{counter:03d}.log"
            filepath = self.log_dir / filename
            if not filepath.exists():
                return filepath
            counter += 1
    
    def _rotate_log_if_needed(self) -> None:
        """Rotate log file if it exceeds size limit."""
        if not self.current_log_file.exists():
            return
        
        if self.current_log_file.stat().st_size > self.max_log_size_bytes:
            # Move current log to historical location
            next_filename = self._get_next_log_filename()
            self.current_log_file.rename(next_filename)
            
            # Create new log file
            self._create_new_log()
            
            # Log the rotation event
            self._write_transaction_record(TransactionRecord(
                id=f"rotate_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.utcnow().isoformat(),
                transaction_type=TransactionType.ROTATE_LOG,
                details={'rotated_to': str(next_filename)}
            ))
    
    def _write_transaction_record(self, record: TransactionRecord) -> None:
        """Write a transaction record to the current log file."""
        self._rotate_log_if_needed()
        
        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record.to_dict()) + '\n')
            f.flush()
    
    def log_read(self, file_id: str, file_hash: str = None, file_name: str = None, 
                 author: str = None, details: Dict[str, Any] = None) -> None:
        """
        Log a file read operation.
        
        Args:
            file_id: ID of file being read
            file_hash: Hash of file being read
            file_name: Name of file being read
            author: User performing the operation
            details: Additional operation details
        """
        record = TransactionRecord(
            id=f"read_{file_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow().isoformat(),
            transaction_type=TransactionType.READ,
            file_id=file_id,
            file_hash=file_hash,
            file_name=file_name,
            author=author,
            details=details or {}
        )
        self._write_transaction_record(record)
    
    def log_write(self, file_id: str, file_hash: str = None, file_name: str = None,
                  author: str = None, details: Dict[str, Any] = None, success: bool = True,
                  error_message: str = None) -> None:
        """
        Log a file write operation.
        
        Args:
            file_id: ID of file being written
            file_hash: Hash of file being written
            file_name: Name of file being written  
            author: User performing the operation
            details: Additional operation details
            success: Whether operation succeeded
            error_message: Error message if operation failed
        """
        record = TransactionRecord(
            id=f"write_{file_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow().isoformat(),
            transaction_type=TransactionType.WRITE,
            file_id=file_id,
            file_hash=file_hash,
            file_name=file_name,
            author=author,
            details=details or {},
            success=success,
            error_message=error_message
        )
        self._write_transaction_record(record)
    
    def log_update(self, file_id: str, file_hash: str = None, file_name: str = None,
                   author: str = None, details: Dict[str, Any] = None, success: bool = True,
                   error_message: str = None) -> None:
        """
        Log a file update operation.
        
        Args:
            file_id: ID of file being updated
            file_hash: Hash of file being updated
            file_name: Name of file being updated
            author: User performing the operation
            details: Additional operation details
            success: Whether operation succeeded
            error_message: Error message if operation failed
        """
        record = TransactionRecord(
            id=f"update_{file_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow().isoformat(),
            transaction_type=TransactionType.UPDATE,
            file_id=file_id,
            file_hash=file_hash,
            file_name=file_name,
            author=author,
            details=details or {},
            success=success,
            error_message=error_message
        )
        self._write_transaction_record(record)
    
    def log_delete(self, file_id: str, file_hash: str = None, file_name: str = None,
                   author: str = None, details: Dict[str, Any] = None, success: bool = True,
                   error_message: str = None) -> None:
        """
        Log a file delete operation.
        
        Args:
            file_id: ID of file being deleted
            file_hash: Hash of file being deleted
            file_name: Name of file being deleted
            author: User performing the operation
            details: Additional operation details
            success: Whether operation succeeded
            error_message: Error message if operation failed
        """
        record = TransactionRecord(
            id=f"delete_{file_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow().isoformat(),
            transaction_type=TransactionType.DELETE,
            file_id=file_id,
            file_hash=file_hash,
            file_name=file_name,
            author=author,
            details=details or {},
            success=success,
            error_message=error_message
        )
        self._write_transaction_record(record)
    
    def get_transactions(self, 
                        file_id: Optional[str] = None,
                        transaction_type: Optional[TransactionType] = None,
                        author: Optional[str] = None,
                        start_time: Optional[str] = None,
                        end_time: Optional[str] = None,
                        limit: Optional[int] = None) -> List[TransactionRecord]:
        """
        Query transaction records.
        
        Args:
            file_id: Filter by file ID
            transaction_type: Filter by transaction type
            author: Filter by author
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            limit: Maximum number of records to return
            
        Returns:
            List of matching transaction records
        """
        records = []
        
        # Get all log files (current + historical)
        log_files = [self.current_log_file]
        log_files.extend(self.log_dir.glob("transaction_*.log"))
        
        for log_file in log_files:
            if not log_file.exists():
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                            
                            # Skip header lines
                            if data.get('log_type') == 'miminions_transaction_log':
                                continue
                            
                            # Parse transaction record
                            record = TransactionRecord.from_dict(data)
                            
                            # Apply filters
                            if file_id and record.file_id != file_id:
                                continue
                            
                            if transaction_type and record.transaction_type != transaction_type:
                                continue
                            
                            if author and record.author != author:
                                continue
                            
                            if start_time and record.timestamp < start_time:
                                continue
                            
                            if end_time and record.timestamp > end_time:
                                continue
                            
                            records.append(record)
                            
                            # Check limit
                            if limit and len(records) >= limit:
                                break
                                
                        except (json.JSONDecodeError, ValueError, TypeError) as e:
                            logger.warning(f"Could not parse log line {line_num} in {log_file}: {e}")
                            continue
                    
                    # Check limit
                    if limit and len(records) >= limit:
                        break
                        
            except IOError as e:
                print(f"Warning: Could not read log file {log_file}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        records.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit after sorting
        if limit:
            records = records[:limit]
        
        return records
    
    def get_file_history(self, file_id: str) -> List[TransactionRecord]:
        """
        Get complete transaction history for a specific file.
        
        Args:
            file_id: File ID to get history for
            
        Returns:
            List of transaction records for the file
        """
        return self.get_transactions(file_id=file_id)
    
    def get_recent_activity(self, limit: int = 100) -> List[TransactionRecord]:
        """
        Get recent activity across all files.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent transaction records
        """
        return self.get_transactions(limit=limit)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get transaction log statistics.
        
        Returns:
            Dictionary with log statistics
        """
        # Get all log files
        log_files = [self.current_log_file]
        log_files.extend(self.log_dir.glob("transaction_*.log"))
        
        total_size = 0
        total_records = 0
        transaction_counts = {}
        
        for log_file in log_files:
            if not log_file.exists():
                continue
            
            try:
                total_size += log_file.stat().st_size
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                            
                            # Skip header lines
                            if data.get('log_type') == 'miminions_transaction_log':
                                continue
                            
                            total_records += 1
                            
                            transaction_type = data.get('transaction_type', 'unknown')
                            transaction_counts[transaction_type] = transaction_counts.get(transaction_type, 0) + 1
                            
                        except (json.JSONDecodeError, ValueError):
                            continue
            
            except IOError:
                continue
        
        return {
            'total_log_files': len(log_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_records': total_records,
            'transaction_counts': transaction_counts,
            'current_log_file': str(self.current_log_file)
        }