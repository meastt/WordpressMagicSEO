"""
SEO Fix Tracker
===============
Tracks which URLs have been fixed for which issues to avoid redundant audits.
"""

import json
import os
from typing import Dict, List, Set
from datetime import datetime
from urllib.parse import urlparse


class SEOFixTracker:
    """Tracks fixed SEO issues to avoid redundant audits."""
    
    def __init__(self, site_url: str):
        """
        Initialize fix tracker for a site.
        
        Args:
            site_url: Base URL of the site (e.g., https://example.com)
        """
        self.site_url = site_url.rstrip("/")
        parsed = urlparse(self.site_url)
        self.site_domain = parsed.netloc.replace('www.', '')
        self.state_file = f"{self.site_domain}_seo_fixes.json"
        self.fixes = self._load_fixes()
    
    def _load_fixes(self) -> Dict:
        """Load fix history from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_fixes(self):
        """Save fix history to file."""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.fixes, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save fix history: {e}")
    
    def record_fix(self, url: str, issue_type: str, category: str, success: bool = True):
        """
        Record that a URL was fixed for a specific issue.
        
        Args:
            url: URL that was fixed
            issue_type: Type of issue (e.g., 'h1_presence')
            category: Issue category (e.g., 'onpage')
            success: Whether the fix was successful
        """
        if url not in self.fixes:
            self.fixes[url] = {}
        
        issue_key = f"{category}.{issue_type}"
        if issue_key not in self.fixes[url]:
            self.fixes[url][issue_key] = []
        
        self.fixes[url][issue_key].append({
            "fixed_at": datetime.now().isoformat(),
            "success": success
        })
        
        self._save_fixes()
    
    def is_fixed(self, url: str, issue_type: str, category: str) -> bool:
        """
        Check if a URL was already fixed for a specific issue.
        
        Args:
            url: URL to check
            issue_type: Type of issue
            category: Issue category
            
        Returns:
            True if URL was successfully fixed for this issue
        """
        if url not in self.fixes:
            return False
        
        issue_key = f"{category}.{issue_type}"
        if issue_key not in self.fixes[url]:
            return False
        
        # Check if there's at least one successful fix
        fixes = self.fixes[url][issue_key]
        return any(fix.get("success", False) for fix in fixes)
    
    def get_fixed_urls(self, issue_type: str, category: str) -> Set[str]:
        """
        Get all URLs that have been fixed for a specific issue.
        
        Args:
            issue_type: Type of issue
            category: Issue category
            
        Returns:
            Set of URLs that have been fixed
        """
        issue_key = f"{category}.{issue_type}"
        fixed_urls = set()
        
        for url, issues in self.fixes.items():
            if issue_key in issues:
                fixes = issues[issue_key]
                if any(fix.get("success", False) for fix in fixes):
                    fixed_urls.add(url)
        
        return fixed_urls
    
    def get_fix_history(self, url: str) -> Dict:
        """Get fix history for a specific URL."""
        return self.fixes.get(url, {})
    
    def clear_fix(self, url: str, issue_type: str = None, category: str = None):
        """
        Clear fix history for a URL (or specific issue).
        
        Args:
            url: URL to clear
            issue_type: Optional - clear only this issue type
            category: Optional - clear only this category
        """
        if url not in self.fixes:
            return
        
        if issue_type and category:
            issue_key = f"{category}.{issue_type}"
            if issue_key in self.fixes[url]:
                del self.fixes[url][issue_key]
        else:
            del self.fixes[url]
        
        self._save_fixes()
    
    def get_stats(self) -> Dict:
        """Get statistics about fixes."""
        total_fixes = 0
        successful_fixes = 0
        unique_urls = set()
        
        for url, issues in self.fixes.items():
            unique_urls.add(url)
            for issue_key, fixes in issues.items():
                total_fixes += len(fixes)
                successful_fixes += sum(1 for fix in fixes if fix.get("success", False))
        
        return {
            "total_urls_fixed": len(unique_urls),
            "total_fixes": total_fixes,
            "successful_fixes": successful_fixes,
            "failed_fixes": total_fixes - successful_fixes
        }

