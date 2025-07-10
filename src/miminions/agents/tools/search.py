"""
Search tools for MiMinions agents

This module provides tools for web search using Google and DuckDuckGo.
"""

import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    import aiohttp
    from googlesearch import search as google_search
    from duckduckgo_search import DDGS
except ImportError:
    aiohttp = None
    google_search = None
    DDGS = None


class SearchTools:
    """
    Search tools for web exploration
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize search tools
        
        Args:
            max_workers: Maximum number of concurrent search operations
        """
        if google_search is None or DDGS is None:
            raise ImportError("googlesearch-python and duckduckgo-search are required for search operations")
        
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._session = None
    
    def _get_session(self):
        """Get aiohttp session for async operations"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    def _google_search_sync(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Internal method for Google search"""
        try:
            results = []
            for i, url in enumerate(google_search(query, num=num_results, stop=num_results)):
                results.append({
                    "url": url,
                    "title": f"Result {i+1}",
                    "snippet": "",
                    "source": "google"
                })
            return results
        except Exception as e:
            return [{"error": str(e), "source": "google"}]
    
    def _duckduckgo_search_sync(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Internal method for DuckDuckGo search"""
        try:
            with DDGS() as ddgs:
                results = []
                for result in ddgs.text(query, max_results=num_results):
                    results.append({
                        "url": result.get("href", ""),
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo"
                    })
                return results
        except Exception as e:
            return [{"error": str(e), "source": "duckduckgo"}]
    
    async def _google_search_async(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Internal async method for Google search"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._google_search_sync, query, num_results)
    
    async def _duckduckgo_search_async(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Internal async method for DuckDuckGo search"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._duckduckgo_search_sync, query, num_results)
    
    def _select_search_engine(self, query: str, prefer_engine: Optional[str] = None) -> str:
        """Internal method to select search engine based on query"""
        if prefer_engine and prefer_engine.lower() in ["google", "duckduckgo"]:
            return prefer_engine.lower()
        
        # Simple heuristic: use Google for specific queries, DuckDuckGo for general ones
        if any(keyword in query.lower() for keyword in ["how to", "tutorial", "guide", "documentation"]):
            return "google"
        else:
            return "duckduckgo"
    
    # Public synchronous methods
    def google_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform Google search
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            
        Returns:
            List of search results
        """
        return self._google_search_sync(query, num_results)
    
    def duckduckgo_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform DuckDuckGo search
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            
        Returns:
            List of search results
        """
        return self._duckduckgo_search_sync(query, num_results)
    
    def search(self, query: str, num_results: int = 10, 
              prefer_engine: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform web search using automatically selected or preferred engine
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            prefer_engine: Preferred search engine ("google" or "duckduckgo")
            
        Returns:
            List of search results
        """
        engine = self._select_search_engine(query, prefer_engine)
        
        if engine == "google":
            return self.google_search(query, num_results)
        else:
            return self.duckduckgo_search(query, num_results)
    
    # Public asynchronous methods
    async def google_search_async(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform Google search asynchronously
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            
        Returns:
            List of search results
        """
        return await self._google_search_async(query, num_results)
    
    async def duckduckgo_search_async(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform DuckDuckGo search asynchronously
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            
        Returns:
            List of search results
        """
        return await self._duckduckgo_search_async(query, num_results)
    
    async def search_async(self, query: str, num_results: int = 10,
                          prefer_engine: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform web search asynchronously using automatically selected or preferred engine
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            prefer_engine: Preferred search engine ("google" or "duckduckgo")
            
        Returns:
            List of search results
        """
        engine = self._select_search_engine(query, prefer_engine)
        
        if engine == "google":
            return await self.google_search_async(query, num_results)
        else:
            return await self.duckduckgo_search_async(query, num_results)
    
    async def parallel_search(self, query: str, num_results: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform parallel search across multiple engines
        
        Args:
            query: Search query string
            num_results: Maximum number of results per engine
            
        Returns:
            Dictionary with results from each engine
        """
        google_task = asyncio.create_task(self.google_search_async(query, num_results))
        duckduckgo_task = asyncio.create_task(self.duckduckgo_search_async(query, num_results))
        
        google_results, duckduckgo_results = await asyncio.gather(google_task, duckduckgo_task)
        
        return {
            "google": google_results,
            "duckduckgo": duckduckgo_results
        }
    
    def close(self):
        """Close search tools resources"""
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def close_async(self):
        """Close async search tools resources"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_async()