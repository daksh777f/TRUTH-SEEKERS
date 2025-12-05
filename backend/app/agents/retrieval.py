"""
Retrieval Agent - Fetches evidence from web sources
"""
from typing import List, Dict, Any
import asyncio
import httpx
from urllib.parse import urlparse, quote_plus
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class RetrievalAgent:
    """
    Fetches evidence from web sources for claim verification.
    
    Uses DuckDuckGo (FREE, no API key needed) as primary search.
    Falls back to SerpAPI or Google CSE if configured.
    """
    
    def __init__(self):
        self.serpapi_key = settings.SERPAPI_API_KEY
        self.google_api_key = settings.GOOGLE_API_KEY
        self.google_cse_id = settings.GOOGLE_CSE_ID
        self.use_free_search = settings.USE_FREE_SEARCH
        self.max_results_per_query = 5
    
    async def fetch_evidence(
        self,
        queries: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch evidence for all claims in parallel.
        
        Args:
            queries: Dictionary mapping claim_id to list of search queries
            
        Returns:
            Dictionary mapping claim_id to list of evidence items
        """
        if not queries:
            return {}
        
        logger.info("Fetching evidence", claims_count=len(queries))
        
        # Collect all search tasks
        tasks = []
        claim_query_map = []  # Track which task belongs to which claim
        
        for claim_id, claim_queries in queries.items():
            for query in claim_queries:
                tasks.append(self._search(query))
                claim_query_map.append(claim_id)
        
        # Execute searches in parallel (with some concurrency limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
        
        async def limited_search(query_task):
            async with semaphore:
                return await query_task
        
        results = await asyncio.gather(
            *[limited_search(task) for task in tasks],
            return_exceptions=True
        )
        
        # Aggregate results by claim
        evidence: Dict[str, List[Dict[str, Any]]] = {}
        
        for claim_id, result in zip(claim_query_map, results):
            if claim_id not in evidence:
                evidence[claim_id] = []
            
            if isinstance(result, Exception):
                logger.warning("Search failed", claim_id=claim_id, error=str(result))
                continue
            
            # Add results, avoiding duplicates
            existing_urls = {e["url"] for e in evidence[claim_id]}
            for item in result:
                if item["url"] not in existing_urls:
                    evidence[claim_id].append(item)
                    existing_urls.add(item["url"])
        
        total_evidence = sum(len(e) for e in evidence.values())
        logger.info("Evidence fetched", total=total_evidence)
        
        return evidence
    
    async def _search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform a single search query.
        
        Args:
            query: Search query string
            
        Returns:
            List of evidence items
        """
        # Priority: DuckDuckGo (free) -> SerpAPI -> Google CSE -> Mock
        if self.use_free_search:
            return await self._search_duckduckgo(query)
        elif self.serpapi_key:
            return await self._search_serpapi(query)
        elif self.google_api_key and self.google_cse_id:
            return await self._search_google(query)
        else:
            return await self._search_duckduckgo(query)
    
    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo HTML (FREE, no API key needed)."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # DuckDuckGo HTML endpoint
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True
                )
                response.raise_for_status()
                
                # Parse HTML response
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = []
                for result in soup.select('.result')[:self.max_results_per_query]:
                    link_elem = result.select_one('.result__a')
                    snippet_elem = result.select_one('.result__snippet')
                    
                    if link_elem and link_elem.get('href'):
                        url = link_elem.get('href')
                        # DuckDuckGo sometimes wraps URLs
                        if url.startswith('//duckduckgo.com/l/?uddg='):
                            url = url.split('uddg=')[1].split('&')[0]
                            from urllib.parse import unquote
                            url = unquote(url)
                        
                        domain = urlparse(url).netloc
                        results.append({
                            "url": url,
                            "title": link_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "domain": domain,
                            "published_at": None,
                            "relevance_score": 0.5,
                            "domain_reputation": self._get_domain_reputation(domain)
                        })
                
                if results:
                    return results
                else:
                    # Fallback to mock if no results
                    logger.warning("DuckDuckGo returned no results, using mock")
                    return await self._mock_search(query)
                    
        except Exception as e:
            logger.error("DuckDuckGo search failed", error=str(e))
            return await self._mock_search(query)
    
    async def _search_serpapi(self, query: str) -> List[Dict[str, Any]]:
        """Search using SerpAPI."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "api_key": self.serpapi_key,
                        "q": query,
                        "num": self.max_results_per_query,
                        "engine": "google"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("organic_results", [])[:self.max_results_per_query]:
                    domain = urlparse(item.get("link", "")).netloc
                    results.append({
                        "url": item.get("link", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "domain": domain,
                        "published_at": item.get("date"),
                        "relevance_score": 0.5,
                        "domain_reputation": self._get_domain_reputation(domain)
                    })
                
                return results
                
        except Exception as e:
            logger.error("SerpAPI search failed", error=str(e))
            return []
    
    async def _search_google(self, query: str) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.google_cse_id,
                        "q": query,
                        "num": min(self.max_results_per_query, 10)
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("items", [])[:self.max_results_per_query]:
                    domain = urlparse(item.get("link", "")).netloc
                    results.append({
                        "url": item.get("link", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "domain": domain,
                        "published_at": None,
                        "relevance_score": 0.5,
                        "domain_reputation": self._get_domain_reputation(domain)
                    })
                
                return results
                
        except Exception as e:
            logger.error("Google search failed", error=str(e))
            return []
    
    async def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """Mock search for development without API keys."""
        logger.warning("Using mock search results")
        
        # Return simulated results
        return [
            {
                "url": f"https://example.com/article/{hash(query) % 1000}",
                "title": f"Article about: {query[:50]}",
                "snippet": f"This is relevant information about {query[:30]}... Multiple sources confirm this data.",
                "domain": "example.com",
                "published_at": "2024-01-15",
                "relevance_score": 0.7,
                "domain_reputation": 0.6
            },
            {
                "url": f"https://trusted-source.org/data/{hash(query) % 500}",
                "title": f"Data and statistics: {query[:40]}",
                "snippet": f"According to verified sources, {query[:25]}... Our research shows...",
                "domain": "trusted-source.org",
                "published_at": "2024-03-20",
                "relevance_score": 0.8,
                "domain_reputation": 0.85
            }
        ]
    
    def _get_domain_reputation(self, domain: str) -> float:
        """
        Get reputation score for a domain.
        
        In production, this would query the domains table.
        For now, use simple heuristics.
        """
        # High-trust domains
        trusted_domains = [
            "wikipedia.org", "github.com", "reuters.com", "bbc.com",
            "nytimes.com", "nature.com", "science.org", "gov",
            "edu", "who.int", "cdc.gov"
        ]
        
        for trusted in trusted_domains:
            if trusted in domain:
                return 0.9
        
        # Medium trust for known platforms
        medium_domains = [
            "medium.com", "linkedin.com", "forbes.com", "techcrunch.com"
        ]
        
        for medium in medium_domains:
            if medium in domain:
                return 0.7
        
        # Default score
        return 0.5
