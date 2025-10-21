"""
multi_site_content_agent.py
===========================

This module contains a skeleton for an automated content generation pipeline that
can be reused across multiple websites.  It expands on the earlier single‑site
version by accepting a Google Search Console (GSC) export for any site in
CSV format, analysing the data to identify underperforming pages, generating
a fresh content plan, drafting new articles and (optionally) preparing
WordPress API calls to publish or update posts.  The goal is to provide
a plug‑and‑play foundation for building a web app or plugin that balances
SEO best practices with helpful, people‑first content.

**How it works**

1. **Data ingestion** – Upload a CSV export from GSC covering the past 12 months.
   The `GSCProcessor` reads and cleans this data, computing key metrics such as
   total clicks, impressions, click‑through rate (CTR) and average position per page.
2. **Opportunity analysis** – The processor identifies pages with high impressions
   but low CTR or poor ranking.  These pages are candidates for a content refresh.
   It also extracts high‑volume queries to seed new topic ideas.  At this stage you
   could add more sophisticated clustering or keyword research via external APIs.
3. **Content planning** – The `TopicPlanner` takes candidate queries and maps
   them to article titles, primary keywords and recommended publish months.  You can
   customise this mapping based on seasonality or your editorial calendar.
4. **Draft generation** – The `ContentGenerator` turns each topic into a full
   article.  The default implementation uses simple heuristics and templated
   paragraphs (similar to the previous MVP).  In production you would
   replace this with calls to a language model API or a more advanced
   natural language generation component.
5. **Publishing** – The `WordPressPublisher` is a thin wrapper around the
   WordPress REST API.  It exposes methods to create new posts or update
   existing ones.  You must provide credentials (username and application
   password) and the base URL for your WordPress site.  These methods are
   stubs in this skeleton and will only execute network calls if the
   `requests` library is installed and the provided endpoint is reachable.

Note: This script is a template and does not perform any real network
operations by default.  It is designed to be extended and integrated
into a user interface (e.g. a Flask/Streamlit app or a WordPress plugin).

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import pandas as pd
import requests
import datetime
import re


# Topic dataclass removed - no longer needed with AI-powered content generation
# Use ClaudeContentGenerator for all content creation instead


class DataProcessor:
    """
    Unified data processor for Google Search Console (GSC) and Google Analytics 4 (GA4).
    
    Handles loading, cleaning, and merging data from both sources to provide
    comprehensive insights combining search performance (GSC) with user behavior (GA4).
    """

    def __init__(self, gsc_path: str, ga4_path: Optional[str] = None) -> None:
        self.gsc_path = gsc_path
        self.ga4_path = ga4_path
        self.df: pd.DataFrame | None = None
        self.pages_df: pd.DataFrame | None = None
        self.queries_df: pd.DataFrame | None = None
        self.ga4_df: pd.DataFrame | None = None
        # Enhanced GSC tabs
        self.countries_df: pd.DataFrame | None = None
        self.devices_df: pd.DataFrame | None = None
        self.search_appearance_df: pd.DataFrame | None = None
        self.dates_df: pd.DataFrame | None = None

    def _normalize_gsc_metrics(self, df: pd.DataFrame) -> None:
        """Normalize GSC metric columns (clicks, impressions, CTR, position) in place."""
        numeric_cols = ["clicks", "impressions", "ctr", "position"]
        for col in numeric_cols:
            if col in df.columns:
                if col == "ctr":
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str).str.replace("%", "").astype(float) / 100
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

    def load_gsc(self) -> pd.DataFrame:
        """Load Google Search Console CSV or Excel file and combine Queries + Pages data."""

        # Check file extension
        if self.gsc_path.endswith('.xlsx') or self.gsc_path.endswith('.xls'):
            # Read Excel file
            try:
                # First, try to read the first sheet (most common GSC export format)
                df = pd.read_excel(self.gsc_path, sheet_name=0)
                df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

                # Handle various GSC export column name formats
                column_renames = {
                    'top_pages': 'page',
                    'url': 'page',
                    'landing_page': 'page',
                    'top_queries': 'query',
                    'search_query': 'query',
                }

                for old_name, new_name in column_renames.items():
                    if old_name in df.columns and new_name not in df.columns:
                        df.rename(columns={old_name: new_name}, inplace=True)

                # Ensure we have required columns
                if 'page' not in df.columns:
                    df['page'] = ''
                if 'query' not in df.columns:
                    df['query'] = ''

                # Check if this is a multi-sheet export (has separate Queries and Pages sheets)
                excel_file = pd.ExcelFile(self.gsc_path)
                if 'Queries' in excel_file.sheet_names and 'Pages' in excel_file.sheet_names:
                    print(f"\n📊 Loading GSC data from multi-sheet export...")

                    # Load Queries sheet
                    self.queries_df = pd.read_excel(self.gsc_path, sheet_name='Queries')
                    self.queries_df.columns = [col.strip().lower().replace(" ", "_") for col in self.queries_df.columns]
                    if 'top_queries' in self.queries_df.columns:
                        self.queries_df.rename(columns={'top_queries': 'query'}, inplace=True)
                    print(f"   ✓ Loaded Queries sheet: {len(self.queries_df)} queries")

                    # Load Pages sheet
                    self.pages_df = pd.read_excel(self.gsc_path, sheet_name='Pages')
                    self.pages_df.columns = [col.strip().lower().replace(" ", "_") for col in self.pages_df.columns]
                    if 'top_pages' in self.pages_df.columns:
                        self.pages_df.rename(columns={'top_pages': 'page'}, inplace=True)
                    print(f"   ✓ Loaded Pages sheet: {len(self.pages_df)} pages")

                    # Load Countries sheet if available
                    if 'Countries' in excel_file.sheet_names:
                        self.countries_df = pd.read_excel(self.gsc_path, sheet_name='Countries')
                        self.countries_df.columns = [col.strip().lower().replace(" ", "_") for col in self.countries_df.columns]
                        self._normalize_gsc_metrics(self.countries_df)
                        print(f"   ✓ Loaded Countries sheet: {len(self.countries_df)} countries")

                    # Load Devices sheet if available
                    if 'Devices' in excel_file.sheet_names:
                        self.devices_df = pd.read_excel(self.gsc_path, sheet_name='Devices')
                        self.devices_df.columns = [col.strip().lower().replace(" ", "_") for col in self.devices_df.columns]
                        self._normalize_gsc_metrics(self.devices_df)
                        print(f"   ✓ Loaded Devices sheet: {len(self.devices_df)} device types")

                    # Load Search Appearance sheet if available
                    if 'Search Appearance' in excel_file.sheet_names:
                        self.search_appearance_df = pd.read_excel(self.gsc_path, sheet_name='Search Appearance')
                        self.search_appearance_df.columns = [col.strip().lower().replace(" ", "_") for col in self.search_appearance_df.columns]
                        self._normalize_gsc_metrics(self.search_appearance_df)
                        print(f"   ✓ Loaded Search Appearance sheet: {len(self.search_appearance_df)} appearance types")

                    # Load Dates sheet if available
                    if 'Dates' in excel_file.sheet_names:
                        self.dates_df = pd.read_excel(self.gsc_path, sheet_name='Dates')
                        self.dates_df.columns = [col.strip().lower().replace(" ", "_") for col in self.dates_df.columns]
                        self._normalize_gsc_metrics(self.dates_df)
                        # Convert date column to datetime
                        if 'date' in self.dates_df.columns:
                            self.dates_df['date'] = pd.to_datetime(self.dates_df['date'], errors='coerce')
                        print(f"   ✓ Loaded Dates sheet: {len(self.dates_df)} date entries")

                    df = self._create_combined_data()

            except Exception as e:
                print(f"Error reading Excel file: {e}")
                raise ValueError(f"Could not read Excel file. Please ensure it's a valid GSC export. Error: {str(e)}")
        else:
            # Read CSV file with encoding detection
            try:
                # Try UTF-8 first (most common)
                df = pd.read_csv(self.gsc_path, encoding='utf-8')
            except UnicodeDecodeError:
                # Fall back to latin-1 (handles most other encodings)
                try:
                    df = pd.read_csv(self.gsc_path, encoding='latin-1')
                except Exception:
                    # Last resort: ignore errors
                    df = pd.read_csv(self.gsc_path, encoding='utf-8', errors='ignore')

            df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        
        # Ensure numeric columns are of correct type
        numeric_cols = ["clicks", "impressions", "ctr", "position"]
        for col in numeric_cols:
            if col in df.columns:
                if col == "ctr":
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str).str.replace("%", "").astype(float) / 100
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

        # CRITICAL: Filter out homepage URLs to prevent treating them as posts
        # Homepage URLs match pattern: http(s)://domain.com/ or http(s)://domain.com
        import re
        homepage_pattern = re.compile(r'^https?://[^/]+/?$')
        if 'page' in df.columns:
            before_count = len(df)
            df = df[~df['page'].astype(str).str.match(homepage_pattern, na=False)]
            filtered_count = before_count - len(df)
            if filtered_count > 0:
                print(f"   ℹ  Filtered out {filtered_count} homepage URL(s) from GSC data")

        self.df = df
        return df
    
    def load_ga4(self) -> pd.DataFrame:
        """
        Load Google Analytics 4 CSV export.

        Supports two export formats:
        1. Standard CSV/Excel with columns: page, views, users, bounce_rate, etc.
        2. "Reports Snapshot" format with hashtag-delimited sections

        For Reports Snapshot, extracts the "Page title and screen class" section which contains:
        - Page title and screen class
        - Views
        - Active users
        - Event count
        - Bounce rate

        Returns:
            pd.DataFrame: Normalized GA4 data with columns:
                - page (URL)
                - sessions
                - engagement_rate (decimal)
                - avg_engagement_time (seconds)
                - bounce_rate (decimal)
                - conversions (if available)
        """
        if not self.ga4_path:
            return pd.DataFrame()

        print(f"\n📊 Loading GA4 data from: {self.ga4_path}")

        # First, check if this is a "Reports Snapshot" format by reading raw lines
        try:
            with open(self.ga4_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline() for _ in range(5)]
                is_reports_snapshot = any('Reports snapshot' in line or '# ------' in line for line in first_lines)
        except:
            is_reports_snapshot = False

        if is_reports_snapshot:
            print(f"   ℹ Detected GA4 'Reports Snapshot' format - using section parser")
            return self._parse_ga4_reports_snapshot()
        
        # Read Excel or CSV file
        if self.ga4_path.endswith('.xlsx') or self.ga4_path.endswith('.xls'):
            # Read Excel file (first sheet)
            # GA4 exports often have metadata rows at the top - try to detect them
            try:
                # Try reading with default (no skip)
                df_test = pd.read_excel(self.ga4_path, sheet_name=0, nrows=20, header=None)

                # Look for the row that contains actual column headers
                # GA4 typically has headers like "Page", "Views", "Sessions", etc.
                header_row = None
                for idx, row in df_test.iterrows():
                    row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
                    # Check if this looks like a header row
                    if any(keyword in row_str for keyword in ['page', 'view', 'session', 'user', 'bounce', 'engagement']):
                        header_row = idx
                        print(f"   ✓ Detected header row at line {idx + 1}")
                        break

                if header_row is not None and header_row > 0:
                    print(f"   ℹ Skipping {header_row} metadata rows")
                    df = pd.read_excel(self.ga4_path, sheet_name=0, skiprows=header_row)
                else:
                    df = pd.read_excel(self.ga4_path, sheet_name=0)
            except Exception as e:
                print(f"   ⚠️  GA4 Excel read error: {e}, trying default read")
                df = pd.read_excel(self.ga4_path, sheet_name=0)
        else:
            # Read CSV file with encoding detection
            print(f"   📄 Reading CSV file...")
            try:
                # GA4 CSV exports may have metadata at the top - detect header row
                # Read first 20 rows to find headers
                df_test = pd.read_csv(self.ga4_path, nrows=20, header=None, encoding='utf-8')
                
                header_row = None
                for idx, row in df_test.iterrows():
                    row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
                    # Check if this looks like a header row
                    if any(keyword in row_str for keyword in ['page', 'view', 'session', 'user', 'bounce', 'engagement']):
                        header_row = idx
                        print(f"   ✓ Detected header row at line {idx + 1}")
                        break
                
                if header_row is not None and header_row > 0:
                    print(f"   ℹ Skipping {header_row} metadata rows")
                    df = pd.read_csv(self.ga4_path, skiprows=header_row, encoding='utf-8')
                else:
                    df = pd.read_csv(self.ga4_path, encoding='utf-8')
            except UnicodeDecodeError:
                print(f"   ⚠️  UTF-8 decode error, trying latin-1...")
                # Fall back to latin-1 (handles most other encodings)
                try:
                    df = pd.read_csv(self.ga4_path, encoding='latin-1')
                except Exception:
                    # Last resort: ignore errors
                    print(f"   ⚠️  Latin-1 failed, using UTF-8 with error ignore")
                    df = pd.read_csv(self.ga4_path, encoding='utf-8', errors='ignore')
        
        # Remove completely empty rows (GA4 exports sometimes have trailing empty rows)
        df = df.dropna(how='all')
        
        # Normalize column names
        df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]

        # Debug: print available columns
        print(f"   ✓ GA4 columns found: {list(df.columns)[:10]}..." if len(df.columns) > 10 else f"   ✓ GA4 columns found: {list(df.columns)}")
        print(f"   ✓ GA4 rows loaded: {len(df)}")

        # Map common variations to standard names (including more variations)
        column_mapping = {
            'landing_page': 'page',
            'page_path': 'page',
            'page_location': 'page',
            'page_path_and_screen_class': 'page',
            'page_title_and_screen_class': 'page',  # GA4 export format
            'url': 'page',
            'views': 'sessions',  # GA4 uses "Views" instead of "Sessions"
            'average_engagement_time': 'avg_engagement_time',
            'average_engagement_time_per_session': 'avg_engagement_time',
            'engaged_sessions_per_user': 'engagement_rate',
            'engagement_rate': 'engagement_rate',
            'active_users': 'users',  # Keep active users as a metric
            'event_count': 'events',  # Keep event count
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)

        # If still no 'page' column, try to find any URL-like column
        if 'page' not in df.columns:
            # Look for any column that might contain URLs or page identifiers
            url_candidates = [col for col in df.columns if any(x in col for x in ['page', 'url', 'path', 'landing', 'title'])]
            if url_candidates:
                print(f"   ℹ Using column '{url_candidates[0]}' as 'page' identifier")
                df.rename(columns={url_candidates[0]: 'page'}, inplace=True)
                # Check if this column contains page titles vs URLs
                sample = df['page'].iloc[0] if len(df) > 0 else ''
                if sample and not sample.startswith('http') and '/' not in str(sample):
                    print(f"   ⚠️  Warning: GA4 'page' column contains page titles, not URLs.")
                    print(f"      This data won't merge with GSC data. For better results,")
                    print(f"      export GA4 with 'Page path' or 'Full page URL' dimension.")
                    print(f"      Continuing with GA4 data as supplementary metrics only...")
            else:
                # GA4 data is optional, so return empty instead of error
                print(f"   ⚠️  Warning: GA4 file has no recognizable page/URL column.")
                print(f"      Available columns: {list(df.columns)}")
                print(f"      Skipping GA4 data - only GSC data will be used.")
                return pd.DataFrame()
        
        # Normalize numeric columns
        numeric_cols = ['sessions', 'engagement_rate', 'avg_engagement_time', 'bounce_rate', 'conversions']
        
        for col in numeric_cols:
            if col in df.columns:
                # Remove % signs and convert to decimal
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '')
                
                # Convert to numeric
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Convert percentages to decimals if needed (rates > 1 are likely percentages)
                if col in ['engagement_rate', 'bounce_rate']:
                    if df[col].max() > 1:
                        df[col] = df[col] / 100
        
        self.ga4_df = df
        return df

    def _parse_ga4_reports_snapshot(self) -> pd.DataFrame:
        """
        Parse GA4 'Reports Snapshot' CSV format which uses hashtag-delimited sections.

        Format example:
        # ----------------------------------------
        # Reports snapshot
        # ----------------------------------------
        ...
        # Start date: 20241013
        # End date: 20251013
        Page title and screen class    Views    Active users    Event count    Bounce rate
        Article Title 1    1370    1070    4372    0.5580847724
        Article Title 2    1115    953    3320    0.815920398
        ...
        #
        # Start date: 20241013
        First user source / medium    Active users
        ...

        We want to extract the "Page title and screen class" section.
        """
        print(f"   📄 Parsing GA4 Reports Snapshot format...")

        try:
            with open(self.ga4_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(self.ga4_path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"   ❌ Failed to read file: {e}")
                return pd.DataFrame()

        # Find the "Page title" section
        page_section_start = None
        page_section_end = None

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Look for section that contains page titles
            if 'page title' in line_lower and 'screen class' in line_lower:
                # This is the header row for the page section
                page_section_start = i
                print(f"   ✓ Found 'Page title' section at line {i + 1}")
                continue

            # If we found the start, look for the end (next # line or empty section)
            if page_section_start is not None and page_section_end is None:
                # Check if this is the start of a new section (line starting with #)
                if line.strip().startswith('#'):
                    page_section_end = i
                    print(f"   ✓ Page section ends at line {i}")
                    break

        if page_section_start is None:
            print(f"   ⚠️  Warning: Could not find 'Page title and screen class' section")
            print(f"      Available sections: {[l.strip() for l in lines if 'user' in l.lower() or 'page' in l.lower()][:5]}")
            return pd.DataFrame()

        # If we didn't find an end, use the rest of the file
        if page_section_end is None:
            page_section_end = len(lines)

        # Extract the page section lines
        section_lines = lines[page_section_start:page_section_end]

        # Remove empty lines and lines starting with #
        data_lines = [line for line in section_lines if line.strip() and not line.strip().startswith('#')]

        if len(data_lines) < 2:  # Need at least header + 1 data row
            print(f"   ⚠️  Warning: Page section has insufficient data ({len(data_lines)} lines)")
            return pd.DataFrame()

        # Parse into DataFrame using tab separator (GA4 uses tabs)
        from io import StringIO
        csv_data = ''.join(data_lines)

        try:
            # Try tab-separated first (most common in GA4 exports)
            df = pd.read_csv(StringIO(csv_data), sep='\t')

            # If that resulted in only 1 column, try comma-separated
            if len(df.columns) == 1:
                df = pd.read_csv(StringIO(csv_data), sep=',')

            print(f"   ✓ Parsed {len(df)} rows from Page title section")
            print(f"   ✓ Columns: {list(df.columns)}")

            # Normalize column names
            df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]

            # Map GA4 columns to our standard names
            column_mapping = {
                'page_title_and_screen_class': 'page',
                'page_title': 'page',
                'views': 'sessions',
                'active_users': 'users',
                'event_count': 'events',
                'bounce_rate': 'bounce_rate',
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)

            # Convert bounce rate from decimal to percentage if needed
            if 'bounce_rate' in df.columns:
                df['bounce_rate'] = pd.to_numeric(df['bounce_rate'], errors='coerce')
                # If values are between 0 and 1, they're already decimals
                # If values are > 1, they're percentages that need conversion
                if df['bounce_rate'].max() > 1:
                    df['bounce_rate'] = df['bounce_rate'] / 100

            # Convert other numeric columns
            numeric_cols = ['sessions', 'users', 'events', 'bounce_rate']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Add warning about page titles vs URLs
            if 'page' in df.columns and len(df) > 0:
                sample = df['page'].iloc[0] if len(df) > 0 else ''
                if sample and not str(sample).startswith('http') and '/' not in str(sample):
                    print(f"   ⚠️  Note: 'page' column contains page TITLES, not URLs")
                    print(f"      This data will be used as supplementary metrics only.")
                    print(f"      For URL-based merging with GSC, export GA4 with 'Page path' dimension.")

            self.ga4_df = df
            return df

        except Exception as e:
            print(f"   ❌ Error parsing page section: {e}")
            print(f"      First few lines: {data_lines[:3]}")
            return pd.DataFrame()

    def merge_data(self) -> pd.DataFrame:
        """
        Merge GSC and GA4 data on the 'page' column.
        
        Returns a DataFrame with both search performance (GSC) and user behavior (GA4) metrics.
        If GA4 data is not available, returns GSC data only.
        
        Returns:
            pd.DataFrame: Merged data with columns from both sources
        """
        # Load GSC data
        gsc_df = self.load_gsc()
        
        # Load GA4 data if available
        ga4_df = self.load_ga4()
        
        # If no GA4 data, return GSC only
        if ga4_df.empty:
            return gsc_df
        
        # Normalize URLs for matching (remove trailing slashes, query params)
        def normalize_url(url):
            if pd.isna(url) or url == '':
                return url
            # Remove query parameters
            url = str(url).split('?')[0]
            # Remove trailing slash
            url = url.rstrip('/')
            return url
        
        gsc_df['page_normalized'] = gsc_df['page'].apply(normalize_url)
        ga4_df['page_normalized'] = ga4_df['page'].apply(normalize_url)
        
        # Merge on normalized page URLs
        merged_df = pd.merge(
            gsc_df,
            ga4_df,
            on='page_normalized',
            how='left',
            suffixes=('', '_ga4')
        )
        
        # Use GSC page URL as the primary one
        if 'page_ga4' in merged_df.columns:
            merged_df.drop(columns=['page_ga4'], inplace=True)
        
        # Drop the normalized column used for matching
        merged_df.drop(columns=['page_normalized'], inplace=True)
        
        # Store merged data
        self.df = merged_df
        
        return merged_df
    
    def load(self) -> pd.DataFrame:
        """
        Convenience method for backward compatibility.
        Loads and merges GSC + GA4 data if available.
        """
        return self.merge_data()
    
    def _create_combined_data(self) -> pd.DataFrame:
        """
        Create a comprehensive dataset combining Pages and Queries data properly.

        Returns a DataFrame with:
        - Page-level aggregated stats (for pages with traffic)
        - Query-level data (actual search queries from GSC)
        - Orphaned queries (queries without associated pages - content gaps)
        """
        combined_rows = []

        # IMPORTANT: We need to maintain BOTH page-level AND query-level data
        # Don't create "fake" keywords from URLs - use actual GSC query data

        # 1. Add page-level aggregated statistics
        # These rows have 'page' but empty 'query' - represents overall page performance
        for _, page_row in self.pages_df.iterrows():
            page_url = page_row['page']

            combined_rows.append({
                'page': page_url,
                'query': '',  # Empty query for page-level aggregates
                'clicks': page_row['clicks'],
                'impressions': page_row['impressions'],
                'ctr': page_row['ctr'],
                'position': page_row['position']
            })

        # 2. Add all ACTUAL search queries from GSC
        # These are the real keywords people use to find content
        for _, query_row in self.queries_df.iterrows():
            combined_rows.append({
                'page': '',  # No specific page association in Queries sheet
                'query': query_row['query'],  # REAL search query from GSC
                'clicks': query_row['clicks'],
                'impressions': query_row['impressions'],
                'ctr': query_row['ctr'],
                'position': query_row['position']
            })

        # Note: If you have the full GSC export with BOTH page AND query in each row,
        # that would be ideal. The current multi-sheet format separates them.
        # This approach maintains data integrity without creating fake keywords.

        return pd.DataFrame(combined_rows)
    
    def get_top_queries(self, top_n: int = 20) -> pd.DataFrame:
        """Get top queries by impressions."""
        if self.queries_df is not None:
            return self.queries_df.nlargest(top_n, 'impressions')
        elif self.df is not None:
            return self.df.nlargest(top_n, 'impressions')
        return pd.DataFrame()
    
    def get_top_pages(self, top_n: int = 20) -> pd.DataFrame:
        """Get top pages by impressions."""
        if self.pages_df is not None:
            return self.pages_df.nlargest(top_n, 'impressions')
        elif self.df is not None:
            return self.df.groupby('page').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index().nlargest(top_n, 'impressions')
        return pd.DataFrame()

    def summarise_by_page(self) -> pd.DataFrame:
        """Group data by URL and calculate total clicks, impressions, CTR and average position."""
        assert self.df is not None, "DataFrame not loaded"
        grouped = (
            self.df.groupby("page")
            .agg(
                total_clicks=("clicks", "sum"),
                total_impressions=("impressions", "sum"),
                avg_ctr=("ctr", "mean"),
                avg_position=("position", "mean"),
            )
            .reset_index()
        )
        return grouped

    def identify_refresh_candidates(
        self, impression_threshold: int = 500, ctr_threshold: float = 0.01, position_threshold: float = 30
    ) -> pd.DataFrame:
        """Identify pages with high impressions but low CTR or poor ranking."""
        summary = self.summarise_by_page()
        candidates = summary[
            (
                (summary["total_impressions"] >= impression_threshold)
                & (summary["avg_ctr"] <= ctr_threshold)
            )
            | (summary["avg_position"] >= position_threshold)
        ].copy()
        return candidates.sort_values("total_impressions", ascending=False)

    def extract_query_opportunities(self, top_n: int = 10) -> list:
        """Return a list of unique query strings with high impressions for new topic ideas."""
        assert self.df is not None, "DataFrame not loaded"
        query_df = self.df.sort_values("impressions", ascending=False)
        queries = query_df["query"].dropna().unique().tolist()
        # Filter out empty strings
        queries = [q for q in queries if q and len(q) > 0]
        return queries[:top_n]

    # Enhanced GSC analysis methods

    def get_device_breakdown(self) -> Optional[pd.DataFrame]:
        """
        Get device performance breakdown (Mobile/Desktop/Tablet).

        Returns:
            DataFrame with device, clicks, impressions, ctr, position
            or None if device data not available
        """
        return self.devices_df if self.devices_df is not None else None

    def get_mobile_vs_desktop_performance(self) -> Dict[str, Dict]:
        """
        Compare mobile vs desktop performance.

        Returns:
            Dict with mobile and desktop metrics, or empty dict if not available
        """
        if self.devices_df is None or len(self.devices_df) == 0:
            return {}

        result = {}
        for _, row in self.devices_df.iterrows():
            device = row.get('device', '').lower()
            if device in ['mobile', 'desktop']:
                result[device] = {
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0),
                    'position': row.get('position', 0)
                }
        return result

    def is_mobile_first_site(self) -> bool:
        """
        Determine if site is mobile-first based on traffic distribution.

        Returns:
            True if mobile traffic > desktop traffic
        """
        breakdown = self.get_mobile_vs_desktop_performance()
        if not breakdown or 'mobile' not in breakdown or 'desktop' not in breakdown:
            return False  # Default to desktop if unknown

        mobile_clicks = breakdown['mobile'].get('clicks', 0)
        desktop_clicks = breakdown['desktop'].get('clicks', 0)

        return mobile_clicks > desktop_clicks

    def get_geographic_performance(self, top_n: int = 10) -> Optional[pd.DataFrame]:
        """
        Get top performing countries.

        Args:
            top_n: Number of top countries to return

        Returns:
            DataFrame with country performance data
        """
        if self.countries_df is not None and len(self.countries_df) > 0:
            return self.countries_df.nlargest(top_n, 'clicks')
        return None

    def get_trending_vs_declining(self, lookback_days: int = 30) -> Dict[str, List[str]]:
        """
        Identify trending and declining content based on time-series data.

        Compares recent performance (last N days) vs previous period to detect growth/decline.

        Args:
            lookback_days: Number of days for recent period (default: 30)

        Returns:
            Dict with 'trending' and 'declining' lists of queries with growth percentages
        """
        if self.dates_df is None or len(self.dates_df) == 0:
            return {'trending': [], 'declining': []}

        try:
            # Ensure date column is datetime
            if 'date' not in self.dates_df.columns:
                return {'trending': [], 'declining': []}

            # Calculate cutoff dates
            max_date = self.dates_df['date'].max()
            recent_cutoff = max_date - pd.Timedelta(days=lookback_days)
            comparison_cutoff = recent_cutoff - pd.Timedelta(days=lookback_days)

            # Split into periods
            recent_period = self.dates_df[self.dates_df['date'] >= recent_cutoff]
            comparison_period = self.dates_df[
                (self.dates_df['date'] >= comparison_cutoff) &
                (self.dates_df['date'] < recent_cutoff)
            ]

            # Aggregate by query (if query column exists)
            query_col = 'query' if 'query' in self.dates_df.columns else None

            if not query_col:
                # If no query breakdown, use page instead
                query_col = 'page' if 'page' in self.dates_df.columns else None

            if not query_col:
                return {'trending': [], 'declining': []}

            # Calculate clicks for each period
            recent_clicks = recent_period.groupby(query_col)['clicks'].sum()
            comparison_clicks = comparison_period.groupby(query_col)['clicks'].sum()

            # Calculate growth rates
            growth_data = []
            for query in set(recent_clicks.index) | set(comparison_clicks.index):
                recent = recent_clicks.get(query, 0)
                comparison = comparison_clicks.get(query, 0)

                if comparison > 0:
                    growth_pct = ((recent - comparison) / comparison) * 100
                elif recent > 0:
                    growth_pct = 100.0  # New content
                else:
                    continue  # No data for either period

                growth_data.append({
                    'query': query,
                    'growth_pct': growth_pct,
                    'recent_clicks': recent,
                    'comparison_clicks': comparison
                })

            # Sort by growth percentage
            growth_data.sort(key=lambda x: x['growth_pct'], reverse=True)

            # Identify trending (growth > 20%)
            trending = [
                f"{item['query']} (+{item['growth_pct']:.1f}%)"
                for item in growth_data
                if item['growth_pct'] > 20 and item['recent_clicks'] >= 10
            ][:10]  # Top 10

            # Identify declining (growth < -20%)
            declining = [
                f"{item['query']} ({item['growth_pct']:.1f}%)"
                for item in reversed(growth_data)
                if item['growth_pct'] < -20 and item['comparison_clicks'] >= 10
            ][:10]  # Top 10

            return {
                'trending': trending,
                'declining': declining
            }

        except Exception as e:
            print(f"Error in trend analysis: {e}")
            return {'trending': [], 'declining': []}

    def get_rich_results_opportunities(self) -> Optional[pd.DataFrame]:
        """
        Get search appearance data showing rich result opportunities.

        Returns:
            DataFrame with search appearance types and their performance
        """
        return self.search_appearance_df if self.search_appearance_df is not None else None

    def get_data_summary(self) -> Dict[str, any]:
        """
        Get a comprehensive summary of all available data.

        Returns:
            Dict with summary statistics from all data sources
        """
        summary = {
            'gsc_available': True if self.df is not None else False,
            'ga4_available': True if self.ga4_df is not None else False,
            'queries_count': len(self.queries_df) if self.queries_df is not None else 0,
            'pages_count': len(self.pages_df) if self.pages_df is not None else 0,
            'countries_available': True if self.countries_df is not None else False,
            'devices_available': True if self.devices_df is not None else False,
            'search_appearance_available': True if self.search_appearance_df is not None else False,
            'dates_available': True if self.dates_df is not None else False,
        }

        # Add device breakdown if available
        if self.devices_df is not None:
            summary['device_breakdown'] = self.get_mobile_vs_desktop_performance()
            summary['is_mobile_first'] = self.is_mobile_first_site()

        # Add top country if available
        if self.countries_df is not None and len(self.countries_df) > 0:
            top_country = self.countries_df.nlargest(1, 'clicks').iloc[0]
            summary['top_country'] = top_country.get('country', 'Unknown')

        return summary


# LEGACY CLASSES REMOVED - Use ClaudeContentGenerator instead
# These template-based generators have been replaced with AI-powered content generation
# See claude_content_generator.py for the modern implementation


# Backward compatibility alias
GSCProcessor = DataProcessor


# Legacy run_pipeline_for_site function removed
# Use seo_automation_main.py -> SEOAutomationPipeline for the modern implementation
# Example:
#   from seo_automation_main import SEOAutomationPipeline
#   pipeline = SEOAutomationPipeline(site_name="example.com", gsc_csv_path="data.csv")
#   result = pipeline.run()

if __name__ == "__main__":
    print("This module has been refactored.")
    print("Use: python seo_automation_main.py --help for the modern CLI interface")
    print("Or import: from seo_automation_main import SEOAutomationPipeline")