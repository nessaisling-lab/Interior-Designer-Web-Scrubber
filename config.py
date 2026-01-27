"""Configuration for website scrapers."""

# Global settings
GLOBAL_CONFIG = {
    'output_file': 'output/designers.csv',
    'log_level': 'INFO',
    'log_file': 'logs/scraper.log',
    'default_rate_limit': 1.0,  # seconds between requests
    'default_max_results': None,  # None = no limit
}

# Website-specific configurations
# Each entry defines selectors and settings for a specific directory website
WEBSITE_CONFIGS = {
    'yelp': {
        'base_url': 'https://www.yelp.com',
        'search_url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc=',
        'rate_limit': 2.0,  # Be respectful with Yelp
        'selectors': {
            'listing': [
                'div[class*="businessName"]',
                'a[class*="businessName"]',
                '.business-name'
            ],
            'name': 'h3 a, .business-name, [class*="businessName"]',
            'website': 'a[href*="biz_redir"]',
            'phone': '[class*="phone"]',
            'address': '[class*="address"]',
            'city': '[class*="city"]',
            'state': '[class*="state"]',
            'zip_code': '[class*="zip"]',
            'next_page': 'a[aria-label="Next"]',
        }
    },
    'houzz': {
        'base_url': 'https://www.houzz.com',
        'search_url_template': 'https://www.houzz.com/professionals/interior-designer/c/{query}',
        'rate_limit': 1.5,
        'selectors': {
            'listing': [
                '.hz-pro-search-result',
                '.hz-pro-card',
                '[class*="pro-card"]'
            ],
            'name': 'h3 a, .hz-pro-card__title',
            'website': 'a[href*="professional"]',
            'phone': '[class*="phone"]',
            'address': '[class*="address"]',
            'city': '[class*="city"]',
            'state': '[class*="state"]',
            'specialty': '[class*="specialty"]',
            'next_page': 'a[aria-label="Next"], .hz-pagination-next',
        }
    },
    'bocadolobo': {
        'base_url': 'https://www.bocadolobo.com',
        'list_url': 'https://www.bocadolobo.com/en/inspiration-and-ideas/50-best-interior-designers-in-new-york/',
        'rate_limit': 2.0,  # Be respectful
        'selectors': {
            # Try to find entries - look for numbered sections or article entries
            'listing': [
                'article',
                'div[class*="entry"]',
                'div[class*="post"]',
                'div[class*="designer"]',
                'section',
                'h5',  # Headings with designer names
            ],
            # Designer names are in headings (h5, h4, etc.) with format "1. Designer Name"
            'name': [
                'h5',
                'h4',
                'h3',
                'h2',
                '[class*="title"]',
                '[class*="name"]',
                'strong',
            ],
            # Look for links that might be designer websites
            'website': [
                'a[href*="http"]',
                'a[href*="www"]',
            ],
            # Try to extract from description text
            'specialty': [
                'p',
                '[class*="description"]',
                '[class*="content"]',
            ],
        }
    },
    'asid': {
        'base_url': 'https://designfinder.asid.org',
        'list_url': 'https://designfinder.asid.org/search?FreeTextSearch=&SubCategoryIds=a12a6fac-88fb-4b09-8cbc-1bbe0f7f729e%2C773845e4-7f77-4c95-a5e1-f04fb3fa27d2%2Ca51c5200-98d7-49f9-972f-dce37383826e%2C856354b9-cc24-40e2-8c83-73c0c1c782f2%2C319e47c4-007f-4a8a-97f5-68321755b636%2C1c7c75ce-1fa5-490b-9fa3-c3b5942707e1%2C9a66be6b-6d6c-4fda-8cc0-98fc5445d73f%2C3af30c4f-1e0a-4973-af1b-b2fb8846986b%2Cabea894a-f877-4cd8-8031-e19e271bb62b%2C3276001b-8176-4a6b-8b8f-e1840406c2a0%2C&SortBy=Distance&View=List&ContentType=Suppliers&ListingType=Designers%2B%26%2BFirms&ListingTypeId=4f3a8c49-db60-477b-9751-31fda707d523&DemographicsSubCategoryId=&MemberPerks=false&ReferFriendCampaign=false&Latitude=40.7460972&Longitude=-73.9799209&Distance=17&PlaceName=231-237+Lexington+Ave%2C+New+York%2C+NY%2C+10016%2C+USA&OpenStore=false&IsStandAlone=false&UrlTitle=&UrlSubtitle=&DistanceSearchHQ=true&DistanceSearchBranches=true&isMapViewToggleSwitchEnabled=false&IsShowAds=false',
        'rate_limit': 2.0,
        'output_file': 'output/ASID results.csv',  # Custom output file for ASID
        'requires_js': True,  # This site requires JavaScript rendering (Selenium needed)
        'selectors': {
            # Try various patterns - ASID might use different structures
            'listing': [
                'div[data-supplier-id]',  # Common pattern for supplier listings
                '[class*="supplier-card"]',
                '[class*="supplier-item"]',
                '[class*="result-card"]',
                '[class*="result-item"]',
                '[class*="listing-card"]',
                '[class*="listing-item"]',
                'div[class*="supplier"]',
                'div[class*="result"]',
                'div[class*="listing"]',
                'article',
                'li[class*="result"]',
                '.search-result',
                '.listing-item',
                'div[itemtype*="Organization"]',
            ],
            'name': [
                'h1', 'h2', 'h3', 'h4', 'h5',
                '[class*="supplier-name"]',
                '[class*="company-name"]',
                '[class*="name"]',
                '[class*="title"]',
                '[class*="company"]',
                'a[class*="name"]',
                '[itemprop="name"]',
                'h2 a', 'h3 a', 'h4 a',
            ],
            'website': [
                'a[href*="http"][target="_blank"]',
                'a[href^="http"]',
                'a[class*="website"]',
                'a[class*="url"]',
                '[class*="website"] a',
                '[class*="url"] a',
                '[itemprop="url"]',
            ],
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
                '[data-phone]',
                '[itemprop="telephone"]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
                '[data-email]',
                '[itemprop="email"]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
                '[class*="street"]',
                '[itemprop="streetAddress"]',
                '[itemprop="address"]',
            ],
            'city': [
                '[class*="city"]',
                '[itemprop="addressLocality"]',
            ],
            'state': [
                '[class*="state"]',
                '[itemprop="addressRegion"]',
            ],
            'zip_code': [
                '[class*="zip"]',
                '[class*="postal"]',
                '[itemprop="postalCode"]',
            ],
            'specialty': [
                '[class*="specialty"]',
                '[class*="category"]',
                '[class*="service"]',
                '[class*="expertise"]',
            ],
            'next_page': [
                'a[aria-label*="Next"]',
                'a[aria-label*="next"]',
                '.pagination-next',
                'a[class*="next"]',
                'button[class*="next"]',
            ],
        }
    },
    'rethinkingthefuture': {
        'base_url': 'https://www.re-thinkingthefuture.com',
        'list_url': 'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/',
        # Explicit page URLs to scrape (no pagination). When set, list_url/pagination are ignored.
        'list_urls': [
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/2/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/3/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/4/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/5/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/6/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/7/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/8/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/9/',
            'https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york/10/',
            # Add more URLs as needed, e.g. /3/, /4/, ...
        ],
        'rate_limit': 2.0,
        'output_file': 'output/rethinkingthefuture_results.csv',  # Custom output file
        'requires_js': True,  # This site blocks automated requests, use Selenium
        'headless': False,  # Run visible browser to reduce block detection
        'stealth': True,  # Use Chrome flags to look less like automation
        'use_undetected': True,  # Use undetected-chromedriver to evade bot/block pages
        'delay_between_pages': 30,  # Seconds between list_urls (when using list_urls)
        # 'proxy': 'http://host:port',  # Optional: use a proxy for different IP (no VPN); e.g. free/paid proxy
        'pagination': {
            'enabled': True,
            'start_page': 1,
            'end_page': 1,  # Site blocks pages 2–10; set to 10 and use delay/stealth to try more
            'url_pattern': '{base_url}/{page}/',  # Pattern: base_url/2/, base_url/3/, etc.
            'first_page_no_suffix': True,  # Page 1 has no /1/ suffix
            'delay_between_pages': 30,  # Seconds to wait before loading next page (reduce blocking)
        },
        'selectors': {
            # Look for numbered list entries - similar to bocadolobo pattern
            'listing': [
                'article',
                'div[class*="entry"]',
                'div[class*="post"]',
                'div[class*="firm"]',
                'div[class*="architect"]',
                'div[class*="company"]',
                'section',
                'li',
                'div[class*="item"]',
                'div[class*="listing"]',
                'div[class*="card"]',
            ],
            # Names are likely in headings (numbered format like "1. Firm Name")
            'name': [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                '[class*="title"]',
                '[class*="name"]',
                '[class*="firm-name"]',
                '[class*="architect-name"]',
                '[class*="company-name"]',
                'strong',
                'a[class*="title"]',
                'h2 a', 'h3 a', 'h4 a',
            ],
            # Look for website links (external links to firm websites)
            'website': [
                'a[href^="http"]',
                'a[href*="www"]',
                'a[class*="website"]',
                'a[class*="url"]',
                'a[class*="link"]',
                '[class*="website"] a',
                '[class*="url"] a',
            ],
            # Contact information - may be in paragraphs or specific sections
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
                '[class*="contact"]',
                '[data-phone]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
                '[class*="contact"]',
                '[data-email]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
                '[class*="street"]',
                '[class*="office"]',
            ],
            'city': [
                '[class*="city"]',
            ],
            'state': [
                '[class*="state"]',
            ],
            'zip_code': [
                '[class*="zip"]',
                '[class*="postal"]',
            ],
            'specialty': [
                '[class*="specialty"]',
                '[class*="description"]',
                '[class*="content"]',
                '[class*="about"]',
                'p',
            ],
        }
    },
    'archello': {
        'base_url': 'https://archello.com',
        'list_url': 'https://archello.com/news/25-best-architecture-firms-in-new-york-city',
        'rate_limit': 2.0,
        'output_file': 'output/archello_results.csv',
        'requires_js': True,  # News/article pages often need JS; set False if plain HTTP works
        'selectors': {
            # Article list: numbered entries like "1. Diller Scofidio + Renfro", "2. Skidmore, Owings & Merrill"
            'listing': [
                'article',
                'div[class*="article"]',
                'div[class*="content"]',
                'div[class*="entry"]',
                'section',
                'div[class*="firm"]',
                'div[class*="news"]',
                'li',
            ],
            'name': [
                'h2',
                'h3',
                'h4',
                'strong',
                '[class*="title"]',
                '[class*="firm"]',
                '[class*="name"]',
                'h2 a',
                'h3 a',
            ],
            'website': [
                'a[href^="http"]',
                'a[href*="www"]',
                'a[href*="archello.com/firms"]',
                '[class*="website"] a',
                '[class*="url"] a',
            ],
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
            ],
            'specialty': [
                'p',
                '[class*="description"]',
                '[class*="content"]',
            ],
        }
    },
    'inven': {
        'base_url': 'https://www.inven.ai',
        'list_url': 'https://www.inven.ai/company-lists/top-21-residential-construction-companies-in-new-york',
        'rate_limit': 2.0,
        'output_file': 'output/inven_results.csv',
        'requires_js': True,  # Modern SaaS list page; set False if plain HTTP works
        'selectors': {
            # List: "1. The Beechwood Organization|Beechwood Homes NY & Carolinas", "2. Forbes Capretto Homes", etc.
            'listing': [
                'article',
                'div[class*="content"]',
                'div[class*="list"]',
                'div[class*="company"]',
                'section',
                'li',
                'div[class*="entry"]',
                'div[class*="item"]',
            ],
            'name': [
                'h2',
                'h3',
                'h4',
                'strong',
                '[class*="title"]',
                '[class*="company-name"]',
                '[class*="name"]',
                'h2 a',
                'h3 a',
            ],
            'website': [
                'a[href^="http"]',
                'a[href*="www"]',
                '[class*="website"] a',
                '[class*="url"] a',
            ],
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
                '[class*="headquarter"]',
                '[class*="headquarters"]',
            ],
            'city': [
                '[class*="city"]',
            ],
            'state': [
                '[class*="state"]',
            ],
            'specialty': [
                'p',
                '[class*="description"]',
                '[class*="content"]',
            ],
        }
    },
    'architecturaldigest': {
        'base_url': 'https://www.architecturaldigest.com',
        'list_url': 'https://www.architecturaldigest.com/story/new-york-builders-and-contractors-we-love-from-the-ad-pro-directory',
        'rate_limit': 2.0,
        'output_file': 'output/architecturaldigest_results.csv',
        'requires_js': True,
        'selectors': {
            'listing': [
                'article',
                'div[class*="article"]',
                'div[class*="content"]',
                'div[class*="entry"]',
                'section',
                'div[class*="story"]',
                'li',
            ],
            'name': [
                'h2',
                'h3',
                'h4',
                'strong',
                '[class*="title"]',
                '[class*="name"]',
                'h2 a',
                'h3 a',
            ],
            'website': [
                'a[href^="http"]',
                'a[href*="www"]',
                '[class*="website"] a',
                '[class*="url"] a',
            ],
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
            ],
            'specialty': [
                'p',
                '[class*="description"]',
                '[class*="content"]',
            ],
        }
    },
    'architizer': {
        'base_url': 'https://architizer.com',
        'list_url': 'https://architizer.com/blog/inspiration/collections/best-nyc-architecture-firms/',
        'rate_limit': 2.0,
        'output_file': 'output/architizer_results.csv',
        'requires_js': True,
        'selectors': {
            'listing': [
                'article',
                'div[class*="article"]',
                'div[class*="content"]',
                'div[class*="entry"]',
                'section',
                'div[class*="collections"]',
                'li',
            ],
            'name': [
                'h2',
                'h3',
                'h4',
                'strong',
                '[class*="title"]',
                '[class*="firm"]',
                '[class*="name"]',
                'h2 a',
                'h3 a',
            ],
            'website': [
                'a[href^="http"]',
                'a[href*="www"]',
                'a[href*="architizer.com/firms"]',
                '[class*="website"] a',
                '[class*="url"] a',
            ],
            'phone': [
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[class*="tel"]',
            ],
            'email': [
                'a[href^="mailto:"]',
                '[class*="email"]',
            ],
            'address': [
                '[class*="address"]',
                '[class*="location"]',
            ],
            'specialty': [
                'p',
                '[class*="description"]',
                '[class*="content"]',
            ],
        }
    },
    # Add more website configurations here
    # Example template:
    # 'website_name': {
    #     'base_url': 'https://example.com',
    #     'search_url_template': 'https://example.com/search?q={query}',
    #     'rate_limit': 1.0,
    #     'selectors': {
    #         'listing': ['.listing-class'],
    #         'name': '.name-selector',
    #         'website': 'a.website-selector',
    #         'phone': '.phone-selector',
    #         # ... more selectors
    #     }
    # }
}

# Search queries to use
SEARCH_QUERIES = [
    'interior designer',
    'interior design',
    'home designer',
    'residential designer',
]
