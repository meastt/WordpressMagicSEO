"""
Affiliate Link Manager
----------------------
Manages affiliate links for automated insertion into content.
Stores links per site with product information.
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import csv
import io


class AffiliateLinkManager:
    """Manage affiliate links for a specific site."""
    
    def __init__(self, site_name: str, storage_dir: str = "/tmp"):
        """
        Initialize affiliate link manager for a specific site.
        
        Args:
            site_name: Domain name of the site
            storage_dir: Directory to store affiliate links data
        """
        self.site_name = site_name
        self.storage_file = os.path.join(storage_dir, f"{site_name}_affiliate_links.json")
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Load affiliate links from disk or create new structure."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load affiliate links file, creating new: {e}")
        
        return {
            "site_name": self.site_name,
            "links": [],
            "last_updated": None
        }
    
    def save(self):
        """Save affiliate links to disk."""
        try:
            self.data['last_updated'] = datetime.now().isoformat()
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save affiliate links file: {e}")
    
    def add_link(
        self,
        url: str,
        brand: str,
        product_name: str,
        product_type: str,
        keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        Add a single affiliate link.
        
        Args:
            url: Full affiliate link URL
            brand: Brand name (e.g., "Traeger")
            product_name: Product name (e.g., "Flatrock Griddle")
            product_type: Product category (e.g., "outdoor griddle")
            keywords: Optional list of keywords for matching
            
        Returns:
            Dict: The added link record
        """
        link = {
            "id": len(self.data['links']) + 1,
            "url": url,
            "brand": brand.lower(),
            "product_name": product_name,
            "product_type": product_type.lower(),
            "keywords": keywords or [],
            "added_at": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.data['links'].append(link)
        self.save()
        return link
    
    def add_links_from_csv(self, csv_content: str) -> Dict:
        """
        Add multiple links from CSV content.
        
        Expected CSV format:
        url,brand,product_name,product_type,keywords(optional)
        
        Args:
            csv_content: CSV file content as string
            
        Returns:
            Dict with counts of added, skipped, and errors
        """
        results = {
            "added": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # Normalize column names (strip whitespace, lowercase)
            fieldnames = [col.strip().lower() for col in reader.fieldnames]
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                try:
                    # Normalize keys
                    row_normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
                    
                    # Required fields
                    url = row_normalized.get('url', '')
                    brand = row_normalized.get('brand', '')
                    product_name = row_normalized.get('product_name', '')
                    product_type = row_normalized.get('product_type', '')
                    
                    # Validate required fields
                    if not all([url, brand, product_name, product_type]):
                        results['errors'].append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    # Optional keywords (comma-separated)
                    keywords_str = row_normalized.get('keywords', '')
                    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()] if keywords_str else []
                    
                    # Check for duplicates
                    if any(link['url'] == url for link in self.data['links']):
                        results['skipped'] += 1
                        continue
                    
                    # Add the link
                    self.add_link(url, brand, product_name, product_type, keywords)
                    results['added'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Row {row_num}: {str(e)}")
        
        except Exception as e:
            results['errors'].append(f"CSV parsing error: {str(e)}")
        
        return results
    
    def get_all_links(self) -> List[Dict]:
        """Get all affiliate links."""
        return self.data['links']
    
    def search_links(
        self,
        keywords: Optional[List[str]] = None,
        product_type: Optional[str] = None,
        brand: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for relevant affiliate links based on criteria.
        
        Args:
            keywords: Keywords to match against
            product_type: Product type to filter by
            brand: Brand name to filter by
            
        Returns:
            List of matching affiliate links, sorted by relevance
        """
        results = []
        
        for link in self.data['links']:
            score = 0
            
            # Match by brand
            if brand and brand.lower() in link['brand']:
                score += 10
            
            # Match by product type
            if product_type and product_type.lower() in link['product_type']:
                score += 5
            
            # Match by keywords
            if keywords:
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    # Check in product name
                    if keyword_lower in link['product_name'].lower():
                        score += 3
                    # Check in product type
                    if keyword_lower in link['product_type']:
                        score += 2
                    # Check in stored keywords
                    if any(keyword_lower in kw.lower() for kw in link.get('keywords', [])):
                        score += 1
            
            if score > 0:
                results.append({**link, 'relevance_score': score})
        
        # Sort by relevance score
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    def increment_usage(self, link_id: int):
        """Increment usage count for a link."""
        for link in self.data['links']:
            if link['id'] == link_id:
                link['usage_count'] = link.get('usage_count', 0) + 1
                self.save()
                break
    
    def delete_link(self, link_id: int) -> bool:
        """
        Delete an affiliate link by ID.
        
        Args:
            link_id: ID of the link to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        original_count = len(self.data['links'])
        self.data['links'] = [link for link in self.data['links'] if link['id'] != link_id]
        
        if len(self.data['links']) < original_count:
            self.save()
            return True
        return False
    
    def clear_all_links(self):
        """Clear all affiliate links (use with caution)."""
        self.data['links'] = []
        self.save()
    
    def get_stats(self) -> Dict:
        """Get statistics about affiliate links."""
        links = self.data['links']
        
        brands = set(link['brand'] for link in links)
        types = set(link['product_type'] for link in links)
        total_usage = sum(link.get('usage_count', 0) for link in links)
        
        return {
            "total_links": len(links),
            "unique_brands": len(brands),
            "unique_types": len(types),
            "total_usage": total_usage,
            "last_updated": self.data.get('last_updated')
        }
