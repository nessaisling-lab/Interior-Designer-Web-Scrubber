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
