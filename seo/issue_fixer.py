"""
SEO Issue Fixer
===============
Automatically fixes SEO issues found in audits by updating WordPress posts/pages.
Uses AI to generate SEO-optimized titles and meta descriptions when needed.
"""

import requests
import time
import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup

from wordpress.publisher import WordPressPublisher
from seo.fix_tracker import SEOFixTracker


class SEOIssueFixer:
    """Fixes SEO issues by updating WordPress content."""
    
    def __init__(
        self,
        site_url: str,
        wp_username: str,
        wp_app_password: str,
        rate_limit_delay: float = 1.0,
        use_ai: bool = True
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
        self.use_ai = use_ai
        self.fix_tracker = SEOFixTracker(site_url=site_url)
        
        # Initialize AI generator if available
        self.ai_generator = None
        if use_ai:
            try:
                from content.generators.claude_generator import ClaudeContentGenerator
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.ai_generator = ClaudeContentGenerator(api_key=api_key)
            except Exception as e:
                print(f"Warning: Could not initialize AI generator: {e}")
                self.ai_generator = None
    
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
                
                # Check if already fixed
                if self.fix_tracker.is_fixed(url, issue_type, category):
                    results["fixed_count"] += 1
                    results["fixed_urls"].append(url)
                    results["errors"].append(f"{url} was already fixed (skipped)")
                    continue
                
                # Fix the specific issue
                fix_method = f"_fix_{issue_type}"
                if hasattr(self, fix_method):
                    fix_result = getattr(self, fix_method)(post_id, post_type, url)
                    if fix_result:
                        results["fixed_count"] += 1
                        results["fixed_urls"].append(url)
                        # Record successful fix
                        self.fix_tracker.record_fix(url, issue_type, category, success=True)
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"Failed to fix {issue_type} for {url}")
                        # Record failed fix attempt
                        self.fix_tracker.record_fix(url, issue_type, category, success=False)
                else:
                    # Generic fix attempt
                    fix_result = self._fix_generic(post_id, post_type, url, issue_type, category)
                    if fix_result:
                        results["fixed_count"] += 1
                        results["fixed_urls"].append(url)
                        self.fix_tracker.record_fix(url, issue_type, category, success=True)
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"No fix handler for {issue_type}")
                        self.fix_tracker.record_fix(url, issue_type, category, success=False)
                
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
        """Add meta title if missing. Uses AI to generate SEO-optimized title if available."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            title = post_data.get('title', {}).get('rendered', '')
            content = post_data.get('content', {}).get('rendered', '')
            
            if not title:
                return False
            
            # Try AI generation first if available
            if self.ai_generator:
                try:
                    # Extract keywords from title/content
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()[:500]  # First 500 chars for context
                    
                    # Generate SEO-optimized meta title
                    prompt = f"""Generate an SEO-optimized meta title (50-60 characters) for this WordPress post.

Post Title: {title}
Content Preview: {text_content}

Requirements:
- 50-60 characters (optimal for search results)
- Include main keyword from the title
- Compelling and click-worthy
- Different from the post title (optimized for SERP)

Return ONLY the meta title, nothing else."""
                    
                    response = self.ai_generator.client.messages.create(
                        model=self.ai_generator.model,
                        max_tokens=100,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    ai_title = response.content[0].text.strip()
                    # Clean up and validate length
                    ai_title = ai_title.replace('"', '').replace("'", '').strip()
                    if 50 <= len(ai_title) <= 60:
                        meta_title = ai_title
                    else:
                        # Fallback to truncation if AI result is wrong length
                        meta_title = title[:60] if len(title) > 60 else title
                except Exception as e:
                    print(f"AI title generation failed, using fallback: {e}")
                    # Fallback to simple truncation
                    meta_title = title[:60] if len(title) > 60 else title
            else:
                # No AI - use simple truncation
                meta_title = title[:60] if len(title) > 60 else title
            
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
        """Add meta description if missing. Uses AI to generate SEO-optimized description if available."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content = post_data.get('content', {}).get('rendered', '')
            title = post_data.get('title', {}).get('rendered', '')
            
            # Try AI generation first if available
            if self.ai_generator:
                try:
                    # Extract meaningful content
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text().strip()[:1000]  # More context for AI
                    
                    # Generate SEO-optimized meta description
                    prompt = f"""Generate an SEO-optimized meta description (150-155 characters) for this WordPress post.

Post Title: {title}
Content: {text_content}

Requirements:
- 150-155 characters (optimal for search results)
- Compelling and click-worthy
- Includes main keyword naturally
- Summarizes the value/benefit to the reader
- Ends with a call to action or benefit statement

Return ONLY the meta description, nothing else."""
                    
                    response = self.ai_generator.client.messages.create(
                        model=self.ai_generator.model,
                        max_tokens=200,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    ai_desc = response.content[0].text.strip()
                    # Clean up
                    ai_desc = ai_desc.replace('"', '').replace("'", '').strip()
                    
                    # Validate length
                    if 120 <= len(ai_desc) <= 160:
                        meta_desc = ai_desc
                    else:
                        # Adjust if slightly off
                        if len(ai_desc) > 160:
                            meta_desc = ai_desc[:157] + '...'
                        else:
                            # Too short - use fallback
                            text_preview = soup.get_text().strip()[:160]
                            meta_desc = text_preview[:157] + '...' if len(text_preview) > 157 else text_preview
                except Exception as e:
                    print(f"AI description generation failed, using fallback: {e}")
                    # Fallback to content extraction
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text().strip()[:160]
                    if text_content:
                        meta_desc = text_content[:157] + '...' if len(text_content) > 157 else text_content
                    else:
                        meta_desc = f"Learn about {title}"
            else:
                # No AI - use content extraction
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text().strip()[:160]
                if text_content:
                    meta_desc = text_content[:157] + '...' if len(text_content) > 157 else text_content
                else:
                    meta_desc = f"Learn about {title}"
            
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

