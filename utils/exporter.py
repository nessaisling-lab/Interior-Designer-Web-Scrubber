"""CSV export functionality for designer data."""

import csv
from pathlib import Path
from typing import List, Set
from utils.logger import get_logger

from models.designer import Designer

logger = get_logger(__name__)


class CSVExporter:
    """Handles CSV export of designer data."""
    
    def __init__(self, output_path: str = 'output/designers.csv'):
        """
        Initialize CSV exporter.
        
        Args:
            output_path: Path to output CSV file
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = [
            'name', 'email', 'phone', 'website', 'address',
            'city', 'state', 'zip_code', 'social_media', 'specialty', 'source_url'
        ]
    
    def export(self, designers: List[Designer], append: bool = False, deduplicate: bool = True):
        """
        Export designers to CSV file.
        
        Args:
            designers: List of Designer objects to export
            append: If True, append to existing file; otherwise overwrite
            deduplicate: If True, remove duplicates before exporting
        """
        if not designers:
            logger.warning("No designers to export")
            return
        
        # Deduplicate if requested
        if deduplicate:
            designers = self._deduplicate(designers)
        
        # Load existing data if appending
        existing_designers = []
        if append and self.output_path.exists():
            existing_designers = self._load_existing()
            # Merge and deduplicate
            all_designers = existing_designers + designers
            designers = self._deduplicate(all_designers)
        
        # Write to CSV
        mode = 'a' if append and existing_designers else 'w'
        with open(self.output_path, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            
            # Write header if new file or overwriting
            if mode == 'w' or not existing_designers:
                writer.writeheader()
            
            # Write designers
            for designer in designers:
                writer.writerow(designer.to_dict())
        
        logger.info(f"Exported {len(designers)} designers to {self.output_path}")
    
    def _deduplicate(self, designers: List[Designer]) -> List[Designer]:
        """Remove duplicate designers."""
        seen: Set[Designer] = set()
        unique = []
        
        for designer in designers:
            if designer not in seen:
                seen.add(designer)
                unique.append(designer)
        
        duplicates_removed = len(designers) - len(unique)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate entries")
        
        return unique
    
    def _load_existing(self) -> List[Designer]:
        """Load existing designers from CSV file."""
        designers = []
        
        try:
            with open(self.output_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    designer = Designer(
                        name=row.get('name', ''),
                        source_url=row.get('source_url', ''),
                        email=row.get('email') or None,
                        phone=row.get('phone') or None,
                        website=row.get('website') or None,
                        address=row.get('address') or None,
                        city=row.get('city') or None,
                        state=row.get('state') or None,
                        zip_code=row.get('zip_code') or None,
                        specialty=row.get('specialty') or None
                    )
                    designers.append(designer)
        except Exception as e:
            logger.warning(f"Could not load existing CSV: {e}")
        
        return designers
