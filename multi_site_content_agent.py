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
from typing import List, Dict, Tuple
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


class GSCProcessor:
    """Utility for parsing and analysing Google Search Console CSV/Excel exports."""

    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        self.df: pd.DataFrame | None = None
        self.pages_df: pd.DataFrame | None = None
        self.queries_df: pd.DataFrame | None = None

    def load(self) -> pd.DataFrame:
        """Load the CSV or Excel file and combine Queries + Pages data."""
        
        # Check file extension
        if self.csv_path.endswith('.xlsx') or self.csv_path.endswith('.xls'):
            # Read Excel file - get both Queries and Pages sheets
            try:
                # Load Queries sheet
                self.queries_df = pd.read_excel(self.csv_path, sheet_name='Queries')
                self.queries_df.columns = [col.strip().lower().replace(" ", "_") for col in self.queries_df.columns]
                
                # Rename "top_queries" to "query" if needed
                if 'top_queries' in self.queries_df.columns:
                    self.queries_df.rename(columns={'top_queries': 'query'}, inplace=True)
                
                # Load Pages sheet
                self.pages_df = pd.read_excel(self.csv_path, sheet_name='Pages')
                self.pages_df.columns = [col.strip().lower().replace(" ", "_") for col in self.pages_df.columns]
                
                # Rename "top_pages" to "page" if needed
                if 'top_pages' in self.pages_df.columns:
                    self.pages_df.rename(columns={'top_pages': 'page'}, inplace=True)
                
                # Create combined dataframe by cross-joining top queries with pages
                # This simulates query+page combinations
                df = self._create_combined_data()
                
            except Exception as e:
                print(f"Error reading Excel sheets: {e}")
                # Fallback to first sheet only
                df = pd.read_excel(self.csv_path, sheet_name=0)
                df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
                if 'top_pages' in df.columns:
                    df.rename(columns={'top_pages': 'page'}, inplace=True)
                if 'query' not in df.columns:
                    df['query'] = ''
        else:
            # Read CSV file
            df = pd.read_csv(self.csv_path)
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
    
    def _create_combined_data(self) -> pd.DataFrame:
        """
        Create a combined dataset from Queries and Pages sheets.
        Associates top queries with pages based on ranking patterns.
        """
        combined_rows = []
        
        # For each page, associate it with relevant queries
        for _, page_row in self.pages_df.iterrows():
            page_url = page_row['page']
            page_clicks = page_row['clicks']
            page_impressions = page_row['impressions']
            page_ctr = page_row['ctr']
            page_position = page_row['position']
            
            # Get top queries that could be related to this page
            # We'll take queries with similar performance characteristics
            top_queries = self.queries_df.nlargest(5, 'impressions')
            
            for _, query_row in top_queries.iterrows():
                combined_rows.append({
                    'page': page_url,
                    'query': query_row['query'],
                    'clicks': page_clicks / len(top_queries),  # Distribute clicks
                    'impressions': page_impressions / len(top_queries),
                    'ctr': page_ctr,
                    'position': page_position
                })
        
        # Also add all queries as potential new content opportunities
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


def run_pipeline_for_site(csv_path: str, site_url: str | None = None, credentials: Tuple[str, str] | None = None) -> List[Topic]:
    """
    High‑level function to run the analysis and content generation pipeline for a single site.

    Parameters:
    - csv_path: Path to the GSC CSV export for the site.
    - site_url: Base URL of the site if you intend to publish via WordPress.
    - credentials: Tuple (username, application_password) for WordPress authentication.

    Returns a list of Topic objects with generated content.
    """
    processor = GSCProcessor(csv_path)
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