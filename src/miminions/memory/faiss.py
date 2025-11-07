# src/miminions/memory/faiss_memory.py

import faiss
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base_memory import BaseMemory
from uuid import uuid4
from sentence_transformers import SentenceTransformer

class FAISSMemory(BaseMemory):
    def __init__(self, dim: int = 384, model_name: str = "all-MiniLM-L6-v2"):
        self.index = faiss.IndexFlatL2(dim)
        self.encoder = SentenceTransformer(model_name)
        self.dim = dim
        self.id_to_idx = {} 
        self.metadata = [] 

    def create(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add knowledge to memory and return its ID"""
        vector = self.encoder.encode([text]).astype("float32")
        
        current_idx = self.index.ntotal
        self.index.add(vector)
        
        id = str(uuid4())
        self.id_to_idx[id] = current_idx # add id and its index mapping
        
        self.metadata.append({
            "id": id,
            "text": text,
            "meta": metadata or {}
        })
        
        return id

    def read(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k similar knowledge entries"""
        if self.index.ntotal == 0:
            return []
        
        query_vec = self.encoder.encode([query]).astype("float32")
        k = min(top_k, self.index.ntotal)
        D, I = self.index.search(query_vec, k)
        
        results = []
        for idx, distance in zip(I[0], D[0]):
            if idx < len(self.metadata) and idx >= 0:
                result = self.metadata[idx].copy()
                result["distance"] = float(distance)
                results.append(result)
        
        return results

    def update(self, id: str, new_text: str) -> bool:
        """Update a knowledge entry by ID"""
        if id not in self.id_to_idx:
            return False
        
        idx = self.id_to_idx[id]
        
        # Update text in metadata and rebuild
        if idx < len(self.metadata):
            old_metadata = self.metadata[idx]["meta"]
            self.metadata[idx]["text"] = new_text
            
            new_vec = self.encoder.encode([new_text]).astype("float32")
            
            # change to IndexIDMap later?
            self._rebuild_index_with_update(idx, new_vec)
            
            return True
        return False

    def delete(self, id: str) -> bool:
        """Delete a knowledge entry by ID"""
        if id not in self.id_to_idx:
            return False
        
        idx = self.id_to_idx[id]
        
        # Remove from metadata, rebuild id map, then rebuild the index
        if idx < len(self.metadata):
            self.metadata.pop(idx)
            
            del self.id_to_idx[id]
            self._rebuild_id_mappings(idx)
            
            self._rebuild_index()
            
            return True
        return False
    
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific entry by ID"""
        if id not in self.id_to_idx:
            return None
        
        idx = self.id_to_idx[id]
        if idx < len(self.metadata):
            return self.metadata[idx].copy()
        return None
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all knowledge entries"""
        return [entry.copy() for entry in self.metadata]
    
    def clear(self) -> None:
        """Clear all knowledge from memory"""
        self.index.reset()
        self.id_to_idx.clear()
        self.metadata.clear()
    
    def _rebuild_index(self):
        """Rebuild FAISS index from metadata"""
        self.index.reset()
        
        if not self.metadata:
            return
        
        vectors = []
        for entry in self.metadata:
            vec = self.encoder.encode([entry["text"]]).astype("float32")
            vectors.append(vec)
        
        if vectors:
            vectors_array = np.vstack(vectors)
            self.index.add(vectors_array)
    
    def _rebuild_id_mappings(self, deleted_idx: int):
        """Rebuild ID to index mappings after deletion"""
        new_mappings = {}
        for id, idx in self.id_to_idx.items():
            if idx < deleted_idx:
                new_mappings[id] = idx
            elif idx > deleted_idx:
                new_mappings[id] = idx - 1
        self.id_to_idx = new_mappings
    
    def _rebuild_index_with_update(self, update_idx: int, new_vec: np.ndarray):
        """Rebuild index with an updated vector"""
        self.index.reset()
        
        vectors = []
        for i, entry in enumerate(self.metadata):
            if i == update_idx:
                vectors.append(new_vec)
            else:
                vec = self.encoder.encode([entry["text"]]).astype("float32")
                vectors.append(vec)
        
        if vectors:
            vectors_array = np.vstack(vectors)
            self.index.add(vectors_array)