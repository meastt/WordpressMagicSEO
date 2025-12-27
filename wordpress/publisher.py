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
    
    def _make_request_with_retry(self, method: str, url: str, max_retries: int = 3, **kwargs):
        """Make HTTP request with retry logic for transient errors."""
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()

                # Try to parse JSON - don't retry JSON errors as they're not transient
                try:
                    json_data = response.json()
                    return response, json_data
                except json.JSONDecodeError as e:
                    # JSON decode errors are not transient - fail immediately
                    raise Exception(f"Invalid JSON response from WordPress API: {e}. Response text: {response.text[:200]}")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise Exception(f"Request failed after {max_retries} attempts: {e}")

        raise Exception("Max retries exceeded")
    
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
                except (json.JSONDecodeError, KeyError, AttributeError) as json_err:
                    print(f"Failed to parse error response for category '{category_name}': {json_err}")
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
                except (json.JSONDecodeError, KeyError, AttributeError) as json_err:
                    print(f"Failed to parse error response for tag '{tag_name}': {json_err}")
            print(f"Error getting/creating tag '{tag_name}': {e}")
            return None
        except Exception as e:
            print(f"Error getting/creating tag '{tag_name}': {e}")
            return None
    
    def get_post(self, post_id: int) -> Dict:
        """
        Fetch a single post by ID from WordPress.
        
        Args:
            post_id: WordPress post ID
            
        Returns:
            Dict with post data
        """
        try:
            response = requests.get(
                f"{self.api_base}/posts/{post_id}",
                auth=self.auth,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error fetching post {post_id}: {e}")
    
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
        """Find a post by its URL. Returns None if not found."""
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
    
    def find_page_by_url(self, url: str) -> Optional[Dict]:
        """Find a WordPress page (not post) by its URL."""
        # Extract slug from URL
        slug = url.rstrip('/').split('/')[-1]
        
        try:
            response = requests.get(
                f"{self.api_base}/pages",
                auth=self.auth,
                params={'slug': slug},
                timeout=30
            )
            response.raise_for_status()
            pages = response.json()
            
            if pages:
                return pages[0]
            return None
            
        except Exception as e:
            print(f"Error finding page by URL {url}: {e}")
            return None
    
    def find_post_or_page_by_url(self, url: str) -> Optional[Dict]:
        """Find either a post or page by URL. Returns dict with 'type' field indicating 'post' or 'page'."""
        # Extract slug from URL
        slug = url.rstrip('/').split('/')[-1]
        
        # Try posts first (include all statuses to find scheduled/draft posts)
        try:
            response = requests.get(
                f"{self.api_base}/posts",
                auth=self.auth,
                params={'slug': slug, 'status': 'any'},
                timeout=30
            )
            response.raise_for_status()
            posts = response.json()
            
            if posts:
                result = posts[0].copy()
                result['_wp_type'] = 'post'
                print(f"  ✓ Found as POST: {url} (ID: {result.get('id')}, Status: {result.get('status')})")
                return result
        except Exception as e:
            pass
        
        # Try pages
        try:
            response = requests.get(
                f"{self.api_base}/pages",
                auth=self.auth,
                params={'slug': slug},
                timeout=30
            )
            response.raise_for_status()
            pages = response.json()
            
            if pages:
                result = pages[0].copy()
                result['_wp_type'] = 'page'
                print(f"  ✓ Found as PAGE: {url} (ID: {result.get('id')})")
                return result
        except Exception as e:
            pass
        
        print(f"  ⚠️  Not found in WordPress: {url}")
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
            
            response, result_data = self._make_request_with_retry(
                'POST',
                f"{self.api_base}/posts",
                auth=self.auth,
                json=post_data,
                timeout=30
            )
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
        tags: List[str] = None,
        featured_media: int = None,
        update_date: str = None,
        status: str = None,
        item_type: str = 'post'
    ) -> PublishResult:
        """
        Update an existing post or page.
        
        Args:
            post_id: WordPress post or page ID
            featured_media: ID of the uploaded media file to set as featured image
            update_date: ISO 8601 date string to update the post's published date
            status: WordPress status (e.g., 'publish', 'draft', 'private', 'future')
            item_type: 'post' or 'page' - determines which endpoint to use
        """
        
        try:
            # Build update data (only include fields that are provided)
            update_data = {}
            
            if title:
                update_data["title"] = title
            if content:
                update_data["content"] = content
            if featured_media:
                update_data["featured_media"] = featured_media
            if update_date:
                update_data["date"] = update_date
            if status:
                update_data["status"] = status
            
            # Handle categories (only for posts, not pages)
            if categories and item_type == 'post':
                category_ids = []
                for cat_name in categories:
                    cat_id = self._get_or_create_category(cat_name)
                    if cat_id:
                        category_ids.append(cat_id)
                if category_ids:
                    update_data["categories"] = category_ids
                    print(f"  ✓ Updated categories: {', '.join(categories)}")
            
            # Handle tags (only for posts, not pages)
            if tags and item_type == 'post':
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
            
            # Use the correct endpoint based on item type
            endpoint = f"{self.api_base}/pages/{post_id}" if item_type == 'page' else f"{self.api_base}/posts/{post_id}"
            
            response, result_data = self._make_request_with_retry(
                'POST',
                endpoint,
                auth=self.auth,
                json=update_data,
                timeout=30
            )
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
    
    def find_category_by_url(self, url: str) -> Optional[Dict]:
        """
        Find a category by its URL.

        Args:
            url: The category URL (e.g., https://site.com/category/bobcats/)

        Returns:
            Category dict or None if not found
        """
        # Extract slug from URL
        # Pattern: /category/slug/ or /category/slug
        import re
        match = re.search(r'/category/([^/]+)', url)
        if not match:
            return None

        slug = match.group(1)

        try:
            response, categories = self._make_request_with_retry(
                'GET',
                f"{self.api_base}/categories",
                auth=self.auth,
                params={'slug': slug},
                timeout=30
            )

            if categories:
                return categories[0]
            return None

        except Exception as e:
            print(f"Error finding category by URL {url}: {e}")
            return None

    def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        alt_text: str = "",
        title: str = "",
        caption: str = "",
        description: str = ""
    ) -> Optional[Dict]:
        """
        Upload an image to WordPress media library.
        
        Args:
            image_bytes: Image file bytes
            filename: Filename for the image
            alt_text: Alt text for accessibility and SEO (required)
            title: Image title for SEO (optional)
            caption: Image caption (optional)
            description: Image description for media library (optional)
            
        Returns:
            Dict with 'id', 'url', 'title' or None if upload fails
        """
        try:
            import base64
            
            # WordPress REST API requires multipart/form-data for media uploads
            # We need to use the /wp/v2/media endpoint with proper authentication
            
            # Prepare file data
            files = {
                'file': (filename, image_bytes, 'image/jpeg')
            }
            
            # Prepare post data
            data = {}
            if title:
                data['title'] = title
            if caption:
                data['caption'] = caption
            if alt_text:
                data['alt_text'] = alt_text
            
            response = requests.post(
                f"{self.api_base}/media",
                auth=self.auth,
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            media_id = result.get('id')
            
            # Update media metadata after upload to ensure alt_text is properly saved
            # WordPress REST API sometimes requires a separate update for alt_text
            if media_id and alt_text:
                try:
                    update_data = {
                        'alt_text': alt_text
                    }
                    if title:
                        update_data['title'] = title
                    if caption:
                        update_data['caption'] = caption
                    if description:
                        update_data['description'] = description
                    
                    update_response = requests.post(
                        f"{self.api_base}/media/{media_id}",
                        auth=self.auth,
                        json=update_data,
                        timeout=30
                    )
                    update_response.raise_for_status()
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not update image metadata: {e}")
                    # Continue anyway - alt text in img tag is still set
            
            return {
                'id': media_id,
                'url': result.get('source_url') or result.get('url'),
                'title': result.get('title', {}).get('rendered', title) if isinstance(result.get('title'), dict) else result.get('title', title)
            }
            
        except Exception as e:
            print(f"Error uploading image to WordPress: {e}")
            return None
    
    def find_tag_by_url(self, url: str) -> Optional[Dict]:
        """
        Find a tag by its URL.

        Args:
            url: The tag URL (e.g., https://site.com/tag/recipes/)

        Returns:
            Tag dict or None if not found
        """
        # Extract slug from URL
        import re
        match = re.search(r'/tag/([^/]+)', url)
        if not match:
            return None

        slug = match.group(1)

        try:
            response, tags = self._make_request_with_retry(
                'GET',
                f"{self.api_base}/tags",
                auth=self.auth,
                params={'slug': slug},
                timeout=30
            )

            if tags:
                return tags[0]
            return None

        except Exception as e:
            print(f"Error finding tag by URL {url}: {e}")
            return None

    def update_category_meta(
        self,
        category_id: int,
        meta_title: str = None,
        meta_description: str = None
    ) -> PublishResult:
        """
        Update ONLY the SEO meta for a category (cannot update content/description).

        Categories are taxonomy terms and don't have editable content like posts.
        We can only update their SEO metadata (title tag, meta description).

        Args:
            category_id: The category ID
            meta_title: SEO title tag (uses Yoast if available)
            meta_description: SEO meta description (uses Yoast if available)

        Returns:
            PublishResult
        """
        try:
            update_data = {"meta": {}}

            # Try to update Yoast SEO meta
            if meta_title:
                update_data["meta"]["_yoast_wpseo_title"] = meta_title
            if meta_description:
                update_data["meta"]["_yoast_wpseo_desc"] = meta_description

            response, result_data = self._make_request_with_retry(
                'POST',
                f"{self.api_base}/categories/{category_id}",
                auth=self.auth,
                json=update_data,
                timeout=30
            )
            self._rate_limit()

            return PublishResult(
                success=True,
                action="update_category_meta",
                url=result_data.get('link', ''),
                post_id=category_id
            )

        except Exception as e:
            return PublishResult(
                success=False,
                action="update_category_meta",
                url="",
                post_id=category_id,
                error=str(e)
            )

    def update_tag_meta(
        self,
        tag_id: int,
        meta_title: str = None,
        meta_description: str = None
    ) -> PublishResult:
        """
        Update ONLY the SEO meta for a tag (cannot update content/description).

        Tags are taxonomy terms and don't have editable content like posts.
        We can only update their SEO metadata (title tag, meta description).

        Args:
            tag_id: The tag ID
            meta_title: SEO title tag (uses Yoast if available)
            meta_description: SEO meta description (uses Yoast if available)

        Returns:
            PublishResult
        """
        try:
            update_data = {"meta": {}}

            # Try to update Yoast SEO meta
            if meta_title:
                update_data["meta"]["_yoast_wpseo_title"] = meta_title
            if meta_description:
                update_data["meta"]["_yoast_wpseo_desc"] = meta_description

            response, result_data = self._make_request_with_retry(
                'POST',
                f"{self.api_base}/tags/{tag_id}",
                auth=self.auth,
                json=update_data,
                timeout=30
            )
            self._rate_limit()

            return PublishResult(
                success=True,
                action="update_tag_meta",
                url=result_data.get('link', ''),
                post_id=tag_id
            )

        except Exception as e:
            return PublishResult(
                success=False,
                action="update_tag_meta",
                url="",
                post_id=tag_id,
                error=str(e)
            )

    def create_301_redirect(
        self,
        source_url: str,
        target_url: str
    ) -> PublishResult:
        """Create a 301 redirect (requires Redirection plugin)."""
        
        try:
            from urllib.parse import urlparse
            
            # Validate target URL exists and is not empty
            if not target_url or target_url.strip() == '':
                return PublishResult(
                    success=False,
                    action="redirect",
                    url=source_url,
                    error="Target URL is empty"
                )
            
            # Normalize URLs: ensure they have proper format
            # If target_url doesn't start with http, it might be relative - make it absolute
            if not target_url.startswith('http'):
                # It's a relative path, prepend site URL
                target_url = f"{self.site_url.rstrip('/')}/{target_url.lstrip('/')}"
            
            # Extract paths from URLs more robustly
            # Parse URLs to extract paths
            source_parsed = urlparse(source_url)
            target_parsed = urlparse(target_url)
            
            # Get paths - ensure they start with /
            source_path = source_parsed.path
            if not source_path.startswith('/'):
                source_path = '/' + source_path
            
            target_path = target_parsed.path
            if not target_path.startswith('/'):
                target_path = '/' + target_path
            
            # Normalize paths (remove trailing slashes except root)
            source_path = source_path.rstrip('/') or '/'
            target_path = target_path.rstrip('/') or '/'
            
            # Validate target path is not empty or root (unless that's intentional)
            if not target_path or target_path == '/':
                return PublishResult(
                    success=False,
                    action="redirect",
                    url=source_url,
                    error=f"Invalid target URL: {target_url} (extracted path is empty or root)"
                )
            
            print(f"Creating redirect: {source_path} -> {target_path}")
            print(f"  Source URL: {source_url}")
            print(f"  Target URL: {target_url}")
            
            # Optional: Verify target page exists (warn but don't fail)
            try:
                # Try to find the target page/post to warn if it doesn't exist
                # This uses the target_path, so we need to extract the slug
                target_slug = target_path.strip('/').split('/')[-1]
                if target_slug:
                    target_post = self.find_post_by_url(target_url)
                    if not target_post:
                        print(f"  ⚠️  WARNING: Target URL '{target_url}' does not appear to exist on the site!")
                        print(f"     The redirect will still be created, but users will be redirected to a 404 page.")
            except Exception as e:
                # Don't fail on verification - just log it
                print(f"  ⚠️  Could not verify target URL exists: {e}")
            
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
            
            # Check for HTTP errors
            if response.status_code not in [200, 201]:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get('message', error_text)
                except:
                    pass
                return PublishResult(
                    success=False,
                    action="redirect",
                    url=source_url,
                    error=f"WordPress API error ({response.status_code}): {error_text}"
                )
            
            response.raise_for_status()
            self._rate_limit()
            
            result_data = response.json() if response.content else {}
            
            return PublishResult(
                success=True,
                action="redirect",
                url=f"{source_path} -> {target_path}"
            )
            
        except requests.exceptions.RequestException as e:
            return PublishResult(
                success=False,
                action="redirect",
                url=source_url,
                error=f"Request failed: {str(e)}"
            )
        except Exception as e:
            return PublishResult(
                success=False,
                action="redirect",
                url=source_url,
                error=f"Error creating redirect: {str(e)}"
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
                response, posts = self._make_request_with_retry(
                    'GET',
                    f"{self.api_base}/posts",
                    auth=self.auth,
                    params={'search': keyword, 'per_page': limit},
                    timeout=30
                )
                
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