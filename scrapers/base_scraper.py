"""Abstract base class for all web scrapers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import time
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

from models.designer import Designer
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, base_url: str, rate_limit: float = 1.0, user_agent: str = None):
        """
        Initialize the base scraper.
        
        Args:
            base_url: Base URL for the website
            rate_limit: Minimum seconds between requests
            user_agent: User agent string for requests
        """
        self.base_url = base_url.rstrip('/')
        self.rate_limiter = RateLimiter(rate_limit)
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self._robots_parser = None
    
    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if self._robots_parser is None:
            try:
                robots_url = urljoin(self.base_url, '/robots.txt')
                self._robots_parser = RobotFileParser()
                self._robots_parser.set_url(robots_url)
                self._robots_parser.read()
            except Exception as e:
                logger.warning(f"Could not fetch robots.txt: {e}")
                return True  # Allow if robots.txt is unavailable
        
        try:
            return self._robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            return True  # Allow if check fails
    
    def _fetch_page(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            BeautifulSoup object or None if failed
        """
        # Check robots.txt (warning only, don't block)
        if not self._check_robots_txt(url):
            logger.warning(f"URL may be blocked by robots.txt: {url} (continuing anyway)")
        
        # Rate limiting
        self.rate_limiter.wait()
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                # Try lxml first, fallback to html.parser if not available
                try:
                    return BeautifulSoup(response.content, 'lxml')
                except Exception:
                    return BeautifulSoup(response.content, 'html.parser')
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
        
        return None
    
    def _extract_text(self, soup: BeautifulSoup, selector, default: str = '') -> str:
        """Extract text from a CSS selector."""
        if not soup or not selector:
            return default
        # Handle list of selectors
        if isinstance(selector, list):
            for sel in selector:
                if sel:
                    result = self._extract_text(soup, str(sel), '')
                    if result:
                        return result
            return default
        # Single selector string
        try:
            element = soup.select_one(str(selector))
            if element:
                return element.get_text(strip=True)
            # When soup is the element itself (e.g. a heading passed as listing), select_one finds nothing
            if hasattr(soup, 'name') and soup.name:
                sel = str(selector).strip().lower()
                if sel == soup.name.lower():
                    return soup.get_text(strip=True) if hasattr(soup, 'get_text') else default
            return default
        except Exception:
            return default
    
    def _extract_attr(self, soup: BeautifulSoup, selector, attr: str, default: str = '') -> str:
        """Extract attribute value from a CSS selector."""
        if not soup or not selector:
            return default
        # Handle list of selectors
        if isinstance(selector, list):
            for sel in selector:
                if sel:
                    result = self._extract_attr(soup, str(sel), attr, '')
                    if result:
                        return result
            return default
        # Single selector string
        try:
            element = soup.select_one(str(selector))
            return element.get(attr, default) if element else default
        except Exception:
            return default
    
    @abstractmethod
    def scrape(self, search_query: Optional[str] = None, max_results: Optional[int] = None) -> List[Designer]:
        """
        Main scraping method.
        
        Args:
            search_query: Optional search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Designer objects
        """
        pass
    
    @abstractmethod
    def parse_designer(self, soup: BeautifulSoup, source_url: str) -> Optional[Designer]:
        """
        Parse a single designer from HTML.
        
        Args:
            soup: BeautifulSoup object of the page
            source_url: URL where the data was found
            
        Returns:
            Designer object or None if parsing failed
        """
        pass
