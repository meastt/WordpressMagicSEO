"""
sitemap_analyzer.py
==================
Fetch and analyze WordPress sitemaps, compare with GSC data to find dead content.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Set
from dataclasses import dataclass
import pandas as pd


@dataclass
class SitemapURL:
    """Represents a URL from the sitemap."""
    url: str
    lastmod: str = ""
    priority: float = 0.5
    changefreq: str = ""


class SitemapAnalyzer:
    """Fetch and analyze WordPress sitemaps."""
    
    def __init__(self, site_url: str):
        self.site_url = site_url.rstrip("/")
        self.sitemap_url = f"{self.site_url}/sitemap.xml"
    
    def fetch_sitemap(self) -> List[SitemapURL]:
        """Fetch and parse the sitemap XML."""
        try:
            response = requests.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Handle namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            urls = []
            for url_element in root.findall('.//ns:url', namespace):
                loc = url_element.find('ns:loc', namespace)
                lastmod = url_element.find('ns:lastmod', namespace)
                priority = url_element.find('ns:priority', namespace)
                changefreq = url_element.find('ns:changefreq', namespace)
                
                if loc is not None:
                    sitemap_url = SitemapURL(
                        url=loc.text,
                        lastmod=lastmod.text if lastmod is not None else "",
                        priority=float(priority.text) if priority is not None else 0.5,
                        changefreq=changefreq.text if changefreq is not None else ""
                    )
                    urls.append(sitemap_url)
            
            return urls
        
        except Exception as e:
            print(f"Error fetching sitemap: {e}")
            return []
    
    def compare_with_gsc(
        self, 
        sitemap_urls: List[SitemapURL], 
        gsc_df: pd.DataFrame
    ) -> Dict[str, List[str]]:
        """Compare sitemap URLs with GSC data to find dead content."""
        
        # Get all URLs from sitemap
        sitemap_set = {url.url for url in sitemap_urls}
        
        # Get all URLs that have GSC data (any impressions/clicks)
        gsc_urls = set(gsc_df['page'].unique())
        
        # Find dead content (in sitemap but no GSC data)
        dead_urls = sitemap_set - gsc_urls
        
        # Find performing URLs
        performing_urls = sitemap_set & gsc_urls
        
        # Find URLs in GSC but not in sitemap (might be deleted or orphaned)
        orphaned_urls = gsc_urls - sitemap_set
        
        return {
            'dead_content': list(dead_urls),
            'performing_content': list(performing_urls),
            'orphaned_content': list(orphaned_urls)
        }
    
    def find_duplicate_content_candidates(
        self, 
        gsc_df: pd.DataFrame
    ) -> List[Dict]:
        """Find URLs that might be duplicate content based on shared keywords."""
        
        # Group by query and find URLs that rank for the same queries
        query_groups = gsc_df.groupby('query')['page'].apply(list).to_dict()
        
        duplicates = []
        for query, urls in query_groups.items():
            if len(urls) > 1:
                # Multiple URLs rank for same query - potential duplicates
                # Get performance metrics for each
                url_metrics = []
                for url in urls:
                    url_data = gsc_df[gsc_df['page'] == url]
                    total_clicks = url_data['clicks'].sum()
                    total_impressions = url_data['impressions'].sum()
                    avg_position = url_data['position'].mean()
                    
                    url_metrics.append({
                        'url': url,
                        'clicks': total_clicks,
                        'impressions': total_impressions,
                        'position': avg_position
                    })
                
                # Sort by performance (clicks first, then impressions)
                url_metrics.sort(key=lambda x: (x['clicks'], x['impressions']), reverse=True)
                
                # Winner is best performing, losers are candidates for 301
                winner = url_metrics[0]
                losers = url_metrics[1:]
                
                duplicates.append({
                    'query': query,
                    'winner': winner,
                    'redirect_candidates': losers
                })
        
        return duplicates
    
    def analyze_url_performance(
        self, 
        url: str, 
        gsc_df: pd.DataFrame
    ) -> Dict:
        """Get detailed performance metrics for a specific URL."""
        
        url_data = gsc_df[gsc_df['page'] == url]
        
        if url_data.empty:
            return {
                'url': url,
                'status': 'no_data',
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0,
                'avg_position': 0,
                'top_queries': []
            }
        
        # Get top queries for this URL
        top_queries = (
            url_data.nlargest(10, 'impressions')[['query', 'clicks', 'impressions', 'position']]
            .to_dict('records')
        )
        
        return {
            'url': url,
            'status': 'active',
            'total_clicks': int(url_data['clicks'].sum()),
            'total_impressions': int(url_data['impressions'].sum()),
            'avg_ctr': float(url_data['ctr'].mean()),
            'avg_position': float(url_data['position'].mean()),
            'top_queries': top_queries
        }