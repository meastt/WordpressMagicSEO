"""
SEO Issue Fixer
===============
Automatically fixes SEO issues found in audits by updating WordPress posts/pages.
"""

import requests
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup

from wordpress.publisher import WordPressPublisher


class SEOIssueFixer:
    """Fixes SEO issues by updating WordPress content."""
    
    def __init__(
        self,
        site_url: str,
        wp_username: str,
        wp_app_password: str,
        rate_limit_delay: float = 1.0
    ):
        self.site_url = site_url.rstrip("/")
        self.wp_publisher = WordPressPublisher(
            site_url=site_url,
            username=wp_username,
            application_password=wp_app_password,
            rate_limit_delay=rate_limit_delay
        )
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (wp_username, wp_app_password)
    
    def fix_issue(self, issue_type: str, category: str, urls: List[str]) -> Dict:
        """
        Fix a specific issue type across multiple URLs.
        
        Args:
            issue_type: Type of issue (e.g., 'h1_presence', 'title_presence')
            category: Issue category (e.g., 'onpage', 'technical')
            urls: List of URLs to fix
            
        Returns:
            Dict with success status, fixed_count, failed_count, and details
        """
        results = {
            "success": True,
            "fixed_count": 0,
            "failed_count": 0,
            "errors": [],
            "fixed_urls": []
        }
        
        for url in urls:
            try:
                # Get post/page ID from URL
                post_id, post_type = self._get_post_id_from_url(url)
                if not post_id:
                    results["failed_count"] += 1
                    results["errors"].append(f"Could not find post ID for {url}")
                    continue
                
                # Fix the specific issue
                fix_method = f"_fix_{issue_type}"
                if hasattr(self, fix_method):
                    fix_result = getattr(self, fix_method)(post_id, post_type, url)
                    if fix_result:
                        results["fixed_count"] += 1
                        results["fixed_urls"].append(url)
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"Failed to fix {issue_type} for {url}")
                else:
                    # Generic fix attempt
                    fix_result = self._fix_generic(post_id, post_type, url, issue_type, category)
                    if fix_result:
                        results["fixed_count"] += 1
                        results["fixed_urls"].append(url)
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"No fix handler for {issue_type}")
                
                time.sleep(self.wp_publisher.rate_limit_delay)
                
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append(f"Error fixing {url}: {str(e)}")
        
        results["success"] = results["failed_count"] == 0
        return results
    
    def _get_post_id_from_url(self, url: str) -> Tuple[Optional[int], Optional[str]]:
        """Get WordPress post/page ID from URL by querying the REST API."""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')
            
            # Try to get post by slug
            slug = path.split('/')[-1] if path else None
            if not slug:
                return None, None
            
            # Try posts endpoint
            response = requests.get(
                f"{self.api_base}/posts",
                auth=self.auth,
                params={'slug': slug, 'per_page': 1},
                timeout=30
            )
            if response.ok:
                posts = response.json()
                if posts:
                    return posts[0]['id'], 'post'
            
            # Try pages endpoint
            response = requests.get(
                f"{self.api_base}/pages",
                auth=self.auth,
                params={'slug': slug, 'per_page': 1},
                timeout=30
            )
            if response.ok:
                pages = response.json()
                if pages:
                    return pages[0]['id'], 'page'
            
            # Try searching by link
            response = requests.get(
                f"{self.api_base}/posts",
                auth=self.auth,
                params={'search': slug, 'per_page': 10},
                timeout=30
            )
            if response.ok:
                posts = response.json()
                for post in posts:
                    if post.get('link', '').rstrip('/') == url.rstrip('/'):
                        return post['id'], 'post'
            
            return None, None
            
        except Exception as e:
            print(f"Error getting post ID for {url}: {e}")
            return None, None
    
    def _get_post_content(self, post_id: int, post_type: str = 'post') -> Dict:
        """Get current post content from WordPress."""
        try:
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = requests.get(
                endpoint, 
                auth=self.auth, 
                params={'context': 'edit'},  # Get raw content for editing
                timeout=30
            )
            if response.ok:
                return response.json()
            return {}
        except:
            return {}
    
    def _fix_h1_presence(self, post_id: int, post_type: str, url: str) -> bool:
        """Add H1 tag if missing."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            # Use raw content for editing (not rendered HTML)
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            
            if not title:
                return False
            
            # Check if H1 already exists
            soup = BeautifulSoup(content_raw, 'html.parser')
            if soup.find('h1'):
                return True  # Already has H1
            
            # Add H1 tag at the beginning of content
            h1_tag = f'<h1>{title}</h1>\n\n'
            new_content = h1_tag + content_raw
            
            # Update post using direct API call to set raw content
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = requests.post(
                endpoint,
                auth=self.auth,
                json={'content': new_content},
                timeout=30
            )
            
            if response.ok:
                time.sleep(self.wp_publisher.rate_limit_delay)
                return True
            return False
            
        except Exception as e:
            print(f"Error fixing H1 for {url}: {e}")
            return False
    
    def _fix_title_presence(self, post_id: int, post_type: str, url: str) -> bool:
        """Add meta title if missing."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            title = post_data.get('title', {}).get('rendered', '')
            if not title:
                return False
            
            # Set meta title to post title if not set
            meta_title = title[:60] if len(title) > 60 else title  # SEO best practice: 50-60 chars
            
            result = self.wp_publisher.update_post(
                post_id=post_id,
                meta_title=meta_title,
                item_type=post_type
            )
            return result.success
            
        except Exception as e:
            print(f"Error fixing title for {url}: {e}")
            return False
    
    def _fix_meta_description_presence(self, post_id: int, post_type: str, url: str) -> bool:
        """Add meta description if missing."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content = post_data.get('content', {}).get('rendered', '')
            title = post_data.get('title', {}).get('rendered', '')
            
            # Extract text from HTML
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text().strip()[:160]  # Meta desc should be 120-160 chars
            
            # Generate meta description
            if text_content:
                meta_desc = text_content[:157] + '...' if len(text_content) > 157 else text_content
            else:
                meta_desc = f"Learn about {title}"  # Fallback
            
            result = self.wp_publisher.update_post(
                post_id=post_id,
                meta_description=meta_desc,
                item_type=post_type
            )
            return result.success
            
        except Exception as e:
            print(f"Error fixing meta description for {url}: {e}")
            return False
    
    def _fix_generic(self, post_id: int, post_type: str, url: str, issue_type: str, category: str) -> bool:
        """Generic fix handler for issues without specific handlers."""
        # For now, just return False - specific handlers need to be implemented
        print(f"No specific handler for {issue_type} (category: {category})")
        return False

