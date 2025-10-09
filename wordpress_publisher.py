"""
wordpress_publisher.py
=====================
Enhanced WordPress publisher with scheduling, 301 redirects, and metadata management.
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
            # Get or create category IDs
            category_ids = []
            if categories:
                category_ids = self._get_or_create_categories(categories)
            
            # Get or create tag IDs
            tag_ids = []
            if tags:
                tag_ids = self._get_or_create_tags(tags)
            
            # Prepare post data
            post_data = {
                "title": title,
                "content": content,
                "status": status,
                "categories": category_ids,
                "tags": tag_ids
            }
            
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
            
            if categories:
                category_ids = self._get_or_create_categories(categories)
                update_data["categories"] = category_ids
            
            if tags:
                tag_ids = self._get_or_create_tags(tags)
                update_data["tags"] = tag_ids
            
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
    
    def _get_or_create_categories(self, category_names: List[str]) -> List[int]:
        """Get existing category IDs or create new ones."""
        category_ids = []
        
        for name in category_names:
            try:
                # Search for existing category
                response = requests.get(
                    f"{self.api_base}/categories",
                    auth=self.auth,
                    params={'search': name},
                    timeout=30
                )
                response.raise_for_status()
                categories = response.json()
                
                if categories:
                    category_ids.append(categories[0]['id'])
                else:
                    # Create new category
                    create_response = requests.post(
                        f"{self.api_base}/categories",
                        auth=self.auth,
                        json={'name': name},
                        timeout=30
                    )
                    create_response.raise_for_status()
                    category_ids.append(create_response.json()['id'])
                
                self._rate_limit()
                
            except Exception as e:
                print(f"Error with category {name}: {e}")
        
        return category_ids
    
    def _get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        """Get existing tag IDs or create new ones."""
        tag_ids = []
        
        for name in tag_names:
            try:
                # Search for existing tag
                response = requests.get(
                    f"{self.api_base}/tags",
                    auth=self.auth,
                    params={'search': name},
                    timeout=30
                )
                response.raise_for_status()
                tags = response.json()
                
                if tags:
                    tag_ids.append(tags[0]['id'])
                else:
                    # Create new tag
                    create_response = requests.post(
                        f"{self.api_base}/tags",
                        auth=self.auth,
                        json={'name': name},
                        timeout=30
                    )
                    create_response.raise_for_status()
                    tag_ids.append(create_response.json()['id'])
                
                self._rate_limit()
                
            except Exception as e:
                print(f"Error with tag {name}: {e}")
        
        return tag_ids
    
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