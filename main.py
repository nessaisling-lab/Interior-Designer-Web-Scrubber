"""Main orchestrator for the interior designer web scraper."""

import argparse
import os
from pathlib import Path
from typing import List, Optional

from models.designer import Designer
from scrapers.directory_scraper import DirectoryScraper
from utils.exporter import CSVExporter
from utils.logger import setup_logging, get_logger
import config

logger = get_logger(__name__)


def scrape_all_sources(
    sources: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
    output_file: Optional[str] = None,
    single_url: Optional[str] = None
) -> List[Designer]:
    """
    Scrape designers from all configured sources.
    
    Args:
        sources: List of source names to scrape (None = all)
        search_query: Search query to use
        max_results: Maximum results per source
        output_file: Output CSV file path
        single_url: If set, scrape only this one URL (requires exactly one source via --sources)
        
    Returns:
        List of all scraped Designer objects
    """
    all_designers = []
    
    # When --url is used, require exactly one source (that source's config is used for the single URL)
    if single_url and single_url.strip():
        if not sources or len(sources) != 1:
            logger.error("When using --url, you must specify exactly one source with --sources (e.g. --sources rethinkingthefuture --url \"https://...\")")
            return all_designers
        sources_to_scrape = sources
        logger.info(f"Single-URL mode: scraping one URL using source '{sources_to_scrape[0]}'")
    else:
        sources_to_scrape = sources if sources else list(config.WEBSITE_CONFIGS.keys())
    
    logger.info(f"Starting scrape from {len(sources_to_scrape)} source(s)")
    
    for source_name in sources_to_scrape:
        if source_name not in config.WEBSITE_CONFIGS:
            logger.warning(f"Source '{source_name}' not found in configuration")
            continue
        
        try:
            logger.info(f"Scraping from {source_name}...")
            source_config = config.WEBSITE_CONFIGS[source_name]
            
            # Create scraper instance
            scraper = DirectoryScraper(source_config)
            
            # Perform scrape (single_url overrides list_urls when set)
            query = search_query or config.SEARCH_QUERIES[0]
            designers = scraper.scrape(
                search_query=query,
                max_results=max_results,
                single_url=single_url.strip() if single_url and single_url.strip() else None
            )
            
            logger.info(f"Found {len(designers)} designers from {source_name}")
            
            # Check if this source has its own output file configured
            source_output_file = source_config.get('output_file')
            if source_output_file and designers:
                # Check if we have per-page results (from pagination)
                if hasattr(scraper, '_page_results') and scraper._page_results:
                    # Export each page to a separate file (append if file exists to preserve prior runs)
                    base_output_path = source_output_file
                    base_name = os.path.splitext(base_output_path)[0]
                    base_ext = os.path.splitext(base_output_path)[1] or '.csv'
                    
                    for page_data in scraper._page_results:
                        page_num = page_data['page_num']
                        page_designers = page_data['designers']
                        page_output_file = f"{base_name}_page{page_num}{base_ext}"
                        
                        if page_designers:
                            append_page = os.path.exists(page_output_file)
                            exporter = CSVExporter(page_output_file)
                            exporter.export(page_designers, append=append_page, deduplicate=True)
                            logger.info(f"Exported {len(page_designers)} designers from page {page_num} to {page_output_file} ({'appended' if append_page else 'created new'})")
                        else:
                            logger.warning(f"No designers found on page {page_num}")
                    
                    # Also export combined results to main file (append if exists to preserve prior runs)
                    append_combined = os.path.exists(base_output_path)
                    exporter = CSVExporter(base_output_path)
                    exporter.export(designers, append=append_combined, deduplicate=True)
                    logger.info(f"Exported {len(designers)} total designers (combined) to {base_output_path} ({'appended' if append_combined else 'created new'})")
                else:
                    # Single file export (no pagination or single page); append if file exists to preserve prior runs
                    file_exists = os.path.exists(source_output_file)
                    exporter = CSVExporter(source_output_file)
                    exporter.export(designers, append=file_exists, deduplicate=True)
                    logger.info(f"Exported {len(designers)} designers from {source_name} to {source_output_file} ({'appended' if file_exists else 'created new'})")
            else:
                # Add to combined list for main output file
                all_designers.extend(designers)
            
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}", exc_info=True)
            continue
    
    logger.info(f"Total designers collected: {len(all_designers)}")
    return all_designers


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape interior designer information from web directories'
    )
    parser.add_argument(
        '--sources',
        nargs='+',
        help='Specific sources to scrape (default: all)',
        choices=list(config.WEBSITE_CONFIGS.keys())
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Search query (default: "interior designer")'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        help='Maximum results per source'
    )
    parser.add_argument(
        '--output',
        type=str,
        help=f'Output CSV file path (default: {config.GLOBAL_CONFIG["output_file"]})'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=config.GLOBAL_CONFIG['log_level'],
        help='Logging level'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append to existing CSV file instead of overwriting'
    )
    parser.add_argument(
        '--url',
        type=str,
        default=None,
        metavar='URL',
        help='Single URL to scrape for this run (overrides list_urls). Requires exactly one --sources, e.g. --sources rethinkingthefuture --url "https://.../3/"'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = config.GLOBAL_CONFIG.get('log_file')
    setup_logging(log_level=args.log_level, log_file=log_file)
    
    logger.info("=" * 60)
    logger.info("Interior Designer Web Scraper")
    logger.info("=" * 60)
    
    # Determine output file
    output_file = args.output or config.GLOBAL_CONFIG['output_file']
    
    # Determine max results
    max_results = args.max_results or config.GLOBAL_CONFIG.get('default_max_results')
    
    try:
        # Scrape all sources (pass --url for one-run-one-URL mode)
        designers = scrape_all_sources(
            sources=args.sources,
            search_query=args.query,
            max_results=max_results,
            output_file=output_file,
            single_url=args.url
        )
        
        # Export to CSV
        if designers:
            exporter = CSVExporter(output_file)
            exporter.export(designers, append=args.append, deduplicate=True)
            logger.info(f"Successfully exported {len(designers)} designers to {output_file}")
        else:
            logger.warning("No designers found to export")
    
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
