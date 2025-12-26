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

try:
    from PIL import Image
    from io import BytesIO
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


class SEOIssueFixer:
    """Fixes SEO issues by updating WordPress content."""
    
    def __init__(
        self,
        site_url: str,
        wp_username: str,
        wp_app_password: str,
        rate_limit_delay: float = 1.0,
        use_ai: bool = True,
        safe_mode: bool = False
    ):
        self.site_url = site_url.rstrip("/")
        self.safe_mode = safe_mode
        self.rate_limit_delay = 5.0 if safe_mode else rate_limit_delay
        
        self.wp_publisher = WordPressPublisher(
            site_url=site_url,
            username=wp_username,
            application_password=wp_app_password,
            rate_limit_delay=self.rate_limit_delay
        )
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (wp_username, wp_app_password)
        self.use_ai = use_ai
        self.fix_tracker = SEOFixTracker(site_url=site_url)
        
        # Error logging
        self.error_log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            f"fix_errors_{urlparse(site_url).netloc.replace('.', '_')}.json"
        )

        self.backup_dir = os.path.join(os.getcwd(), 'backups', urlparse(site_url).netloc.replace('.', '_'))
        if not os.path.exists(self.backup_dir):
            try: os.makedirs(self.backup_dir, exist_ok=True)
            except: pass
        
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
                self.ai_generator = ClaudeContentGenerator(api_key="none") if use_ai else None

    def _request(self, method: str, endpoint: str, max_retries: int = 3, **kwargs) -> Optional[requests.Response]:
        """
        WordPress API request with built-in retry logic and exponential backoff.
        Handles 429 (Rate Limit) and 5xx (Server Error) gracefully.
        """
        retry_delay = 2.0
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.request(method, endpoint, auth=self.auth, **kwargs)
                
                # Success
                if response.ok:
                    return response
                
                # Rate limited - wait longer and retry
                if response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️ Rate limited (429) for {endpoint}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Server error - retry
                if response.status_code >= 500:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️ Server error ({response.status_code}) for {endpoint}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Client error (4xx) - don't retry unless it's 429
                print(f"❌ API Error ({response.status_code}): {response.text}")
                return response

            except Exception as e:
                last_error = str(e)
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️ Request failed for {endpoint}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            
            finally:
                # Apply consistent rate limiting after every attempt (or failure)
                time.sleep(self.rate_limit_delay)
        
        print(f"❌ Failed to {method} {endpoint} after {max_retries} attempts. Last error: {last_error}")
        return None

    def _save_error_log(self, url: str, issue_type: str, error: str):
        """Append error to local log for debugging."""
        try:
            log_data = []
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, 'r') as f:
                    log_data = json.load(f)
            
            log_data.append({
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "issue_type": issue_type,
                "error": str(error)
            })
            
            # Keep last 100 errors
            log_data = log_data[-100:]
            
            with open(self.error_log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except:
            pass

    def _save_backup(self, post_id: int, content: str, issue_type: str):
        """Save a backup of post content before modification."""
        try:
            filename = f"post_{post_id}_{issue_type}_{int(time.time())}.html"
            filepath = os.path.join(self.backup_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            # Maintain only last 10 backups per post/issue combo to save space
            # (Simple implementation: just log it for now)
            print(f"  💾 Backup saved to {filename}")
        except Exception as e:
            print(f"  ⚠️ Backup failed: {e}")
    
    def fix_issue(self, issue_type: str, category: str, urls: List[str]) -> Dict:
        """
        Fix a specific issue type across multiple URLs.
        
        Args:
            issue_type: Type of issue (e.g., 'h1_presence', 'title_presence')
            category: Issue category (e.g., 'onpage', 'technical')
            urls: List of URLs to fix
            
        Returns:
            Dict with categorized results:
            - fixed: Successfully fixed URLs
            - skipped: Already fixed (no action needed)
            - not_applicable: URLs where fix doesn't apply (e.g., category pages)
            - errors: Actual failures that need attention
        """
        results = {
            "success": True,
            "fixed_count": 0,
            "skipped_count": 0,
            "not_applicable_count": 0,
            "error_count": 0,
            # Detailed lists
            "fixed": [],
            "skipped": [],
            "not_applicable": [],
            "errors": [],
            # Legacy compatibility
            "failed_count": 0,
            "fixed_urls": [],
            # User-friendly summary
            "summary": ""
        }
        
        for url in urls:
            try:
                # Get post/page ID from URL
                post_id, post_type = self._get_post_id_from_url(url)
                
                if not post_id:
                    # Determine WHY we couldn't find the post
                    reason = self._categorize_missing_post(url)
                    
                    if reason == "category_page":
                        results["not_applicable_count"] += 1
                        results["not_applicable"].append({
                            "url": url,
                            "reason": "Category/archive page (no editable content)",
                            "icon": "📁"
                        })
                    elif reason == "home_page":
                        results["not_applicable_count"] += 1
                        results["not_applicable"].append({
                            "url": url,
                            "reason": "Home page (edit in theme settings)",
                            "icon": "🏠"
                        })
                    elif reason == "tag_page":
                        results["not_applicable_count"] += 1
                        results["not_applicable"].append({
                            "url": url,
                            "reason": "Tag archive page (no editable content)",
                            "icon": "🏷️"
                        })
                    else:
                        results["error_count"] += 1
                        results["errors"].append({
                            "url": url,
                            "reason": "Could not find this page in WordPress",
                            "icon": "❓"
                        })
                    continue
                
                # Check if already fixed
                if self.fix_tracker.is_fixed(url, issue_type, category):
                    results["skipped_count"] += 1
                    results["skipped"].append({
                        "url": url,
                        "reason": "Already fixed previously",
                        "icon": "✓"
                    })
                    results["fixed_count"] += 1  # Count as success for summary
                    results["fixed_urls"].append(url)
                    continue
                
                # Fix the specific issue
                fix_method = f"_fix_{issue_type}"
                if hasattr(self, fix_method):
                    fix_result = getattr(self, fix_method)(post_id, post_type, url)
                    if fix_result:
                        results["fixed_count"] += 1
                        results["fixed"].append({
                            "url": url,
                            "reason": "Successfully fixed",
                            "icon": "✅"
                        })
                        results["fixed_urls"].append(url)
                        self.fix_tracker.record_fix(url, issue_type, category, success=True)
                    else:
                        results["error_count"] += 1
                        results["errors"].append({
                            "url": url,
                            "reason": f"Fix attempted but failed",
                            "icon": "❌"
                        })
                        self.fix_tracker.record_fix(url, issue_type, category, success=False)
                else:
                    # No handler for this issue type
                    results["error_count"] += 1
                    results["errors"].append({
                        "url": url,
                        "reason": f"No fix handler for {issue_type}",
                        "icon": "🔧"
                    })
                
                time.sleep(self.wp_publisher.rate_limit_delay)
                
            except Exception as e:
                results["error_count"] += 1
                results["errors"].append({
                    "url": url,
                    "reason": str(e),
                    "icon": "💥"
                })
        
        # Legacy compatibility
        results["failed_count"] = results["error_count"]
        
        # Generate user-friendly summary
        results["summary"] = self._generate_fix_summary(results, issue_type)
        results["success"] = results["error_count"] == 0
        
        return results
    
    def _categorize_missing_post(self, url: str) -> str:
        """Determine why a URL doesn't have a post ID."""
        url_lower = url.lower()
        
        # Check for common non-post URL patterns
        if '/category/' in url_lower:
            return "category_page"
        elif '/tag/' in url_lower:
            return "tag_page"
        elif url.rstrip('/').count('/') <= 3 and url.rstrip('/').endswith(('.com', '.net', '.org')):
            return "home_page"
        elif '/author/' in url_lower:
            return "author_page"
        elif '/page/' in url_lower:
            return "pagination"
        elif url.rstrip('/') == self.site_url.rstrip('/'):
            return "home_page"
        else:
            return "unknown"
    
    def _generate_fix_summary(self, results: Dict, issue_type: str) -> str:
        """Generate a user-friendly summary message."""
        fixed = results["fixed_count"]
        skipped = results["skipped_count"]
        na = results["not_applicable_count"]
        errors = results["error_count"]
        total = fixed + skipped + na + errors
        
        parts = []
        
        if fixed > 0:
            parts.append(f"✅ {fixed} fixed")
        if skipped > 0:
            parts.append(f"⏭️ {skipped} already done")
        if na > 0:
            parts.append(f"📁 {na} not applicable (category/archive pages)")
        if errors > 0:
            parts.append(f"❌ {errors} need attention")
        
        if not parts:
            return "No URLs to process"
        
        summary = " | ".join(parts)
        
        # Add reassurance if there are "not applicable" items
        if na > 0 and errors == 0:
            summary += "\n\n💡 Category and archive pages can't be edited directly — this is normal!"
        
        return summary
    
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
            response = self._request('GET', f"{self.api_base}/posts", params={'slug': slug, 'per_page': 1}, timeout=30)
            if response and response.ok:
                posts = response.json()
                if posts:
                    return posts[0]['id'], 'post'
            
            # Try pages endpoint
            response = self._request('GET', f"{self.api_base}/pages", params={'slug': slug, 'per_page': 1}, timeout=30)
            if response and response.ok:
                pages = response.json()
                if pages:
                    return pages[0]['id'], 'page'
            
            # Try searching by link
            response = self._request('GET', f"{self.api_base}/posts", params={'search': slug, 'per_page': 10}, timeout=30)
            if response and response.ok:
                posts = response.json()
                for post in posts:
                    if post.get('link', '').rstrip('/') == url.rstrip('/'):
                        return post['id'], 'post'
            
            return None, None
            
        except Exception as e:
            print(f"Error getting post ID for {url}: {e}")
            return None, None
    
    def _get_post_content(self, post_id: int, post_type: str = 'post', backup_before_fix: bool = False, issue_type: str = "") -> Dict:
        """Get current post content from WordPress with retry logic."""
        endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
        response = self._request('GET', endpoint, params={'context': 'edit'}, timeout=30)
        
        if response and response.ok:
            data = response.json()
            if backup_before_fix and issue_type:
                content = data.get('content', {}).get('raw', data.get('content', {}).get('rendered', ''))
                self._save_backup(post_id, content, issue_type)
            return data
        return {}
    
    def _fix_h1_presence(self, post_id: int, post_type: str, url: str) -> bool:
        """Add H1 tag if missing."""
        try:
            # Pass backup_before_fix=True to ensure we have a rollback point
            post_data = self._get_post_content(post_id, post_type, backup_before_fix=True, issue_type="h1_presence")
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
            response = self._request('POST', endpoint, json={'content': new_content}, timeout=30)
            
            if response and response.ok:
                return True
            return False
            
        except Exception as e:
            print(f"Error fixing H1 for {url}: {e}")
            return False
    
    def _fix_title_presence(self, post_id: int, post_type: str, url: str) -> bool:
        """Add meta title if missing. Uses AI to generate SEO-optimized title if available."""
        try:
            post_data = self._get_post_content(post_id, post_type, backup_before_fix=True, issue_type="title_presence")
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
            post_data = self._get_post_content(post_id, post_type, backup_before_fix=True, issue_type="meta_description_presence")
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
    
    def _fix_title_length(self, post_id: int, post_type: str, url: str) -> bool:
        """Fix title that is too long or too short (target: 50-60 chars)."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            content = post_data.get('content', {}).get('rendered', '')
            
            if not title:
                return False
            
            current_len = len(title)
            
            # Already optimal
            if 50 <= current_len <= 60:
                return True
            
            # Use AI to rewrite if available
            if self.ai_generator:
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    text_content = soup.get_text()[:500]
                    
                    if current_len > 60:
                        instruction = "Shorten this title to 50-60 characters while keeping the main keyword and meaning."
                    else:
                        instruction = "Expand this title to 50-60 characters by adding relevant context or power words."
                    
                    prompt = f"""{instruction}

Current Title ({current_len} chars): {title}
Content Context: {text_content[:300]}

Requirements:
- MUST be exactly 50-60 characters
- Keep the primary keyword
- Make it compelling for search results

Return ONLY the new title, nothing else."""
                    
                    response = self.ai_generator.client.messages.create(
                        model=self.ai_generator.model,
                        max_tokens=100,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    new_title = response.content[0].text.strip().replace('"', '').replace("'", '')
                    
                    # Validate length
                    if 45 <= len(new_title) <= 65:  # Allow slight variance
                        result = self.wp_publisher.update_post(
                            post_id=post_id,
                            meta_title=new_title,
                            item_type=post_type
                        )
                        return result.success
                except Exception as e:
                    print(f"AI title rewrite failed: {e}")
            
            # Fallback: simple truncation or padding
            if current_len > 60:
                new_title = title[:57] + "..."
            else:
                new_title = title  # Can't easily expand without AI
            
            result = self.wp_publisher.update_post(
                post_id=post_id,
                meta_title=new_title,
                item_type=post_type
            )
            return result.success
            
        except Exception as e:
            print(f"Error fixing title length for {url}: {e}")
            return False
    
    def _fix_meta_description_length(self, post_id: int, post_type: str, url: str) -> bool:
        """Fix meta description that is too long or too short (target: 120-160 chars)."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            title = post_data.get('title', {}).get('rendered', '')
            content = post_data.get('content', {}).get('rendered', '')
            
            # Get current meta description (would need to check Yoast/RankMath meta)
            # For now, generate a new one
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text().strip()[:1000]
            
            if self.ai_generator:
                try:
                    prompt = f"""Write an SEO meta description (exactly 140-155 characters) for this page.

Title: {title}
Content: {text_content}

Requirements:
- MUST be 140-155 characters (count carefully!)
- Include the main keyword naturally
- Compelling and click-worthy
- End with a benefit or call to action

Return ONLY the meta description, nothing else."""
                    
                    response = self.ai_generator.client.messages.create(
                        model=self.ai_generator.model,
                        max_tokens=200,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    new_desc = response.content[0].text.strip().replace('"', '').replace("'", '')
                    
                    # Enforce length limits
                    if len(new_desc) > 160:
                        new_desc = new_desc[:157] + "..."
                    
                    result = self.wp_publisher.update_post(
                        post_id=post_id,
                        meta_description=new_desc,
                        item_type=post_type
                    )
                    return result.success
                except Exception as e:
                    print(f"AI description rewrite failed: {e}")
            
            # Fallback: extract from content
            if text_content:
                new_desc = text_content[:157] + "..." if len(text_content) > 157 else text_content
                result = self.wp_publisher.update_post(
                    post_id=post_id,
                    meta_description=new_desc,
                    item_type=post_type
                )
                return result.success
            
            return False
            
        except Exception as e:
            print(f"Error fixing meta description length for {url}: {e}")
            return False
    
    def _fix_multiple_h1s(self, post_id: int, post_type: str, url: str) -> bool:
        """Fix multiple H1 tags by demoting extras to H2."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            h1s = soup.find_all('h1')
            
            if len(h1s) <= 1:
                return True  # Already OK
            
            # Keep the first H1, demote the rest to H2
            for h1 in h1s[1:]:
                h1.name = 'h2'
            
            new_content = str(soup)
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing multiple H1s for {url}: {e}")
            return False
    
    def _fix_heading_hierarchy(self, post_id: int, post_type: str, url: str) -> bool:
        """Fix skipped heading levels (e.g., H1 -> H3 should be H1 -> H2 -> H3)."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            if not headings:
                return True  # No headings to fix
            
            # Track expected level and fix skips
            modified = False
            expected_level = 1
            
            for heading in headings:
                current_level = int(heading.name[1])
                
                # If we skip a level (e.g., H1 to H3), demote to expected
                if current_level > expected_level + 1:
                    new_level = expected_level + 1
                    heading.name = f'h{new_level}'
                    modified = True
                    expected_level = new_level
                else:
                    expected_level = current_level
            
            if not modified:
                return True  # Nothing to fix
            
            new_content = str(soup)
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing heading hierarchy for {url}: {e}")
            return False
    
    def _fix_image_alt_text(self, post_id: int, post_type: str, url: str) -> bool:
        """Add alt text to images that are missing it."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            images = soup.find_all('img')
            
            modified = False
            for img in images:
                alt = img.get('alt', '').strip()
                if not alt:
                    # Generate alt text from context
                    src = img.get('src', '')
                    filename = src.split('/')[-1].split('.')[0] if src else ''
                    
                    if self.ai_generator:
                        try:
                            # Get surrounding text for context
                            parent = img.parent
                            context = parent.get_text()[:200] if parent else ''
                            
                            prompt = f"""Generate a brief, descriptive alt text for an image.

Page Title: {title}
Image Filename: {filename}
Surrounding Text: {context}

Requirements:
- 5-15 words
- Descriptive and specific
- Include relevant keyword if natural
- Don't start with "Image of" or "Picture of"

Return ONLY the alt text, nothing else."""
                            
                            response = self.ai_generator.client.messages.create(
                                model=self.ai_generator.model,
                                max_tokens=50,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            
                            new_alt = response.content[0].text.strip().replace('"', '')
                            img['alt'] = new_alt
                            modified = True
                        except:
                            # Fallback to filename-based alt
                            img['alt'] = filename.replace('-', ' ').replace('_', ' ').title()
                            modified = True
                    else:
                        # No AI - use filename
                        img['alt'] = filename.replace('-', ' ').replace('_', ' ').title()
                        modified = True
            
            if not modified:
                return True  # Nothing to fix
            
            new_content = str(soup)
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing image alt text for {url}: {e}")
            return False

    def _fix_image_dimensions(self, post_id: int, post_type: str, url: str) -> bool:
        """Add missing width/height attributes to images to prevent layout shift."""
        if not HAS_PILLOW:
            print("⚠️ Pillow not installed, skipping image dimension fix.")
            return False
            
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            images = soup.find_all('img')
            
            modified = False
            for img in images:
                if not img.get('width') or not img.get('height'):
                    src = img.get('src')
                    if not src:
                        continue
                        
                    # Handle relative URLs
                    if src.startswith('/'):
                        from urllib.parse import urljoin
                        src = urljoin(self.site_url, src)
                    
                    try:
                        # Fetch just enough to get headers/metadata if possible, but simplest is full fetch for now
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        response = requests.get(src, timeout=10, headers=headers)
                        if response.ok:
                            img_obj = Image.open(BytesIO(response.content))
                            width, height = img_obj.size
                            img['width'] = str(width)
                            img['height'] = str(height)
                            modified = True
                            print(f"  ✓ Added dimensions {width}x{height} to {src}")
                    except Exception as img_err:
                        print(f"  ⚠️ Could not get dimensions for {src}: {img_err}")
            
            if not modified:
                return True
            
            new_content = str(soup)
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            
            response = self._request('POST', endpoint, json={'content': new_content}, timeout=30)
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing image dimensions for {url}: {e}")
            return False
    
    def _fix_anchor_text(self, post_id: int, post_type: str, url: str) -> bool:
        """Replace generic anchor text like 'click here' with descriptive text."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            links = soup.find_all('a', href=True)
            
            generic_anchors = ['click here', 'read more', 'here', 'link', 'more', 'this', 'learn more']
            modified = False
            
            for link in links:
                anchor_text = link.get_text().strip().lower()
                
                if anchor_text in generic_anchors:
                    href = link.get('href', '')
                    
                    if self.ai_generator:
                        try:
                            # Get surrounding context
                            parent = link.parent
                            context = parent.get_text()[:200] if parent else ''
                            
                            prompt = f"""Replace the generic anchor text with a descriptive, keyword-rich alternative.

Current Anchor: "{anchor_text}"
Link URL: {href}
Surrounding Context: {context}

Requirements:
- 2-6 words
- Descriptive of what the link leads to
- Natural in the sentence context
- Include relevant keyword if possible

Return ONLY the new anchor text, nothing else."""
                            
                            response = self.ai_generator.client.messages.create(
                                model=self.ai_generator.model,
                                max_tokens=30,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            
                            new_anchor = response.content[0].text.strip().replace('"', '')
                            if new_anchor and len(new_anchor) < 50:
                                link.string = new_anchor
                                modified = True
                        except:
                            pass  # Keep original if AI fails
                    else:
                        # Fallback: extract from URL
                        slug = href.rstrip('/').split('/')[-1] if href else ''
                        if slug and slug != anchor_text:
                            new_anchor = slug.replace('-', ' ').replace('_', ' ').title()
                            link.string = new_anchor
                            modified = True
            
            if not modified:
                return True  # Nothing to fix
            
            new_content = str(soup)
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing anchor text for {url}: {e}")
            return False
    
    def _fix_internal_links(self, post_id: int, post_type: str, url: str) -> bool:
        """
        Add strategic internal links using SmartLinkingEngine.

        Enhanced workflow:
        1. Use AI to suggest contextual link placements
        2. Auto-insert links mid-content (not just footer)
        3. Add "Related Articles" section as backup
        4. Ensure bidirectional linking where appropriate
        """
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False

            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')

            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')

            # Get all posts to find related ones
            try:
                response = self._request(
                    'GET',
                    f"{self.api_base}/posts",
                    params={'per_page': 100, 'status': 'publish'},
                    timeout=30
                )
                all_posts = response.json() if response and response.ok else []
            except:
                all_posts = []

            if not all_posts:
                print(f"   No posts found for internal linking")
                return False

            # Prepare available pages for SmartLinkingEngine
            available_pages = []
            for post in all_posts:
                post_url = post.get('link', '')
                if post_url.rstrip('/') == url.rstrip('/'):
                    continue  # Skip self

                post_title = post.get('title', {}).get('rendered', '')
                post_excerpt = post.get('excerpt', {}).get('rendered', '')

                # Extract plain text from excerpt
                soup_excerpt = BeautifulSoup(post_excerpt, 'html.parser')
                summary = soup_excerpt.get_text()[:200]

                available_pages.append({
                    'url': post_url,
                    'title': post_title,
                    'keywords': post_title.lower().split()[:5],  # Simple keyword extraction
                    'summary': summary
                })

            if not available_pages:
                print(f"   No available pages for linking")
                return False

            # Use SmartLinkingEngine for contextual link suggestions
            link_suggestions = []
            if self.ai_generator and hasattr(self, '_smart_linking_engine'):
                try:
                    print(f"   Using AI for contextual link suggestions...")
                    link_suggestions = self._smart_linking_engine.suggest_contextual_links(
                        current_content=content_raw,
                        available_pages=available_pages,
                        max_links=5
                    )
                    print(f"   AI suggested {len(link_suggestions)} contextual links")
                except Exception as e:
                    print(f"   AI linking failed: {e}, falling back to basic linking")

            modified_content = content_raw

            # If AI suggestions available, insert contextual links
            if link_suggestions:
                try:
                    # Initialize SmartLinkingEngine if not already done
                    if not hasattr(self, '_smart_linking_engine'):
                        api_key = os.getenv("ANTHROPIC_API_KEY")
                        if api_key:
                            from seo.linking_engine import SmartLinkingEngine
                            self._smart_linking_engine = SmartLinkingEngine(api_key=api_key)
                            # Retry with new engine
                            link_suggestions = self._smart_linking_engine.suggest_contextual_links(
                                current_content=content_raw,
                                available_pages=available_pages,
                                max_links=5
                            )

                    if link_suggestions and hasattr(self, '_smart_linking_engine'):
                        modified_content = self._smart_linking_engine.auto_insert_links(
                            content_html=content_raw,
                            link_suggestions=link_suggestions
                        )
                        print(f"   ✓ Inserted {len(link_suggestions)} contextual links")
                except Exception as e:
                    print(f"   Could not insert AI links: {e}")

            # Also add a "Related Articles" section as backup
            # Find related posts using keyword matching
            soup = BeautifulSoup(content_raw, 'html.parser')
            current_text = soup.get_text().lower()

            related_posts = []
            for post in all_posts[:50]:  # Check first 50
                post_url = post.get('link', '')
                if post_url.rstrip('/') == url.rstrip('/'):
                    continue  # Skip self

                post_title = post.get('title', {}).get('rendered', '')
                # Check if post title words appear in content
                title_words = [w for w in post_title.lower().split() if len(w) > 4]
                if any(word in current_text for word in title_words):
                    related_posts.append({
                        'url': post_url,
                        'title': post_title
                    })

            # Add related articles section if we have any
            if related_posts:
                related_html = '\n\n<h2>Related Articles</h2>\n<ul>\n'
                for rp in related_posts[:5]:
                    related_html += f'<li><a href="{rp["url"]}">{rp["title"]}</a></li>\n'
                related_html += '</ul>'
                modified_content += related_html
                print(f"   ✓ Added {len(related_posts[:5])} related article links")

            # Check if content was actually modified
            if modified_content == content_raw:
                print(f"   No links added")
                return False

            # Save updated content
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': modified_content},
                timeout=30
            )

            return response and response.ok

        except Exception as e:
            print(f"Error fixing internal links for {url}: {e}")
            return False
    
    def _fix_external_links(self, post_id: int, post_type: str, url: str) -> bool:
        """Add relevant external authority links (target: 2-3 minimum)."""
        try:
            if not self.ai_generator:
                return False  # Need AI to find relevant links
            
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            text_preview = soup.get_text()[:1000]
            
            # Use AI to suggest relevant authority links
            try:
                prompt = f"""Suggest 3 authoritative external links to add to this article.

Title: {title}
Content: {text_preview}

For each suggestion, provide:
1. A descriptive anchor text (2-5 words)
2. The type of authority site (Wikipedia, gov site, major publication, etc.)

Format each as: anchor_text | site_type

Example:
photography exposure basics | Wikipedia
camera sensor technology | DPreview

Return exactly 3 suggestions, one per line."""
                
                response = self.ai_generator.client.messages.create(
                    model=self.ai_generator.model,
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                suggestions = response.content[0].text.strip().split('\n')
                
                # Add a note about external resources (AI can't actually fetch URLs)
                resources_html = '\n\n<h2>Additional Resources</h2>\n<p>For more information on this topic, consider exploring:</p>\n<ul>\n'
                for suggestion in suggestions[:3]:
                    if '|' in suggestion:
                        anchor, site_type = suggestion.split('|', 1)
                        anchor = anchor.strip()
                        resources_html += f'<li><strong>{anchor}</strong> - search for this on {site_type.strip()}</li>\n'
                resources_html += '</ul>'
                
                new_content = content_raw + resources_html
                
                endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
                response = self._request(
                    'POST',
                    endpoint,
                    json={'content': new_content},
                    timeout=30
                )
                
                return response and response.ok
                
            except Exception as e:
                print(f"AI external link suggestion failed: {e}")
                return False
            
        except Exception as e:
            print(f"Error fixing external links for {url}: {e}")
            return False
    
    def _suggest_redirect_target(self, broken_url: str, source_page_url: str) -> Optional[str]:
        """
        Use AI to suggest a redirect target for a broken internal URL.

        Args:
            broken_url: The broken URL that needs a redirect target
            source_page_url: The page that contains the broken link (for context)

        Returns:
            Suggested redirect target URL, or None if no good match found
        """
        try:
            # Fetch sitemap to get list of available pages
            from data.sitemap_analyzer import SitemapAnalyzer
            sitemap_analyzer = SitemapAnalyzer(self.site_url)
            sitemap_urls = sitemap_analyzer.fetch_sitemap()

            if not sitemap_urls or len(sitemap_urls) == 0:
                return None

            # Get list of available URLs (limit to first 100 for performance)
            available_urls = [url_obj.url for url_obj in sitemap_urls[:100]]

            # Extract slug from broken URL for semantic matching
            broken_parsed = urlparse(broken_url)
            broken_slug = broken_parsed.path.strip('/').split('/')[-1]

            # Simple heuristic: find URLs with similar slugs
            candidates = []
            for candidate_url in available_urls:
                candidate_parsed = urlparse(candidate_url)
                candidate_slug = candidate_parsed.path.strip('/').split('/')[-1]

                # Calculate similarity (simple substring matching)
                if broken_slug and candidate_slug:
                    # Check if slugs share words
                    broken_words = set(broken_slug.replace('-', ' ').split())
                    candidate_words = set(candidate_slug.replace('-', ' ').split())
                    shared_words = broken_words & candidate_words

                    if len(shared_words) >= 2:  # At least 2 words in common
                        similarity_score = len(shared_words) / max(len(broken_words), 1)
                        candidates.append((candidate_url, similarity_score))

            if not candidates:
                # No good candidates found
                return None

            # Sort by similarity score (highest first)
            candidates.sort(key=lambda x: x[1], reverse=True)

            # Use AI to validate the best match if available
            if self.ai_generator and len(candidates) > 0:
                top_candidate = candidates[0][0]

                # Simple validation: if similarity score is high enough, use it
                if candidates[0][1] >= 0.5:  # 50% similarity
                    return top_candidate

            # Return best candidate if found
            return candidates[0][0] if candidates else None

        except Exception as e:
            print(f"   Error suggesting redirect target: {e}")
            return None

    def _fix_broken_links(self, post_id: int, post_type: str, url: str) -> bool:
        """
        Fix broken links with smart 301 redirects for internal links.

        Enhanced workflow:
        1. Detect broken internal links
        2. Create 301 redirects using Redirection plugin
        3. Update links in content
        4. Handle broken external links (remove or archive.org)
        """
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False

            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')

            soup = BeautifulSoup(content_raw, 'html.parser')
            links = soup.find_all('a', href=True)

            modified = False
            redirects_created = 0

            for link in links:
                href = link.get('href', '')
                if not href or href.startswith('#') or href.startswith('mailto:'):
                    continue

                # Check if link is broken
                try:
                    resp = requests.head(href, timeout=5, allow_redirects=True)
                    is_broken = resp.status_code >= 400
                except:
                    # Can't reach - might be broken, be conservative
                    is_broken = False

                if is_broken:
                    # Determine if internal or external link
                    parsed_href = urlparse(href)
                    parsed_site = urlparse(self.site_url)
                    is_internal = parsed_href.netloc == parsed_site.netloc or not parsed_href.netloc

                    if is_internal:
                        # INTERNAL broken link - create 301 redirect
                        print(f"   Found broken internal link: {href}")

                        # Find a similar URL to redirect to
                        redirect_target = self._suggest_redirect_target(href, url)

                        if redirect_target:
                            # Create 301 redirect via Redirection plugin
                            redirect_result = self.wp_publisher.create_301_redirect(
                                source_url=href,
                                target_url=redirect_target
                            )

                            if redirect_result.success:
                                print(f"   ✓ Created 301 redirect: {href} → {redirect_target}")
                                # Update link in content to point to new target
                                link['href'] = redirect_target
                                redirects_created += 1
                                modified = True
                            else:
                                print(f"   ⚠️  Could not create redirect: {redirect_result.error}")
                                # Still update the link
                                link['href'] = redirect_target
                                modified = True
                        else:
                            # No good redirect target found - remove link but keep text
                            print(f"   ⚠️  No redirect target found, removing link")
                            link.unwrap()
                            modified = True

                    else:
                        # EXTERNAL broken link
                        print(f"   Found broken external link: {href}")

                        # Try to find if it redirects somewhere
                        try:
                            final_resp = requests.get(href, timeout=10, allow_redirects=True)
                            if final_resp.ok and final_resp.url != href:
                                # It redirected to a working URL
                                print(f"   ✓ Found redirect: {href} → {final_resp.url}")
                                link['href'] = final_resp.url
                                modified = True
                                continue
                        except:
                            pass

                        # Try archive.org as fallback
                        archive_url = f"https://web.archive.org/web/{href}"
                        try:
                            archive_resp = requests.head(archive_url, timeout=5)
                            if archive_resp.ok:
                                print(f"   ✓ Using archive.org version")
                                link['href'] = archive_url
                                modified = True
                                continue
                        except:
                            pass

                        # If all else fails, remove the link but keep text
                        print(f"   ⚠️  No replacement found, removing link")
                        link.unwrap()
                        modified = True

            if not modified:
                print(f"   No broken links found")
                return True  # Nothing to fix

            if redirects_created > 0:
                print(f"   Created {redirects_created} 301 redirect(s)")

            # Save updated content
            new_content = str(soup)

            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )

            return response and response.ok

        except Exception as e:
            print(f"Error fixing broken links for {url}: {e}")
            return False
    
    def _fix_canonical_tag(self, post_id: int, post_type: str, url: str) -> bool:
        """Add or fix canonical tag via Yoast/RankMath meta or post meta."""
        try:
            # Canonical tags are typically handled by SEO plugins via post meta
            # We'll set the _yoast_wpseo_canonical meta field
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            
            # Set canonical to self (most common fix)
            response = self._request(
                'POST',
                endpoint,
                json={
                    'meta': {
                        '_yoast_wpseo_canonical': url,
                        'rank_math_canonical_url': url
                    }
                },
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing canonical tag for {url}: {e}")
            return False
    
    def _fix_schema_markup(self, post_id: int, post_type: str, url: str) -> bool:
        """Add Article schema markup to content."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            date_published = post_data.get('date', '')
            date_modified = post_data.get('modified', '')
            
            # Extract description
            soup = BeautifulSoup(content_raw, 'html.parser')
            text_content = soup.get_text().strip()[:200]
            
            # Create Article schema
            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": title[:110],  # Schema limit
                "description": text_content,
                "url": url,
                "datePublished": date_published,
                "dateModified": date_modified,
                "author": {
                    "@type": "Person",
                    "name": "Author"  # Would need to fetch actual author
                },
                "publisher": {
                    "@type": "Organization",
                    "name": self.site_url.replace('https://', '').replace('http://', '')
                }
            }
            
            import json
            schema_script = f'\n\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'
            
            new_content = content_raw + schema_script
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            response = self._request(
                'POST',
                endpoint,
                json={'content': new_content},
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing schema markup for {url}: {e}")
            return False
    
    def _fix_open_graph(self, post_id: int, post_type: str, url: str) -> bool:
        """Add Open Graph meta tags via Yoast/RankMath meta."""
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            content = post_data.get('content', {}).get('rendered', '')
            
            soup = BeautifulSoup(content, 'html.parser')
            description = soup.get_text().strip()[:200]
            
            # Use Yoast meta fields for OG tags
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            
            response = self._request(
                'POST',
                endpoint,
                json={
                    'meta': {
                        '_yoast_wpseo_opengraph-title': title[:60],
                        '_yoast_wpseo_opengraph-description': description,
                        'rank_math_facebook_title': title[:60],
                        'rank_math_facebook_description': description
                    }
                },
                timeout=30
            )
            
            return response and response.ok
            
        except Exception as e:
            print(f"Error fixing Open Graph for {url}: {e}")
            return False
    
    def _fix_content_length(self, post_id: int, post_type: str, url: str) -> bool:
        """Expand thin content using AI (target: 300+ words for articles)."""
        try:
            if not self.ai_generator:
                return False  # Need AI for content expansion
            
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            content_raw = post_data.get('content', {}).get('raw', '')
            if not content_raw:
                content_raw = post_data.get('content', {}).get('rendered', '')
            
            title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            
            soup = BeautifulSoup(content_raw, 'html.parser')
            current_text = soup.get_text().strip()
            current_word_count = len(current_text.split())
            
            if current_word_count >= 300:
                return True  # Already OK
            
            target_additional = 400 - current_word_count  # Aim for 400 words total
            
            try:
                prompt = f"""Expand this article content by adding {target_additional} more words of valuable information.

Title: {title}
Current Content:
{current_text}

Requirements:
- Add {target_additional} words of NEW, valuable content
- Keep the same tone and style
- Add new sections with H2 headers if appropriate
- Include practical tips or examples
- Make it more comprehensive and helpful
- Output in HTML format with proper tags

Return the COMPLETE expanded article in HTML (include the original content plus your additions)."""
                
                response = self.ai_generator.client.messages.create(
                    model=self.ai_generator.model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                expanded_content = response.content[0].text.strip()
                
                # Verify it's actually longer
                new_soup = BeautifulSoup(expanded_content, 'html.parser')
                new_word_count = len(new_soup.get_text().split())
                
                if new_word_count > current_word_count:
                    endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
                    response = self._request(
                        'POST',
                        endpoint,
                        json={'content': expanded_content},
                        timeout=60
                    )
                    return response and response.ok
                
            except Exception as e:
                print(f"AI content expansion failed: {e}")
            
            return False
            
        except Exception as e:
            print(f"Error fixing content length for {url}: {e}")
            return False
    
    def _fix_noindex(self, post_id: int, post_type: str, url: str) -> bool:
        """
        Remove noindex directive from a page/post.
        
        Handles:
        1. Yoast SEO plugin meta
        2. RankMath SEO plugin meta
        3. All in One SEO meta
        """
        try:
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False
            
            endpoint = f"{self.api_base}/pages/{post_id}" if post_type == 'page' else f"{self.api_base}/posts/{post_id}"
            
            # Build meta update payload
            meta_updates = {}
            
            # Yoast SEO fields
            yoast_meta = post_data.get('yoast_head_json', {}) or post_data.get('meta', {})
            if yoast_meta:
                # Yoast uses _yoast_wpseo_meta-robots-noindex
                meta_updates['_yoast_wpseo_meta-robots-noindex'] = '0'  # 0 = index, 1 = noindex
                meta_updates['_yoast_wpseo_meta-robots-nofollow'] = '0'
            
            # RankMath SEO fields
            rank_math_meta = post_data.get('rank_math', {}) or {}
            if rank_math_meta or 'rank_math_robots' in str(post_data.get('meta', {})):
                # RankMath stores as array: ['index', 'follow'] or ['noindex']
                meta_updates['rank_math_robots'] = ['index', 'follow']
            
            # All in One SEO
            meta_updates['_aioseo_noindex'] = False
            
            # Try to update via post meta
            update_payload = {'meta': meta_updates}
            
            response = self._request(
                'POST',
                endpoint,
                json=update_payload,
                timeout=30
            )
            
            if response and response.ok:
                print(f"✅ Removed noindex from {url}")
                return True
            else:
                # Try alternative: direct content edit to remove noindex from HTML
                content = post_data.get('content', {}).get('raw', '')
                if content:
                    # Remove any hardcoded noindex in content
                    import re
                    original_len = len(content)
                    content = re.sub(r'<meta[^>]*noindex[^>]*>', '', content, flags=re.IGNORECASE)
                    
                    if len(content) < original_len:
                        response = self._request(
                            'POST',
                            endpoint,
                            json={'content': content},
                            timeout=30
                        )
                        return response and response.ok
                
                print(f"⚠️ Could not remove noindex via meta API for {url}")
                return False
            
        except Exception as e:
            print(f"Error fixing noindex for {url}: {e}")
            return False
    
    def _fix_orphaned_pages(self, post_id: int, post_type: str, url: str) -> bool:
        """
        Fix orphaned pages (pages with < 3 internal links).

        Strategy:
        1. Identify hub pages (pillar content) to link from
        2. Find semantically related hub pages
        3. Add contextual links in those hub pages pointing to this orphan
        4. Creates bidirectional linking for SEO
        """
        try:
            # Get the orphaned page's content
            post_data = self._get_post_content(post_id, post_type)
            if not post_data:
                return False

            orphan_title = post_data.get('title', {}).get('rendered', '') or post_data.get('title', {}).get('raw', '')
            orphan_excerpt = post_data.get('excerpt', {}).get('rendered', '')

            soup_excerpt = BeautifulSoup(orphan_excerpt, 'html.parser')
            orphan_summary = soup_excerpt.get_text()[:200]

            print(f"   Fixing orphaned page: {orphan_title}")

            # Get all posts to find hub pages
            try:
                response = self._request(
                    'GET',
                    f"{self.api_base}/posts",
                    params={'per_page': 100, 'status': 'publish', 'orderby': 'modified', 'order': 'desc'},
                    timeout=30
                )
                all_posts = response.json() if response and response.ok else []
            except:
                all_posts = []

            if not all_posts:
                print(f"   No posts found to link from")
                return False

            # Find potential hub pages (longer content, more authoritative)
            # Simple heuristic: look for posts with related keywords in title
            orphan_keywords = set(orphan_title.lower().split())
            orphan_keywords = {w for w in orphan_keywords if len(w) > 4}  # Filter short words

            hub_candidates = []
            for post in all_posts:
                post_url = post.get('link', '')
                if post_url.rstrip('/') == url.rstrip('/'):
                    continue  # Skip self

                post_id_candidate = post.get('id', 0)
                post_title = post.get('title', {}).get('rendered', '')
                post_excerpt = post.get('excerpt', {}).get('rendered', '')

                # Check keyword overlap
                post_keywords = set(post_title.lower().split())
                shared_keywords = orphan_keywords & post_keywords

                if len(shared_keywords) >= 1:  # At least 1 shared keyword
                    hub_candidates.append({
                        'id': post_id_candidate,
                        'url': post_url,
                        'title': post_title,
                        'type': 'post',  # Assume post for now
                        'shared_keywords': len(shared_keywords)
                    })

            if not hub_candidates:
                print(f"   No related hub pages found")
                return False

            # Sort by number of shared keywords (most related first)
            hub_candidates.sort(key=lambda x: x['shared_keywords'], reverse=True)

            # Add links in top 2-3 hub pages
            links_added = 0
            for hub in hub_candidates[:3]:
                try:
                    # Get hub page content
                    hub_post_data = self._get_post_content(hub['id'], hub['type'])
                    if not hub_post_data:
                        continue

                    hub_content = hub_post_data.get('content', {}).get('raw', '')
                    if not hub_content:
                        hub_content = hub_post_data.get('content', {}).get('rendered', '')

                    # Check if already linked
                    if url in hub_content:
                        print(f"   Already linked from: {hub['title']}")
                        continue

                    # Add a contextual link to the orphaned page
                    # Simple approach: add at the end before any existing related articles
                    link_html = f'\n<p>For more information, see our guide on <a href="{url}">{orphan_title}</a>.</p>\n'

                    # Try to insert before Related Articles section if it exists
                    if '<h2>Related Articles</h2>' in hub_content:
                        modified_hub_content = hub_content.replace(
                            '<h2>Related Articles</h2>',
                            link_html + '<h2>Related Articles</h2>'
                        )
                    else:
                        # Append at end
                        modified_hub_content = hub_content + link_html

                    # Update hub page
                    hub_endpoint = f"{self.api_base}/posts/{hub['id']}"
                    response = self._request(
                        'POST',
                        hub_endpoint,
                        json={'content': modified_hub_content},
                        timeout=30
                    )

                    if response and response.ok:
                        print(f"   ✓ Added link from: {hub['title']}")
                        links_added += 1
                    else:
                        print(f"   ✗ Failed to update: {hub['title']}")

                    time.sleep(2)  # Rate limiting

                except Exception as e:
                    print(f"   Error updating hub page: {e}")
                    continue

            if links_added > 0:
                print(f"   ✓ Added {links_added} incoming link(s) to this orphaned page")
                return True
            else:
                print(f"   Could not add links to orphaned page")
                return False

        except Exception as e:
            print(f"Error fixing orphaned page {url}: {e}")
            return False

    def _fix_robots_txt_blocking(self, post_id: int, post_type: str, url: str) -> bool:
        """
        Fix robots.txt blocking issues.

        Since robots.txt is a server file, this method:
        1. Checks if the blocking is in meta tags (fixable via API)
        2. Provides instructions for manually updating robots.txt
        3. Generates a corrected robots.txt snippet
        """
        try:
            # First, try to fix any meta noindex tags (we can do this via API)
            meta_fixed = self._fix_noindex(post_id, post_type, url)

            # Get current page to check if still blocked
            response = self._request('GET', url, timeout=10, auth=False)
            if not response or not response.ok:
                print(f"⚠️  Could not fetch {url} to validate fix")
                return meta_fixed

            # Check for X-Robots-Tag header
            x_robots = response.headers.get('X-Robots-Tag', '')
            if 'noindex' in x_robots.lower():
                print(f"⚠️  {url} has noindex in X-Robots-Tag HTTP header")
                print(f"   This requires server configuration changes (.htaccess or server config)")

            # Fetch robots.txt
            robots_url = f"{self.site_url}/robots.txt"
            robots_response = self._request('GET', robots_url, timeout=10, auth=False)

            if robots_response and robots_response.ok:
                robots_txt = robots_response.text
                parsed_url = urlparse(url)
                url_path = parsed_url.path

                # Check if this specific URL is disallowed
                is_blocked = False
                blocking_rules = []

                for line in robots_txt.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('disallow:'):
                        pattern = line.split(':', 1)[1].strip()
                        if pattern and (pattern == url_path or url_path.startswith(pattern)):
                            is_blocked = True
                            blocking_rules.append(pattern)

                if is_blocked:
                    print(f"\n⚠️  MANUAL FIX REQUIRED:")
                    print(f"   {url} is blocked by robots.txt")
                    print(f"   Blocking rules: {', '.join(blocking_rules)}")
                    print(f"\n   📝 To fix, edit your robots.txt file and remove these lines:")
                    for rule in blocking_rules:
                        print(f"      Disallow: {rule}")
                    print(f"\n   Access robots.txt at: {robots_url}")
                    print(f"   Via WordPress: Use a plugin like 'Yoast SEO' to edit robots.txt")
                    print(f"   Via FTP: Download, edit, and re-upload /robots.txt")
                    print(f"   Via cPanel: File Manager → Edit /robots.txt\n")

                    # Return partial success if we fixed meta tags
                    return meta_fixed
                else:
                    print(f"✓ {url} is not blocked by robots.txt disallow rules")
                    return True
            else:
                print(f"   Could not fetch robots.txt from {robots_url}")
                return meta_fixed

        except Exception as e:
            print(f"Error checking robots.txt blocking for {url}: {e}")
            return False

    def _fix_generic(self, post_id: int, post_type: str, url: str, issue_type: str, category: str) -> bool:
        """Generic fix handler for issues without specific handlers."""
        print(f"No specific handler for {issue_type} (category: {category})")
        return False

