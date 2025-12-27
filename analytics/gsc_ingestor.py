import csv
import logging
import os
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class GSCPageMetrics:
    url: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    top_query: Optional[str] = None

class GSCIngestor:
    """
    Ingests Google Search Console exports (CSV or Excel).
    Expects standard GSC export format.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: str) -> List[Dict]:
        """Parses a GSC file (CSV or Excel) into a list of dictionaries."""
        data = []
        try:
            if file_path.endswith('.xlsx'):
                # GSC Excel export has sheets: 'Pages', 'Queries', etc.
                # We default to 'Pages' sheet for page metrics
                df = pd.read_excel(file_path, sheet_name='Pages')
                return df.to_dict('records')
            else:
                # Assume CSV
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise
        return data

    def ingest(self, file_path: str) -> List[GSCPageMetrics]:
        """
        Main ingestion method.
        Reads Pages export and converts to GSCPageMetrics objects.
        """
        raw_rows = self.parse_file(file_path)
        metrics_list = []

        for row in raw_rows:
            try:
                # GSC Header Mapping
                # CSV/Excel headers: "Top pages", "Clicks", "Impressions", "CTR", "Position"
                
                url = row.get('Top pages') or row.get('Page')
                if not url:
                    continue

                # Parse metrics
                clicks = int(row.get('Clicks', 0))
                impressions = int(row.get('Impressions', 0))
                
                # Handle CTR (could be string "1.5%" or float 0.015)
                ctr_raw = row.get('CTR', 0)
                if isinstance(ctr_raw, str):
                   ctr_val = float(ctr_raw.replace('%', '')) / 100.0 if '%' in ctr_raw else float(ctr_raw)
                else:
                   ctr_val = float(ctr_raw)

                position = float(row.get('Position', 0))

                metric = GSCPageMetrics(
                    url=url,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=ctr_val,
                    position=position
                )
                metrics_list.append(metric)
                
            except Exception as e:
                self.logger.warning(f"Skipping row due to parse error: {row} - {e}")
                continue

        return metrics_list
