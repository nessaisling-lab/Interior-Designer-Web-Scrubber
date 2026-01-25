# Interior Designer Web Scraper

A Python-based web scraper for collecting interior designer names and contact information from multiple online directories to create a comprehensive client directory.

## Features

- **Modular Architecture**: Easy to add new website sources
- **Multiple Sources**: Supports scraping from various business directories (Yelp, Houzz, etc.)
- **Data Collection**: Collects name, email, phone, website, address, and more
- **CSV Export**: Exports collected data to CSV format
- **Rate Limiting**: Respectful scraping with configurable rate limits
- **Deduplication**: Automatically removes duplicate entries
- **Error Handling**: Robust error handling and logging

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. **For JavaScript-rendered sites (like ASID)**: Install Chrome browser if not already installed. ChromeDriver will be downloaded automatically by webdriver-manager.

## Configuration

Edit `config.py` to configure:

- **Website Configurations**: Add or modify website-specific settings including:
  - Base URLs
  - Search URL templates
  - CSS selectors for data extraction
  - Rate limiting settings

- **Global Settings**: Adjust output file path, logging level, and default limits

## Usage

### Basic Usage

Scrape from all configured sources:
```bash
python main.py
```

### Advanced Usage

Scrape specific sources:
```bash
python main.py --sources yelp houzz bocadolobo
```

Scrape from Boca do Lobo's curated list:
```bash
python main.py --sources bocadolobo --max-results 50
```

Use custom search query:
```bash
python main.py --query "luxury interior designer"
```

Limit results per source:
```bash
python main.py --max-results 50
```

Specify output file:
```bash
python main.py --output my_designers.csv
```

Append to existing file:
```bash
python main.py --append
```

Set logging level:
```bash
python main.py --log-level DEBUG
```

### Command Line Options

- `--sources`: Specific sources to scrape (default: all)
- `--query`: Search query (default: "interior designer")
- `--max-results`: Maximum results per source
- `--output`: Output CSV file path
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--append`: Append to existing CSV file instead of overwriting

## Project Structure

```
interior-designer-web-scrubber/
├── main.py                 # Main entry point
├── config.py              # Configuration file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── models/
│   └── designer.py       # Data model
├── scrapers/
│   ├── base_scraper.py   # Base scraper class
│   └── directory_scraper.py  # Directory scraper implementation
└── utils/
    ├── exporter.py       # CSV export
    ├── logger.py         # Logging utilities
    └── rate_limiter.py   # Rate limiting
```

## Adding New Sources

To add a new website source:

1. Open `config.py`
2. Add a new entry to `WEBSITE_CONFIGS` dictionary:

```python
'new_website': {
    'base_url': 'https://example.com',
    'search_url_template': 'https://example.com/search?q={query}',
    'rate_limit': 1.0,
    'selectors': {
        'listing': ['.listing-class'],
        'name': '.name-selector',
        'website': 'a.website-selector',
        'phone': '.phone-selector',
        'address': '.address-selector',
        'city': '.city-selector',
        'state': '.state-selector',
        'zip_code': '.zip-selector',
        'next_page': 'a.next-page',
    }
}
```

3. Inspect the target website's HTML structure to determine the correct CSS selectors
4. Test the scraper with: `python main.py --sources new_website --max-results 5`

## Output Format

The CSV file includes the following columns:
- `name`: Designer name
- `email`: Email address
- `phone`: Phone number
- `website`: Website URL
- `address`: Street address
- `city`: City
- `state`: State
- `zip_code`: ZIP code
- `social_media`: Social media links
- `specialty`: Design specialty
- `source_url`: URL where data was found

## Important Notes

- **Respect robots.txt**: The scraper checks robots.txt before scraping
- **Rate Limiting**: Default rate limits are set to be respectful. Adjust in config if needed
- **Legal Compliance**: Ensure your use of this scraper complies with website terms of service and applicable laws
- **JavaScript Support**: Selenium support included for JavaScript-rendered pages (like ASID). Chrome browser required.

## Troubleshooting

**No results found:**
- Check that CSS selectors in `config.py` match the website's current HTML structure
- Websites may have changed their structure - inspect the page source
- Try running with `--log-level DEBUG` to see detailed information

**Rate limiting errors:**
- Increase `rate_limit` in the website configuration
- Some websites may block automated access - consider using proxies or API access

**Missing data fields:**
- Some websites may not display all contact information publicly
- The scraper attempts to extract emails from detail pages when available

## License

This project is provided as-is for educational and legitimate business purposes. Users are responsible for ensuring compliance with website terms of service and applicable laws.
