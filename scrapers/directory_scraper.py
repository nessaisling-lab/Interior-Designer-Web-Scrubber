"""Scraper for business directories like Yelp, Houzz, etc."""

from typing import List, Optional, Dict
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from models.designer import Designer
from utils.logger import get_logger
from utils.selenium_helper import SeleniumHelper

logger = get_logger(__name__)


class DirectoryScraper(BaseScraper):
    """Scraper for business directory websites."""
    
    def __init__(self, config: Dict):
        """
        Initialize directory scraper with configuration.
        
        Args:
            config: Configuration dictionary with:
                - base_url: Base URL of the directory
                - search_url_template: URL template for searches (with {query} placeholder)
                - selectors: Dict of CSS selectors for data extraction
                - rate_limit: Rate limit in seconds
        """
        super().__init__(
            base_url=config.get('base_url', ''),
            rate_limit=config.get('rate_limit', 1.0),
            user_agent=config.get('user_agent')
        )
        self.config = config
        self.search_url_template = config.get('search_url_template', '')
        self.list_url = config.get('list_url', '')  # For curated list pages
        self.selectors = config.get('selectors', {})
        self.requires_js = config.get('requires_js', False)  # Whether JavaScript rendering is needed
        self.selenium_helper = None
    
    def scrape(self, search_query: Optional[str] = None, max_results: Optional[int] = None) -> List[Designer]:
        """
        Scrape designers from the directory.
        
        Args:
            search_query: Search query (e.g., "interior designer") - ignored if list_url is set
            max_results: Maximum number of results
            
        Returns:
            List of Designer objects
        """
        designers = []
        
        # Check if this is a direct list URL or search-based
        if self.list_url:
            # Direct list page (curated list)
            logger.info(f"Scraping curated list: {self.list_url}")
            
            # Use Selenium if JavaScript rendering is required
            if self.requires_js:
                logger.info("Using Selenium for JavaScript-rendered page")
                soup = self._fetch_page_with_selenium(self.list_url)
            else:
                soup = self._fetch_page(self.list_url)
            
            if soup:
                designers = self._scrape_list_page(soup, max_results)
            
            # Clean up Selenium if used
            if self.selenium_helper:
                self.selenium_helper.close()
                self.selenium_helper = None
            
            return designers
        
        if not self.search_url_template:
            logger.error("No search_url_template or list_url configured")
            return designers
        
        # Build search URL
        if search_query:
            search_url = self.search_url_template.format(query=search_query)
        else:
            search_url = self.search_url_template.format(query='interior designer')
        
        logger.info(f"Scraping directory: {search_url}")
        
        page_num = 1
        while True:
            # Handle pagination
            page_url = self._build_page_url(search_url, page_num)
            soup = self._fetch_page(page_url)
            
            if not soup:
                break
            
            # Extract designer listings
            listing_selectors = self.selectors.get('listing', [])
            listings = []
            
            for selector in listing_selectors:
                listings = soup.select(selector)
                if listings:
                    break
            
            if not listings:
                logger.info(f"No listings found on page {page_num}")
                break
            
            # Parse each listing
            for listing in listings:
                designer = self._parse_listing(listing, page_url)
                if designer:
                    designers.append(designer)
                    
                    if max_results and len(designers) >= max_results:
                        logger.info(f"Reached max_results limit: {max_results}")
                        return designers
            
            # Check for next page
            if not self._has_next_page(soup, page_num):
                break
            
            page_num += 1
        
        logger.info(f"Scraped {len(designers)} designers from directory")
        return designers
    
    def _scrape_list_page(self, soup: BeautifulSoup, max_results: Optional[int] = None) -> List[Designer]:
        """Scrape a curated list page (single page with multiple entries)."""
        designers = []
        
        # Extract designer listings
        listing_selectors = self.selectors.get('listing', [])
        listings = []
        
        for selector in listing_selectors:
            found_listings = soup.select(selector)
            if found_listings:
                listings = found_listings
                logger.info(f"Found {len(listings)} listings using selector: {selector}")
                break
        
        # Always try to find headings with designer names (numbered entries) first for curated lists
        import re
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        numbered_headings = []
        for heading in headings:
            text = heading.get_text(strip=True)
            # Check if heading starts with a number (e.g., "1. Designer Name" or "##### 1. Designer Name")
            if re.match(r'^\d+\.', text) or re.search(r'\d+\.\s+[A-Z]', text):
                numbered_headings.append(heading)
        
        if numbered_headings:
            logger.info(f"Found {len(numbered_headings)} numbered headings, treating as listings")
            listings = numbered_headings
        
        if not listings:
            logger.warning("No listings found with configured selectors")
            # Try to find JSON-LD structured data as fallback
            json_scripts = soup.find_all('script', type='application/ld+json')
            if json_scripts:
                logger.info(f"Found {len(json_scripts)} JSON-LD scripts, but structured data extraction not yet implemented")
            # Check if page might be JavaScript-rendered
            page_text = soup.get_text()
            if 'loading' in page_text.lower() or 'javascript' in str(soup).lower():
                logger.warning("Page appears to be JavaScript-rendered. Consider using Selenium for dynamic content.")
            return designers
        
        # Parse each listing
        for listing in listings:
            # For headings, get the parent container or next siblings for additional info
            listing_context = listing
            if listing.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Try to get parent container first
                parent = listing.find_parent(['article', 'div', 'section', 'p'])
                if parent and parent != soup:  # Don't use the whole page
                    # Check if parent contains multiple headings (then it's too broad)
                    other_headings = parent.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if len(other_headings) <= 3:  # If only a few headings, use parent
                        listing_context = parent
                    else:
                        # Create a container with this heading and its following content
                        from bs4 import BeautifulSoup
                        temp_soup = BeautifulSoup('', 'html.parser')
                        temp_div = temp_soup.new_tag('div')
                        temp_div.append(listing)
                        # Get next siblings until next heading
                        for sibling in listing.next_siblings:
                            if hasattr(sibling, 'name') and sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                break
                            if hasattr(sibling, 'extract'):
                                temp_div.append(sibling)
                            if len(temp_div.contents) > 10:  # Limit content
                                break
                        listing_context = temp_div
                else:
                    # Create a container with this heading and its following content
                    from bs4 import BeautifulSoup
                    temp_soup = BeautifulSoup('', 'html.parser')
                    temp_div = temp_soup.new_tag('div')
                    temp_div.append(listing)
                    # Get next siblings until next heading
                    for sibling in listing.next_siblings:
                        if hasattr(sibling, 'name') and sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if hasattr(sibling, 'extract'):
                            temp_div.append(sibling)
                        if len(temp_div.contents) > 10:  # Limit content
                            break
                    listing_context = temp_div
            
            designer = self._parse_listing(listing_context, self.list_url)
            if designer:
                designers.append(designer)
                
                if max_results and len(designers) >= max_results:
                    logger.info(f"Reached max_results limit: {max_results}")
                    break
        
        logger.info(f"Scraped {len(designers)} designers from list page")
        return designers
    
    def _fetch_page_with_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch page using Selenium for JavaScript-rendered content.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            if self.selenium_helper is None:
                self.selenium_helper = SeleniumHelper(headless=True, wait_time=15)
            
            # Try to wait for a listing element to appear
            wait_selector = None
            listing_selectors = self.selectors.get('listing', [])
            if listing_selectors:
                # Use the first listing selector to wait for content
                wait_selector = listing_selectors[0] if isinstance(listing_selectors, list) else listing_selectors
            
            soup = self.selenium_helper.get_soup(url, wait_for_selector=wait_selector)
            return soup
            
        except Exception as e:
            logger.error(f"Error fetching page with Selenium: {e}")
            return None
    
    def _build_page_url(self, base_url: str, page_num: int) -> str:
        """Build URL for a specific page number."""
        if page_num == 1:
            return base_url
        # Try common pagination patterns
        if '?' in base_url:
            return f"{base_url}&page={page_num}"
        else:
            return f"{base_url}?page={page_num}"
    
    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        """Check if there's a next page."""
        next_selectors = self.selectors.get('next_page', [])
        for selector in next_selectors:
            next_link = soup.select_one(selector)
            if next_link:
                return True
        return False
    
    def _parse_listing(self, listing_soup: BeautifulSoup, source_url: str) -> Optional[Designer]:
        """Parse a single listing from the directory."""
        try:
            # Extract name - try multiple selectors
            name_selectors = self.selectors.get('name', '')
            name = ''
            if isinstance(name_selectors, list):
                for selector in name_selectors:
                    if selector:  # Ensure selector is not empty
                        name = self._extract_text(listing_soup, str(selector))
                        if name:
                            break
            elif name_selectors:
                name = self._extract_text(listing_soup, str(name_selectors))
            
            # Clean up name (remove numbers, extra whitespace)
            if name:
                import re
                # Remove leading numbers and dots (e.g., "1. Peter Marino" -> "Peter Marino")
                name = re.sub(r'^\d+\.?\s*', '', name).strip()
                # Remove extra whitespace
                name = ' '.join(name.split())
                
                # Filter out invalid entries
                invalid_patterns = [
                    r'no matches',
                    r'no results',
                    r'try again',
                    r'search',
                    r'filter',
                    r'loading',
                    r'error',
                ]
                name_lower = name.lower()
                if any(re.search(pattern, name_lower) for pattern in invalid_patterns):
                    logger.debug(f"Skipping invalid entry: {name}")
                    return None
            
            if not name or len(name) < 3:  # Name must be at least 3 characters
                return None
            
            # Extract website/URL - try multiple methods
            website = None
            website_selectors = self.selectors.get('website', '')
            
            if isinstance(website_selectors, list):
                for selector in website_selectors:
                    if selector:  # Ensure selector is not empty
                        website = self._extract_attr(listing_soup, str(selector), 'href')
                        if website:
                            break
            elif website_selectors:
                website = self._extract_attr(listing_soup, str(website_selectors), 'href')
            
            # Also try to find links in the listing that might be designer websites
            if not website:
                links = listing_soup.find_all('a', href=True)
                potential_websites = []
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    href_lower = href.lower()
                    
                    # Skip social media and internal links
                    if any(x in href_lower for x in ['instagram', 'facebook', 'twitter', 'linkedin', 'pinterest', 'youtube']):
                        continue
                    if 'bocadolobo' in href_lower or href_lower.startswith('/'):
                        continue
                    
                    # Look for external HTTP links
                    if href.startswith('http'):
                        # Prioritize links that seem like designer websites
                        if any(word in text for word in ['website', 'visit', 'www']):
                            potential_websites.insert(0, href)  # Higher priority
                        else:
                            potential_websites.append(href)
                
                if potential_websites:
                    website = potential_websites[0]
            
            # Try to extract website from image source links (sometimes images link to designer sites)
            if not website:
                images = listing_soup.find_all('img')
                for img in images:
                    parent_link = img.find_parent('a', href=True)
                    if parent_link:
                        href = parent_link.get('href', '')
                        if href.startswith('http') and 'bocadolobo' not in href.lower():
                            website = href
                            break
            
            if website and not website.startswith('http'):
                from urllib.parse import urljoin
                website = urljoin(self.base_url, website)
            
            # Extract phone
            phone = self._extract_text(listing_soup, self.selectors.get('phone', ''))
            
            # Extract address components
            address = self._extract_text(listing_soup, self.selectors.get('address', ''))
            city = self._extract_text(listing_soup, self.selectors.get('city', ''))
            state = self._extract_text(listing_soup, self.selectors.get('state', ''))
            zip_code = self._extract_text(listing_soup, self.selectors.get('zip_code', ''))
            
            # Extract specialty if available
            specialty = self._extract_text(listing_soup, self.selectors.get('specialty', ''))
            
            # If website is available, try to get more details
            email = None
            if website:
                email = self._try_extract_email_from_detail_page(website)
            
            designer = Designer(
                name=name,
                email=email,
                phone=phone,
                website=website,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                specialty=specialty,
                source_url=source_url
            )
            
            return designer
            
        except Exception as e:
            import traceback
            logger.error(f"Error parsing listing: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _try_extract_email_from_detail_page(self, url: str) -> Optional[str]:
        """Try to extract email from detail page."""
        try:
            soup = self._fetch_page(url)
            if not soup:
                return None
            
            # Look for email patterns in text
            import re
            text = soup.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            
            # Filter out common non-contact emails
            filtered = [e for e in emails if not any(x in e.lower() for x in ['example.com', 'noreply', 'no-reply'])]
            return filtered[0] if filtered else None
            
        except Exception:
            return None
    
    def parse_designer(self, soup: BeautifulSoup, source_url: str) -> Optional[Designer]:
        """Parse designer from a detail page."""
        return self._parse_listing(soup, source_url)
