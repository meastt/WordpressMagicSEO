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


@dataclass
class Topic:
    """Represents a content topic and its associated metadata."""

    title: str
    primary_keywords: List[str]
    publish_month: str
    description: str = ""
    outline: List[str] = field(default_factory=list)
    meta_title: str = ""
    meta_description: str = ""
    body: str = ""  # The generated article content

    def generate_outline(self) -> None:
        """Generate a basic outline for the topic."""
        h1 = self.title
        h2_sections = [
            "Introduction",
            "Key features and considerations",
            "Top products or examples",
            "How to choose the right option",
            "Conclusion & next steps",
        ]
        self.outline = [h1] + h2_sections

    def generate_meta(self) -> None:
        """Create a simple meta title and description based on the primary keywords."""
        keyword_part = self.primary_keywords[0].capitalize()
        self.meta_title = f"{keyword_part} – {self.title}"
        summary = (
            f"Learn about {self.title.lower()} including features, pros and cons, "
            f"and tips for choosing the right one. Our guide covers {', '.join(self.primary_keywords)}."
        )
        if len(summary) > 155:
            summary = summary[:155].rsplit(" ", 1)[0] + "…"
        self.meta_description = summary


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
                    # Load both sheets
                    self.queries_df = pd.read_excel(self.gsc_path, sheet_name='Queries')
                    self.queries_df.columns = [col.strip().lower().replace(" ", "_") for col in self.queries_df.columns]

                    if 'top_queries' in self.queries_df.columns:
                        self.queries_df.rename(columns={'top_queries': 'query'}, inplace=True)

                    self.pages_df = pd.read_excel(self.gsc_path, sheet_name='Pages')
                    self.pages_df.columns = [col.strip().lower().replace(" ", "_") for col in self.pages_df.columns]

                    if 'top_pages' in self.pages_df.columns:
                        self.pages_df.rename(columns={'top_pages': 'page'}, inplace=True)

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
        
        self.df = df
        return df
    
    def load_ga4(self) -> pd.DataFrame:
        """
        Load Google Analytics 4 CSV export.
        
        Expected columns (flexible, will normalize):
        - page / landing_page / page_path
        - sessions
        - engagement_rate
        - avg_engagement_time / average_engagement_time
        - bounce_rate
        - conversions (optional)
        
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

        # Read Excel or CSV file
        if self.ga4_path.endswith('.xlsx') or self.ga4_path.endswith('.xls'):
            # Read Excel file (first sheet)
            df = pd.read_excel(self.ga4_path, sheet_name=0)
        else:
            # Read CSV file with encoding detection
            try:
                # Try UTF-8 first (most common)
                df = pd.read_csv(self.ga4_path, encoding='utf-8')
            except UnicodeDecodeError:
                # Fall back to latin-1 (handles most other encodings)
                try:
                    df = pd.read_csv(self.ga4_path, encoding='latin-1')
                except Exception:
                    # Last resort: ignore errors
                    df = pd.read_csv(self.ga4_path, encoding='utf-8', errors='ignore')
        
        # Normalize column names
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Debug: print available columns
        print(f"GA4 columns found: {list(df.columns)}")

        # Map common variations to standard names (including more variations)
        column_mapping = {
            'landing_page': 'page',
            'page_path': 'page',
            'page_location': 'page',
            'page_path_and_screen_class': 'page',
            'url': 'page',
            'average_engagement_time': 'avg_engagement_time',
            'average_engagement_time_per_session': 'avg_engagement_time',
            'engaged_sessions_per_user': 'engagement_rate',
            'engagement_rate': 'engagement_rate',
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)

        # If still no 'page' column, try to find any URL-like column
        if 'page' not in df.columns:
            # Look for any column that might contain URLs
            url_candidates = [col for col in df.columns if any(x in col for x in ['page', 'url', 'path', 'landing'])]
            if url_candidates:
                print(f"Using column '{url_candidates[0]}' as 'page'")
                df.rename(columns={url_candidates[0]: 'page'}, inplace=True)
            else:
                # GA4 data is optional, so return empty instead of error
                print(f"Warning: GA4 file has no recognizable page/URL column. Columns: {list(df.columns)}")
                print("Skipping GA4 data - only GSC data will be used.")
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
        Create a dataset from Pages sheet with derived keywords from URLs.
        Returns pages with their stats - keywords will be derived from URL/title.
        """
        combined_rows = []
        
        # Add all pages with their actual stats
        for _, page_row in self.pages_df.iterrows():
            page_url = page_row['page']
            
            # Extract potential keywords from URL path
            # e.g., "https://site.com/bobcats/" -> "bobcats"
            url_parts = page_url.rstrip('/').split('/')
            url_slug = url_parts[-1] if url_parts else ''
            # Convert slug to readable keywords (replace hyphens with spaces)
            derived_keyword = url_slug.replace('-', ' ')
            
            combined_rows.append({
                'page': page_url,
                'query': derived_keyword,  # Derived from URL for compatibility
                'clicks': page_row['clicks'],
                'impressions': page_row['impressions'],
                'ctr': page_row['ctr'],
                'position': page_row['position']
            })
        
        # Add all queries as potential new content opportunities (orphaned queries)
        for _, query_row in self.queries_df.iterrows():
            combined_rows.append({
                'page': '',  # No page yet - content gap
                'query': query_row['query'],
                'clicks': query_row['clicks'],
                'impressions': query_row['impressions'],
                'ctr': query_row['ctr'],
                'position': query_row['position']
            })
        
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


class TopicPlanner:
    """Generate topic objects from high‑opportunity queries."""

    def __init__(self, base_month: str | None = None) -> None:
        # Default to current month if not provided
        if base_month is None:
            today = datetime.date.today()
            base_month = today.strftime("%B %Y")
        self.base_month = base_month

    def _derive_title(self, query: str) -> str:
        """Convert a search query into a capitalised article title."""
        # Simple heuristic: capitalise each word and ensure the query ends with a question mark removed.
        title = re.sub(r"\b\w+\b", lambda m: m.group().capitalize(), query)
        return title

    def create_topics_from_queries(self, queries: List[str]) -> List[Topic]:
        topics: List[Topic] = []
        for q in queries:
            title = self._derive_title(q)
            # Use the query itself as the primary keyword
            topic = Topic(title=title, primary_keywords=[q], publish_month=self.base_month)
            topic.generate_outline()
            topic.generate_meta()
            topics.append(topic)
        return topics


class ContentGenerator:
    """Generate article text from a Topic using simple heuristics."""

    def generate_article(self, topic: Topic) -> str:
        sections = topic.outline[1:]
        lines: List[str] = []
        lines.append(f"# {topic.title}\n")
        for section in sections:
            lines.append(f"## {section}\n")
            # Use simple heuristics similar to the MVP generator
            if section == "Introduction":
                lines.append(
                    f"This article explores {topic.title.lower()}. We'll discuss why it's important, key features to look for and how it fits into your outdoor cooking needs.\n"
                )
            elif section == "Key features and considerations":
                lines.append(
                    "Consider factors such as build quality, fuel type, size, heat distribution and ease of cleaning when evaluating options in this category.\n"
                )
            elif section == "Top products or examples":
                lines.append(
                    "Examples range from entry‑level units with basic functionality to premium models featuring smart technology and modular design.\n"
                )
            elif section == "How to choose the right option":
                lines.append(
                    "Think about your budget, space and desired features. Read reviews, compare specs and match the product to your cooking style.\n"
                )
            elif section == "Conclusion & next steps":
                lines.append(
                    "By understanding these factors you can make an informed decision and elevate your cooking experience. Continue researching and testing to find the perfect fit.\n"
                )
        article = "\n".join(lines)
        topic.body = article
        return article


class WordPressPublisher:
    """
    A lightweight wrapper for interacting with the WordPress REST API.  Requires
    a site URL and credentials (username and application password).  See:
    https://developer.wordpress.org/rest-api/ for details.

    These methods are stubs: they will not run unless valid credentials and
    network access are provided.  Use them as a starting point for your own
    implementation.
    """

    def __init__(self, site_url: str, username: str, application_password: str) -> None:
        self.site_url = site_url.rstrip("/")
        self.auth = (username, application_password)

    def post_article(self, title: str, content: str, status: str = "publish") -> Dict:
        """Create a new post on WordPress."""
        endpoint = f"{self.site_url}/wp-json/wp/v2/posts"
        data = {
            "title": title,
            "content": content,
            "status": status,
        }
        resp = requests.post(endpoint, auth=self.auth, json=data)
        resp.raise_for_status()
        return resp.json()

    def update_article(self, post_id: int, title: str, content: str) -> Dict:
        """Update an existing post by ID."""
        endpoint = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}"
        data = {"title": title, "content": content}
        resp = requests.post(endpoint, auth=self.auth, json=data)
        resp.raise_for_status()
        return resp.json()


# Backward compatibility alias
GSCProcessor = DataProcessor


def run_pipeline_for_site(csv_path: str, site_url: str | None = None, credentials: Tuple[str, str] | None = None) -> List[Topic]:
    """
    High‑level function to run the analysis and content generation pipeline for a single site.

    Parameters:
    - csv_path: Path to the GSC CSV export for the site.
    - site_url: Base URL of the site if you intend to publish via WordPress.
    - credentials: Tuple (username, application_password) for WordPress authentication.

    Returns a list of Topic objects with generated content.
    """
    processor = DataProcessor(csv_path)
    df = processor.load()
    refresh_candidates = processor.identify_refresh_candidates()
    # Extract new query opportunities (for demonstration we take top 5 queries)
    queries = processor.extract_query_opportunities(top_n=5)
    planner = TopicPlanner()
    topics = planner.create_topics_from_queries(queries)
    generator = ContentGenerator()
    for topic in topics:
        generator.generate_article(topic)
    # Optionally publish or update posts via WordPress
    if site_url and credentials:
        wp = WordPressPublisher(site_url, credentials[0], credentials[1])
        for topic in topics:
            # NOTE: This will attempt to create a new post; adjust as needed to update existing posts.
            try:
                wp.post_article(topic.title, topic.body)
            except Exception as e:
                print(f"Failed to publish {topic.title}: {e}")
    return topics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the multi‑site content agent pipeline.")
    parser.add_argument("csv_path", help="Path to the GSC CSV export")
    parser.add_argument("--site_url", help="Base URL of the WordPress site (optional)")
    parser.add_argument("--username", help="WordPress username (optional)")
    parser.add_argument("--application_password", help="WordPress application password (optional)")
    args = parser.parse_args()
    creds = None
    if args.site_url and args.username and args.application_password:
        creds = (args.username, args.application_password)
    run_pipeline_for_site(args.csv_path, args.site_url, creds)