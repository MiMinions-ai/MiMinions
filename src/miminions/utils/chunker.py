"""
Simple text chunker for document ingestion

Splits text into fixed-size chunks with configurable overlap
for better semantic search and retrieval.
"""

from typing import List, Dict, Any


class TextChunker:
    """Simple text chunker with overlap support"""
    
    def __init__(self, chunk_size: int = 800, overlap: int = 150):
        """Initialize the chunker
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
        if chunk_size <= overlap:
            raise ValueError("chunk_size must be greater than overlap")
        
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata
        
        Args:
            text: The text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Extract chunk
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            if chunk_text.strip():
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end
                })
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
                
                chunk_index += 1
            
            start += self.chunk_size - self.overlap
        
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks


def create_chunker(chunk_size: int = 800, overlap: int = 150) -> TextChunker:
    """Create a new text chunker instance
    
    Args:
        chunk_size: Target size for each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        TextChunker instance
    """
    return TextChunker(chunk_size=chunk_size, overlap=overlap)
