"""
wordpress_publisher.py
=====================
Enhanced WordPress publisher with full taxonomy support.
"""

import requests
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class PublishResult:
    """Result of a publishing operation."""
    success: bool
    action: str  # create, update, delete, redirect
    url: str
    post_id: Optional[int] = None
    error: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class WordPressPublisher:
    """Enhanced WordPress publisher with full feature set."""
    
    def __init__(
        self, 
        site_url: str, 
        username: str, 
        application_password: str,
        rate_limit_delay: float = 2.0
    ):
        self.site_url = site_url.rstrip("/")
        self.auth = (username, application_password)
        self.rate_limit_delay = rate_limit_delay
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        time.sleep(self.rate_limit_delay)
    
    def _get_or_create_category(self, category_name: str) -> Optional[int]:
        """Get category ID by name, creating it if it doesn't exist."""
        try:
            # Try to find existing category
            response = requests.get(
                f"{self.api_base}/categories",
                auth=self.auth,
                params={'search': category_name},
                timeout=30
            )
            response.raise_for_status()
            categories = response.json()
            
            # Look for exact match
            for cat in categories:
                if cat['name'].lower() == category_name.lower():
                    return cat['id']
            
            # If not found, try to create it
            response = requests.post(
                f"{self.api_base}/categories",
                auth=self.auth,
                json={'name': category_name},
                timeout=30
            )
            response.raise_for_status()
            new_category = response.json()
            return new_category['id']
            
        except requests.exceptions.HTTPError as e:
            # Check if it's a "term already exists" error
            if e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    if error_data.get('code') == 'term_exists':
                        # WordPress helpfully provides the existing term_id
                        return error_data.get('data', {}).get('term_id')
                except:
                    pass
            print(f"Error getting/creating category '{category_name}': {e}")
            return None
        except Exception as e:
            print(f"Error getting/creating category '{category_name}': {e}")
            return None
    
    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """Get tag ID by name, creating it if it doesn't exist."""
        try:
            # Try to find existing tag
            response = requests.get(
                f"{self.api_base}/tags",
                auth=self.auth,
                params={'search': tag_name},
                timeout=30
            )
            response.raise_for_status()
            tags = response.json()
            
            # Look for exact match
            for tag in tags:
                if tag['name'].lower() == tag_name.lower():
                    return tag['id']
            
            # If not found, try to create it
            response = requests.post(
                f"{self.api_base}/tags",
                auth=self.auth,
                json={'name': tag_name},
                timeout=30
            )
            response.raise_for_status()
            new_tag = response.json()
            return new_tag['id']
            
        except requests.exceptions.HTTPError as e:
            # Check if it's a "term already exists" error
            if e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    if error_data.get('code') == 'term_exists':
                        # WordPress helpfully provides the existing term_id
                        return error_data.get('data', {}).get('term_id')
                except:
                    pass
            print(f"Error getting/creating tag '{tag_name}': {e}")
            return None
        except Exception as e:
            print(f"Error getting/creating tag '{tag_name}': {e}")
            return None
    
    def get_all_posts(self) -> List[Dict]:
        """Fetch all posts from WordPress."""
        posts = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = requests.get(
                    f"{self.api_base}/posts",
                    auth=self.auth,
                    params={'per_page': per_page, 'page': page},
                    timeout=30
                )
                response.raise_for_status()
                
                batch = response.json()
                if not batch:
                    break
                
                posts.extend(batch)
                page += 1
                self._rate_limit()
                
            except Exception as e:
                print(f"Error fetching posts (page {page}): {e}")
                break
        
        return posts
    
    def find_post_by_url(self, url: str) -> Optional[Dict]:
        """Find a post by its URL."""
        # Extract slug from URL
        slug = url.rstrip('/').split('/')[-1]
        
        try:
            response = requests.get(
                f"{self.api_base}/posts",
                auth=self.auth,
                params={'slug': slug},
                timeout=30
            )
            response.raise_for_status()
            posts = response.json()
            
            if posts:
                return posts[0]
            return None
            
        except Exception as e:
            print(f"Error finding post by URL {url}: {e}")
            return None
    
    def create_post(
        self, 
        title: str, 
        content: str,
        meta_title: str = "",
        meta_description: str = "",
        categories: List[str] = None,
        tags: List[str] = None,
        status: str = "publish"
    ) -> PublishResult:
        """Create a new post with full metadata."""
        
        try:
            # Prepare post data
            post_data = {
                "title": title,
                "content": content,
                "status": status
            }
            
            # Handle categories
            if categories:
                category_ids = []
                for cat_name in categories:
                    cat_id = self._get_or_create_category(cat_name)
                    if cat_id:
                        category_ids.append(cat_id)
                if category_ids:
                    post_data["categories"] = category_ids
                    print(f"  ✓ Added categories: {', '.join(categories)}")
            
            # Handle tags
            if tags:
                tag_ids = []
                for tag_name in tags:
                    tag_id = self._get_or_create_tag(tag_name)
                    if tag_id:
                        tag_ids.append(tag_id)
                if tag_ids:
                    post_data["tags"] = tag_ids
                    print(f"  ✓ Added tags: {', '.join(tags)}")
            
            # Add Yoast SEO meta if provided
            if meta_title or meta_description:
                post_data["meta"] = {}
                if meta_title:
                    post_data["meta"]["_yoast_wpseo_title"] = meta_title
                if meta_description:
                    post_data["meta"]["_yoast_wpseo_metadesc"] = meta_description
            
            response = requests.post(
                f"{self.api_base}/posts",
                auth=self.auth,
                json=post_data,
                timeout=30
            )
            response.raise_for_status()
            
            result_data = response.json()
            self._rate_limit()
            
            return PublishResult(
                success=True,
                action="create",
                url=result_data.get('link', ''),
                post_id=result_data.get('id')
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                action="create",
                url="",
                error=str(e)
            )
    
    def update_post(
        self,
        post_id: int,
        title: str = None,
        content: str = None,
        meta_title: str = None,
        meta_description: str = None,
        categories: List[str] = None,
        tags: List[str] = None
    ) -> PublishResult:
        """Update an existing post."""
        
        try:
            # Build update data (only include fields that are provided)
            update_data = {}
            
            if title:
                update_data["title"] = title
            if content:
                update_data["content"] = content
            
            # Handle categories
            if categories:
                category_ids = []
                for cat_name in categories:
                    cat_id = self._get_or_create_category(cat_name)
                    if cat_id:
                        category_ids.append(cat_id)
                if category_ids:
                    update_data["categories"] = category_ids
                    print(f"  ✓ Updated categories: {', '.join(categories)}")
            
            # Handle tags
            if tags:
                tag_ids = []
                for tag_name in tags:
                    tag_id = self._get_or_create_tag(tag_name)
                    if tag_id:
                        tag_ids.append(tag_id)
                if tag_ids:
                    update_data["tags"] = tag_ids
                    print(f"  ✓ Updated tags: {', '.join(tags)}")
            
            # Add Yoast SEO meta
            if meta_title or meta_description:
                update_data["meta"] = {}
                if meta_title:
                    update_data["meta"]["_yoast_wpseo_title"] = meta_title
                if meta_description:
                    update_data["meta"]["_yoast_wpseo_metadesc"] = meta_description
            
            response = requests.post(
                f"{self.api_base}/posts/{post_id}",
                auth=self.auth,
                json=update_data,
                timeout=30
            )
            response.raise_for_status()
            
            result_data = response.json()
            self._rate_limit()
            
            return PublishResult(
                success=True,
                action="update",
                url=result_data.get('link', ''),
                post_id=post_id
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                action="update",
                url="",
                post_id=post_id,
                error=str(e)
            )
    
    def delete_post(self, post_id: int, force: bool = True) -> PublishResult:
        """Delete a post (force=True permanently deletes, force=False moves to trash)."""
        
        try:
            response = requests.delete(
                f"{self.api_base}/posts/{post_id}",
                auth=self.auth,
                params={'force': force},
                timeout=30
            )
            response.raise_for_status()
            self._rate_limit()
            
            return PublishResult(
                success=True,
                action="delete",
                url="",
                post_id=post_id
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                action="delete",
                url="",
                post_id=post_id,
                error=str(e)
            )
    
    def create_301_redirect(
        self, 
        source_url: str, 
        target_url: str
    ) -> PublishResult:
        """Create a 301 redirect (requires Redirection plugin)."""
        
        try:
            # Strip domain from URLs to get paths
            source_path = source_url.replace(self.site_url, '')
            target_path = target_url.replace(self.site_url, '')
            
            redirect_data = {
                "url": source_path,
                "match_type": "url",
                "action_type": "url",
                "action_data": {"url": target_path},
                "action_code": 301,
                "group_id": 1  # Default group
            }
            
            response = requests.post(
                f"{self.site_url}/wp-json/redirection/v1/redirect",
                auth=self.auth,
                json=redirect_data,
                timeout=30
            )
            response.raise_for_status()
            self._rate_limit()
            
            return PublishResult(
                success=True,
                action="redirect",
                url=f"{source_path} -> {target_path}"
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                action="redirect",
                url=source_url,
                error=str(e)
            )
    
    def get_internal_link_suggestions(
        self, 
        keywords: List[str], 
        limit: int = 5
    ) -> List[Dict]:
        """Find relevant internal posts to link to based on keywords."""
        suggestions = []
        
        for keyword in keywords[:3]:  # Check top 3 keywords
            try:
                response = requests.get(
                    f"{self.api_base}/posts",
                    auth=self.auth,
                    params={'search': keyword, 'per_page': limit},
                    timeout=30
                )
                response.raise_for_status()
                posts = response.json()
                
                for post in posts:
                    suggestions.append({
                        'title': post['title']['rendered'],
                        'url': post['link'],
                        'id': post['id']
                    })
                
                self._rate_limit()
                
            except Exception as e:
                print(f"Error searching for internal links with '{keyword}': {e}")
        
        # Remove duplicates
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['id'] not in seen:
                seen.add(s['id'])
                unique_suggestions.append(s)
        
        return unique_suggestions[:limit]