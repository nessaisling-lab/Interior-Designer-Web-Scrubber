"""Scraper for business directories like Yelp, Houzz, etc."""

import time
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
        self.pagination = config.get('pagination', {})  # Pagination config for list URLs
        self.selenium_helper = None
        self._page_results = []  # Store individual page results for separate export
    
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
            # Direct list page (curated list) - may have pagination
            pagination_config = self.pagination
            if pagination_config.get('enabled', False):
                # Handle paginated list
                start_page = pagination_config.get('start_page', 1)
                end_page = pagination_config.get('end_page', 1)
                first_page_no_suffix = pagination_config.get('first_page_no_suffix', True)
                url_pattern = pagination_config.get('url_pattern', '{base_url}/{page}/')
                
                logger.info(f"Scraping paginated list: pages {start_page} to {end_page}")
                
                # Use Selenium if JavaScript rendering is required
                if self.requires_js:
                    logger.info("Using Selenium for JavaScript-rendered pages")
                    if self.selenium_helper is None:
                        headless = self.config.get('headless', True)
                        stealth = self.config.get('stealth', False)
                        use_undetected = self.config.get('use_undetected', False)
                        proxy = self.config.get('proxy')  # e.g. "http://host:port" for different IP
                        self.selenium_helper = SeleniumHelper(
                            headless=headless, wait_time=15, stealth=stealth,
                            use_undetected=use_undetected, proxy=proxy
                        )
                
                # Process each page individually and export separately
                all_page_designers = []
                for page_num in range(start_page, end_page + 1):
                    # Wait before requesting next page (reduce rate-limit / blocking)
                    if page_num > start_page:
                        delay_sec = pagination_config.get('delay_between_pages', 0)
                        if delay_sec > 0:
                            logger.info(f"Waiting {delay_sec}s before loading page {page_num}...")
                            time.sleep(delay_sec)
                    # Build page URL
                    if page_num == 1 and first_page_no_suffix:
                        page_url = self.list_url
                    else:
                        # Replace {base_url} and {page} in pattern
                        page_url = url_pattern.replace('{base_url}', self.list_url.rstrip('/'))
                        page_url = page_url.replace('{page}', str(page_num))
                    
                    logger.info(f"Scraping page {page_num}: {page_url}")
                    
                    # Fetch page
                    if self.requires_js:
                        soup = self._fetch_page_with_selenium(page_url, timeout=20)
                    else:
                        soup = self._fetch_page(page_url)
                    
                    if soup:
                        page_designers = self._scrape_list_page(soup, max_results, source_url=page_url)
                        # If this looks like the site's "you are blocked" page, don't save junk
                        if page_num > 1 and self._is_block_page_result(page_designers):
                            logger.warning(f"Page {page_num} appears to be a block/access-denied page, skipping those entries")
                            page_designers = []
                        logger.info(f"Found {len(page_designers)} designers on page {page_num}")
                        
                        # Store page results separately
                        all_page_designers.append({
                            'page_num': page_num,
                            'designers': page_designers,
                            'page_url': page_url
                        })
                        
                        # Also add to combined list
                        designers.extend(page_designers)
                        
                        # Check if we've reached max_results
                        if max_results and len(designers) >= max_results:
                            logger.info(f"Reached max_results limit: {max_results}")
                            designers = designers[:max_results]
                            break
                    else:
                        logger.warning(f"Failed to fetch page {page_num}, continuing to next page")
                        continue
                
                # Clean up Selenium if used
                if self.selenium_helper:
                    self.selenium_helper.close()
                    self.selenium_helper = None
                
                # Store page results for separate export
                self._page_results = all_page_designers
                
                logger.info(f"Scraped {len(designers)} total designers from {len(all_page_designers)} pages")
                return designers
            else:
                # Single page list (no pagination)
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
    
    def _scrape_list_page(self, soup: BeautifulSoup, max_results: Optional[int] = None, source_url: Optional[str] = None) -> List[Designer]:
        """Scrape a curated list page (single page with multiple entries)."""
        designers = []
        page_source_url = source_url or self.list_url
        
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
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
        numbered_headings = []
        firm_patterns = []
        
        for heading in headings:
            text = heading.get_text(strip=True)
            # Check if heading starts with a number (e.g., "1. Designer Name" or "##### 1. Designer Name")
            if re.match(r'^\d+\.', text) or re.search(r'\d+\.\s+[A-Z]', text):
                numbered_headings.append(heading)
            # Also look for firm name patterns (e.g., "Firm Name | Architects in NY" or "Firm Name:")
            # Check if this might be a firm name by looking at following content
            next_text = ''
            next_sibling_count = 0
            for sibling in heading.next_siblings:
                if hasattr(sibling, 'get_text'):
                    next_text = sibling.get_text(strip=True)
                    if next_text:
                        next_sibling_count += 1
                        if next_sibling_count <= 3:  # Check first few siblings
                            # If next text starts with "Scope of services:" or "Website:", it's likely a firm name
                            if next_text.lower().startswith(('scope of services', 'website:', 'types of built')):
                                firm_patterns.append(heading)
                                break
                        else:
                            break
        
        if numbered_headings:
            logger.info(f"Found {len(numbered_headings)} numbered headings, treating as listings")
            listings = numbered_headings
        elif firm_patterns:
            logger.info(f"Found {len(firm_patterns)} firm name patterns, treating as listings")
            listings = firm_patterns
        
        # Alternative approach: Find all "Website:" patterns and extract firm info from surrounding context
        # This works better for pages that don't have the expected HTML structure
        # Always try this approach, especially if HTML-based listings failed
        import re
        
        # First, try to find H2 headings which contain firm names (common on paginated pages)
        # Use a LOOSE filter: include any H2 that could be a firm, only exclude obvious non-firm headings
        h2_headings = soup.find_all('h2')
        if h2_headings:
            logger.info(f"Found {len(h2_headings)} H2 headings, checking for firm entries (loose filter)")
            h2_listings = []
            for h2 in h2_headings:
                h2_text = h2.get_text(strip=True)
                h2_lower = h2_text.lower()
                
                # LOOSE: Only exclude headings we're certain are NOT firms
                # Must have reasonable length to be a firm name
                if len(h2_text) < 3 or len(h2_text) > 300:
                    continue
                # Exclude only obvious page/section headers (exact or start-with)
                excluded_starts = (
                    'architects in new york | top 100',  # Main page title
                    'top 100 architecture firms',
                    'top 50 architecture',
                    'page ', 'share on', 'share with',
                    'related posts', 'related articles',
                    'author:', 'prev post', 'next post',
                    'join now', 'how to design', 'search for',
                    'sign up', 'subscribe', 'login', 'my account',
                    'architects in göteborg', 'architects in las vegas',  # Other-city list titles
                    'interior designer in raleigh',
                )
                # Exclude only if it's clearly not a firm (very short phrases or nav)
                excluded_exact = ('share', 'related', 'page', 'next', 'prev', 'author', 'menu', 'search')
                
                skip = False
                for prefix in excluded_starts:
                    if h2_lower.startswith(prefix):
                        skip = True
                        break
                if skip:
                    continue
                if h2_lower.strip() in excluded_exact or len(h2_text.split()) <= 1 and h2_lower in ('share', 'related', 'menu'):
                    continue
                # Skip if it's purely a number (pagination)
                if h2_text.strip().isdigit():
                    continue
                
                # INCLUDE: Treat as potential firm – get as much usable data as we can
                is_firm = True
                
                if is_firm:
                    # Create a container with this H2 and its following siblings (one firm per H2)
                    from bs4 import BeautifulSoup
                    temp_soup = BeautifulSoup('', 'html.parser')
                    firm_div = temp_soup.new_tag('div')
                    firm_div.append(h2)
                    # Get next siblings until next H2 – capture all content for this firm
                    sibling_count = 0
                    for sibling in h2.next_siblings:
                        if hasattr(sibling, 'name'):
                            if sibling.name == 'h2':
                                break
                            if sibling.name in ['p', 'div', 'ul', 'li', 'strong', 'b', 'a', 'img', 'span']:
                                firm_div.append(sibling)
                                sibling_count += 1
                                if sibling_count > 40:  # Get plenty of content (Scope, Website, etc.)
                                    break
                    
                    h2_listings.append(firm_div)
                    logger.debug(f"Added H2 listing: {h2_text[:50]}...")
            
            if h2_listings:
                logger.info(f"Extracted {len(h2_listings)} firms from H2 headings")
                # Always prefer H2 listings if we found any (they're more reliable for paginated pages)
                if h2_listings:
                    listings = h2_listings
        
        # Also try text-based extraction using "Website:" patterns
        page_text = soup.get_text()
        # Find all "Website:" occurrences
        website_matches = list(re.finditer(r'Website:\s*(?:www\.)?([^\s\n,]+)', page_text, re.IGNORECASE))
        if website_matches and (not listings or len(website_matches) > len(listings)):
            logger.info(f"Found {len(website_matches)} 'Website:' patterns, extracting firm contexts")
            # For each website match, find the firm name before it
            new_listings = []
            for match in website_matches:
                # Look backwards for firm name (usually within 400 chars)
                start_pos = max(0, match.start() - 400)
                context = page_text[start_pos:match.start()]
                # Find firm name pattern (text before "Scope of services:" or similar, or H2 heading text)
                firm_match = re.search(r'([A-Z][A-Za-z0-9\s&|,.\-]+?)(?:\s*\|\s*Architects?\s+in\s+[^|]*)?(?:\s*:)?\s*(?:Scope of services|Website|Types of Built|Top Architecture)', context, re.IGNORECASE | re.DOTALL)
                if firm_match:
                    firm_name = firm_match.group(1).strip()
                    # Clean up firm name
                    firm_name = re.sub(r'^\d+\.?\s*', '', firm_name)
                    firm_name = re.sub(r'\s*\|\s*Architects?\s+in\s+[^|]*$', '', firm_name, flags=re.IGNORECASE)
                    firm_name = re.sub(r'\s*\|\s*Top Architecture Firms.*$', '', firm_name, flags=re.IGNORECASE)
                    firm_name = re.sub(r':\s*$', '', firm_name)
                    firm_name = ' '.join(firm_name.split())
                    # Skip if too short, too long, or looks like intro text
                    if 3 < len(firm_name) < 100 and not firm_name.lower().startswith(('new york architecture', 'rtf has', 'architects in new york', 'top 100')):
                        # Create a pseudo-element for this firm
                        from bs4 import BeautifulSoup
                        temp_soup = BeautifulSoup('', 'html.parser')
                        firm_div = temp_soup.new_tag('div')
                        # Include more context around the website
                        context_end = min(len(page_text), match.end() + 150)
                        firm_div.string = context + page_text[match.start():context_end]
                        new_listings.append(firm_div)
            
            if new_listings:
                logger.info(f"Extracted {len(new_listings)} firms from Website patterns")
                # Use website pattern results if we found more than HTML-based listings, or if HTML-based failed
                if len(new_listings) > len(listings) or not listings:
                    listings = new_listings
        
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
            
            designer = self._parse_listing(listing_context, page_source_url)
            if designer:
                designers.append(designer)
                
                if max_results and len(designers) >= max_results:
                    logger.info(f"Reached max_results limit: {max_results}")
                    break
        
        logger.info(f"Scraped {len(designers)} designers from list page")
        return designers
    
    def _fetch_page_with_selenium(self, url: str, timeout: Optional[int] = None) -> Optional[BeautifulSoup]:
        """
        Fetch page using Selenium for JavaScript-rendered content.
        
        Args:
            url: URL to fetch
            timeout: Optional timeout override
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            if self.selenium_helper is None:
                headless = self.config.get('headless', True)
                stealth = self.config.get('stealth', False)
                use_undetected = self.config.get('use_undetected', False)
                proxy = self.config.get('proxy')
                self.selenium_helper = SeleniumHelper(
                    headless=headless, wait_time=15, stealth=stealth,
                    use_undetected=use_undetected, proxy=proxy
                )
            
            # Try to wait for a listing element to appear, but don't fail if not found
            # For paginated pages, we'll wait for body content instead of specific selector
            wait_selector = None
            listing_selectors = self.selectors.get('listing', [])
            if listing_selectors:
                # Use the first listing selector to wait for content
                wait_selector = listing_selectors[0] if isinstance(listing_selectors, list) else listing_selectors
            
            # Use body as fallback selector - pages should always have body
            soup = self.selenium_helper.get_soup(url, wait_for_selector=wait_selector or 'body', timeout=timeout or 20)
            return soup
            
        except Exception as e:
            logger.error(f"Error fetching page with Selenium: {e}")
            return None
    
    def _is_block_page_result(self, designers: List[Designer]) -> bool:
        """Return True if this list looks like the re-thinkingthefuture block/access-denied page."""
        if len(designers) != 3:
            return False
        names = [d.name.strip().lower() for d in designers]
        block_phrases = (
            'you are unable to access',
            'why have i been blocked',
            'what can i do to resolve',
        )
        matches = sum(1 for ph in block_phrases if any(ph in n for n in names))
        return matches >= 2  # at least 2 of the 3 block-page phrases present
    
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
            
            # Clean up name (remove numbers, extra whitespace, suffixes)
            if name:
                import re
                # Remove leading numbers and dots (e.g., "1. Peter Marino" -> "Peter Marino")
                name = re.sub(r'^\d+\.?\s*', '', name).strip()
                # Remove trailing patterns like "| Architects in NY" or ": | Architects in New York"
                name = re.sub(r'\s*\|\s*Architects?\s+in\s+[^|]*$', '', name, flags=re.IGNORECASE)
                name = re.sub(r':\s*\|\s*Architects?\s+in\s+[^|]*$', '', name, flags=re.IGNORECASE)
                name = re.sub(r':\s*$', '', name)  # Remove trailing colon
                # Remove extra whitespace
                name = ' '.join(name.split())
                
                # LOOSE filter: only skip entries we're certain are invalid
                invalid_patterns = [
                    r'^no matches',
                    r'^no results',
                    r'^try again',
                    r'^search\s',
                    r'^filter\s',
                    r'^loading',
                    r'^error\s',
                ]
                name_lower = name.lower()
                if any(re.search(pattern, name_lower) for pattern in invalid_patterns):
                    logger.debug(f"Skipping invalid entry: {name}")
                    return None
                # Skip only very obvious non-firms (exact phrase matches)
                if name_lower == 'architecture firms in new york' or name_lower.startswith('new york architecture is unique'):
                    return None
                
                # Only skip if name is clearly too long for a firm (e.g. whole paragraph)
                if len(name) > 400:
                    logger.debug(f"Skipping overly long entry: {name[:50]}...")
                    return None
            
            if not name or len(name) < 2:  # Name must be at least 2 characters (allow abbreviations)
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
            
            # Also look for "Website:" pattern in text (common in list pages like re-thinkingthefuture)
            if not website:
                listing_text = listing_soup.get_text()
                import re
                # Look for "Website: www.example.com" or "Website: example.com"
                website_match = re.search(r'Website:\s*(?:www\.)?([^\s\n,]+)', listing_text, re.IGNORECASE)
                if website_match:
                    website = website_match.group(1).strip()
                    # Remove trailing punctuation
                    website = re.sub(r'[.,;:]+$', '', website)
                    if not website.startswith('http'):
                        if not website.startswith('www.'):
                            website = 'http://www.' + website
                        else:
                            website = 'http://' + website
            
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
