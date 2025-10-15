"""
sitemap_analyzer.py
==================
Fetch and analyze WordPress sitemaps, compare with GSC data to find dead content.
Handles WordPress sitemap indexes and individual sitemaps.
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
        self.sitemap_urls = [
            f"{self.site_url}/sitemap.xml",
            f"{self.site_url}/sitemap_index.xml",
            f"{self.site_url}/wp-sitemap.xml",
            f"{self.site_url}/post-sitemap.xml",
        ]
    
    def fetch_sitemap(self) -> List[SitemapURL]:
        """Fetch and parse the sitemap XML, handling WordPress sitemap indexes."""
        
        # Try different sitemap URLs
        root = None
        for sitemap_url in self.sitemap_urls:
            try:
                print(f"  Trying sitemap: {sitemap_url}")
                response = requests.get(sitemap_url, timeout=30)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    print(f"  ✓ Found sitemap at: {sitemap_url}")
                    break
            except Exception as e:
                continue
        
        if root is None:
            print(f"  ⚠️  Could not fetch any sitemap")
            return []
        
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Check if this is a sitemap index (contains other sitemaps)
        sitemap_elements = root.findall('.//ns:sitemap', namespace)
        
        if sitemap_elements:
            # This is a sitemap index - fetch all child sitemaps
            print(f"  Found sitemap index with {len(sitemap_elements)} child sitemaps")
            return self._fetch_from_sitemap_index(root, namespace)
        else:
            # This is a regular sitemap
            return self._parse_sitemap_urls(root, namespace)
    
    def _fetch_from_sitemap_index(self, root: ET.Element, namespace: dict) -> List[SitemapURL]:
        """Fetch URLs from all sitemaps in a sitemap index."""
        all_urls = []
        
        sitemap_elements = root.findall('.//ns:sitemap', namespace)
        
        for sitemap_elem in sitemap_elements:
            loc = sitemap_elem.find('ns:loc', namespace)
            if loc is not None:
                sitemap_url = loc.text
                print(f"  Fetching child sitemap: {sitemap_url}")
                
                try:
                    response = requests.get(sitemap_url, timeout=30)
                    response.raise_for_status()
                    
                    child_root = ET.fromstring(response.content)
                    urls = self._parse_sitemap_urls(child_root, namespace)
                    all_urls.extend(urls)
                    print(f"    ✓ Got {len(urls)} URLs")
                    
                except Exception as e:
                    print(f"    ⚠️  Failed to fetch {sitemap_url}: {e}")
        
        return all_urls
    
    def _parse_sitemap_urls(self, root: ET.Element, namespace: dict) -> List[SitemapURL]:
        """Parse URLs from a sitemap XML."""
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
        
        print(f"DEBUG SITEMAP: Total sitemap URLs: {len(sitemap_set)}")
        print(f"DEBUG SITEMAP: Total GSC URLs: {len(gsc_urls)}")
        print(f"DEBUG SITEMAP: GSC columns: {list(gsc_df.columns)}")
        
        # Find dead content (in sitemap but no GSC data)
        dead_urls = sitemap_set - gsc_urls
        
        # Find performing URLs
        performing_urls = sitemap_set & gsc_urls
        
        # Find URLs in GSC but not in sitemap (might be deleted or orphaned)
        orphaned_urls = gsc_urls - sitemap_set
        
        print(f"DEBUG SITEMAP: Dead content: {len(dead_urls)}")
        print(f"DEBUG SITEMAP: Performing content: {len(performing_urls)}")
        print(f"DEBUG SITEMAP: Orphaned content: {len(orphaned_urls)}")
        
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