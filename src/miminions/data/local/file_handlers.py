"""
File handlers for different file types.

Provides specific handling for text, markdown, CSV and other file types
including metadata extraction and content processing.
"""

import csv
import mimetypes
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class FileHandler(ABC):
    """Base class for file type handlers."""
    
    @abstractmethod
    def get_file_type(self) -> str:
        """Get the file type identifier."""
        pass
    
    @abstractmethod
    def can_handle(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        """Check if this handler can process the given file."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract metadata from the file."""
        pass
    
    @abstractmethod
    def get_content_preview(self, file_path: Union[str, Path], max_chars: int = 500) -> str:
        """Get a preview of the file content."""
        pass
    
    def get_default_tags(self, file_path: Union[str, Path]) -> List[str]:
        """Get default tags for this file type."""
        return [self.get_file_type()]


class TextFileHandler(FileHandler):
    """Handler for plain text files."""
    
    def get_file_type(self) -> str:
        return "text"
    
    def can_handle(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        file_path = Path(file_path)
        
        # Check by extension
        text_extensions = {'.txt', '.text', '.log', '.rtf'}
        if file_path.suffix.lower() in text_extensions:
            return True
        
        # Check by MIME type
        if mime_type:
            return mime_type.startswith('text/plain')
        
        # Try to detect MIME type
        detected_mime, _ = mimetypes.guess_type(str(file_path))
        if detected_mime and detected_mime.startswith('text/plain'):
            return True
        
        return False
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        file_path = Path(file_path)
        
        metadata = {
            'encoding': 'utf-8',
            'line_count': 0,
            'word_count': 0,
            'char_count': 0
        }
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    metadata['encoding'] = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is not None:
                metadata['char_count'] = len(content)
                metadata['line_count'] = content.count('\n') + 1
                metadata['word_count'] = len(content.split())
            
        except Exception as e:
            metadata['error'] = str(e)
        
        return metadata
    
    def get_content_preview(self, file_path: Union[str, Path], max_chars: int = 500) -> str:
        file_path = Path(file_path)
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(max_chars)
                    return content
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='replace'
            with open(file_path, 'rb') as f:
                raw_content = f.read(max_chars)
            return raw_content.decode('utf-8', errors='replace')
            
        except Exception as e:
            return f"Error reading file: {e}"


class MarkdownFileHandler(FileHandler):
    """Handler for Markdown files."""
    
    def get_file_type(self) -> str:
        return "markdown"
    
    def can_handle(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        file_path = Path(file_path)
        
        # Check by extension
        markdown_extensions = {'.md', '.markdown', '.mdown', '.mkd', '.mkdn'}
        if file_path.suffix.lower() in markdown_extensions:
            return True
        
        # Check by MIME type
        if mime_type:
            return mime_type in ['text/markdown', 'text/x-markdown']
        
        return False
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        file_path = Path(file_path)
        
        metadata = {
            'encoding': 'utf-8',
            'line_count': 0,
            'word_count': 0,
            'char_count': 0,
            'headers': [],
            'has_code_blocks': False,
            'has_tables': False,
            'has_links': False
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata['char_count'] = len(content)
            lines = content.split('\n')
            metadata['line_count'] = len(lines)
            metadata['word_count'] = len(content.split())
            
            # Extract headers
            headers = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#'):
                    level = 0
                    for char in stripped:
                        if char == '#':
                            level += 1
                        else:
                            break
                    header_text = stripped[level:].strip()
                    if header_text:
                        headers.append({'level': level, 'text': header_text})
            
            metadata['headers'] = headers
            
            # Check for code blocks
            metadata['has_code_blocks'] = '```' in content or '~~~' in content
            
            # Check for tables
            metadata['has_tables'] = any('|' in line for line in lines)
            
            # Check for links
            metadata['has_links'] = '[' in content and '](' in content
            
        except Exception as e:
            metadata['error'] = str(e)
        
        return metadata
    
    def get_content_preview(self, file_path: Union[str, Path], max_chars: int = 500) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(max_chars)
            return content
        except Exception as e:
            return f"Error reading file: {e}"
    
    def get_default_tags(self, file_path: Union[str, Path]) -> List[str]:
        tags = super().get_default_tags(file_path)
        
        # Extract additional tags from metadata
        metadata = self.extract_metadata(file_path)
        
        if metadata.get('has_code_blocks'):
            tags.append('code')
        
        if metadata.get('has_tables'):
            tags.append('tables')
        
        if metadata.get('has_links'):
            tags.append('links')
        
        # Add tags based on headers
        headers = metadata.get('headers', [])
        if headers:
            tags.append('structured')
            if any(h['level'] == 1 for h in headers):
                tags.append('document')
        
        return tags


class CSVFileHandler(FileHandler):
    """Handler for CSV files."""
    
    def get_file_type(self) -> str:
        return "csv"
    
    def _detect_csv_header(self, first_row: List[str], second_row: List[str]) -> bool:
        """
        Determine if the first row of a CSV file is a header using heuristic analysis.
        
        This method analyzes the first and second rows of a CSV file to determine
        if the first row contains column headers. The heuristic is based on the
        common structure of CSV files where headers are textual and data rows
        contain numeric or date-like values.
        
        Logic:
            - Assume the first row is a header if it contains strings, and the second row
              contains numbers or date-like values.
            - This is based on the common structure of CSV files where headers are textual
              and data rows are numeric or date-based.
        
        Assumptions:
            - The first row contains only strings (e.g., column names).
            - The second row contains values that can be parsed as numbers or dates.
        
        Limitations:
            - This heuristic may fail for CSV files with unconventional structures, such as:
              - Mixed data types in the first or second row.
              - Non-standard headers (e.g., numeric headers).
            - It does not handle cases where the second row contains non-numeric, non-date
              values that are still valid data.
        
        Args:
            first_row: The first row of the CSV file
            second_row: The second row of the CSV file
            
        Returns:
            True if the first row appears to be a header, False otherwise
        """
        has_header = True
        try:
            for i, (first, second) in enumerate(zip(first_row, second_row)):
                # Try to parse second row values as numbers
                try:
                    float(second)
                except ValueError:
                    # Not a number, check if it's a date-like string
                    if not any(char.isdigit() for char in second):
                        has_header = False
                        break
        except:
            has_header = False
        
        return has_header
    
    def can_handle(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        file_path = Path(file_path)
        
        # Check by extension
        if file_path.suffix.lower() == '.csv':
            return True
        
        # Check by MIME type
        if mime_type:
            return mime_type in ['text/csv', 'application/csv']
        
        return False
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a CSV file.
        
        This method analyzes the CSV file to determine its structure and properties
        including encoding, delimiter, header presence, column information, and
        row/column counts. It uses multiple detection strategies to handle various
        CSV formats and encodings.
        
        The method attempts to:
            - Detect the file encoding by trying multiple common encodings
            - Identify the delimiter using CSV sniffer or common delimiters
            - Determine if the first row contains headers using heuristic analysis
            - Count rows and columns for data structure information
            - Extract column names or generate default column names
        
        Args:
            file_path: Path to the CSV file to analyze
            
        Returns:
            Dictionary containing:
                - encoding: Detected file encoding
                - delimiter: Detected field delimiter
                - has_header: Whether the file has a header row
                - columns: List of column names or generated names
                - row_count: Total number of data rows
                - column_count: Number of columns
                - error: Error message if analysis fails
        """
        file_path = Path(file_path)
        
        metadata = {
            'encoding': 'utf-8',
            'delimiter': ',',
            'has_header': False,
            'columns': [],
            'row_count': 0,
            'column_count': 0
        }
        
        try:
            # Try to detect encoding and delimiter
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            delimiters = [',', ';', '\t', '|']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        # Read first few lines to detect format
                        sample = f.read(8192)
                    
                    metadata['encoding'] = encoding
                    
                    # Detect delimiter
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample, delimiters=delimiters)
                        metadata['delimiter'] = dialect.delimiter
                    except csv.Error:
                        # Default to comma
                        metadata['delimiter'] = ','
                    
                    # Analyze structure
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f, delimiter=metadata['delimiter'])
                        
                        rows = list(reader)
                        if rows:
                            metadata['row_count'] = len(rows)
                            metadata['column_count'] = len(rows[0]) if rows else 0
                            
                            # Check if first row looks like headers
                            if len(rows) > 1:
                                first_row = rows[0]
                                second_row = rows[1]
                                
                                has_header = self._detect_csv_header(first_row, second_row)
                                
                                metadata['has_header'] = has_header
                                
                                if has_header:
                                    metadata['columns'] = first_row
                                else:
                                    metadata['columns'] = [f'Column_{i+1}' for i in range(len(first_row))]
                    
                    break
                    
                except UnicodeDecodeError:
                    continue
        
        except Exception as e:
            metadata['error'] = str(e)
        
        return metadata
    
    def get_content_preview(self, file_path: Union[str, Path], max_chars: int = 500) -> str:
        try:
            metadata = self.extract_metadata(file_path)
            encoding = metadata.get('encoding', 'utf-8')
            delimiter = metadata.get('delimiter', ',')
            
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                preview_lines = []
                char_count = 0
                
                for i, row in enumerate(reader):
                    if i >= 10:  # Limit to first 10 rows
                        break
                    
                    line = delimiter.join(row)
                    if char_count + len(line) > max_chars:
                        break
                    
                    preview_lines.append(line)
                    char_count += len(line) + 1  # +1 for newline
                
                return '\n'.join(preview_lines)
        
        except Exception as e:
            return f"Error reading CSV file: {e}"
    
    def get_default_tags(self, file_path: Union[str, Path]) -> List[str]:
        tags = super().get_default_tags(file_path)
        tags.append('tabular')
        tags.append('data')
        
        # Add tags based on metadata
        metadata = self.extract_metadata(file_path)
        
        if metadata.get('has_header'):
            tags.append('structured')
        
        column_count = metadata.get('column_count', 0)
        if column_count > 10:
            tags.append('wide')
        elif column_count > 0:
            tags.append('narrow')
        
        return tags


class FileHandlerRegistry:
    """Registry for file handlers."""
    
    def __init__(self):
        self.handlers: List[FileHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default file handlers."""
        self.register(TextFileHandler())
        self.register(MarkdownFileHandler())
        self.register(CSVFileHandler())
    
    def register(self, handler: FileHandler) -> None:
        """Register a file handler."""
        self.handlers.append(handler)
    
    def get_handler(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> Optional[FileHandler]:
        """
        Get appropriate handler for a file.
        
        Args:
            file_path: Path to the file
            mime_type: Optional MIME type hint
            
        Returns:
            File handler if found, None otherwise
        """
        for handler in self.handlers:
            if handler.can_handle(file_path, mime_type):
                return handler
        return None
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of all supported file extensions.
        
        This method determines supported file extensions by testing each handler
        with sample files. It creates temporary test files with known extensions
        and checks if the corresponding handler can process them.
        
        Note: This is a simplified implementation. In a production environment,
        handlers should expose their supported extensions directly for better
        performance and accuracy.
        
        Returns:
            List of supported file extensions (e.g., ['.txt', '.md', '.csv'])
        """
        extensions = set()
        
        # Test each handler with sample files to determine supported extensions
        test_files = {
            '.txt': TextFileHandler(),
            '.md': MarkdownFileHandler(),
            '.csv': CSVFileHandler()
        }
        
        for ext, handler in test_files.items():
            if handler.can_handle(f"test{ext}"):
                extensions.add(ext)
        
        return sorted(extensions)