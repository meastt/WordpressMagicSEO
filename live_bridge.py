import os
import logging
import markdown
import re
from urllib.parse import urlparse
from typing import Dict, List, Optional
from wordpress.publisher import WordPressPublisher

class LiveBridge:
    """
    The 'Messenger' of the AI Content Engine.
    Coordinates the deployment of local AI assets to the live WordPress site.
    """
    
    def __init__(self, site_url: str = None, username: str = None, app_password: str = None, target_url: str = None):
        self.logger = logging.getLogger(__name__)
        
        # 1. Resolve Site URL
        self.site_url = site_url or os.getenv("WP_SITE_URL")
        
        # 2. Heuristic for dynamic credential lookup if target_url is provided
        if target_url and not self.site_url:
            parsed = urlparse(target_url)
            domain = parsed.netloc.replace(".", "_").upper()
            env_url = os.getenv(f"WP_{domain}_URL")
            if env_url:
                self.site_url = env_url
                self.logger.info(f"📍 Resolved site URL from domain: {self.site_url}")

        # 3. Resolve Username/Password
        self.username = username or os.getenv("WP_USERNAME")
        self.app_password = app_password or os.getenv("WP_APP_PASSWORD")
        
        # Fallback to domain-specific if missing
        if target_url and (not self.username or not self.app_password):
            parsed = urlparse(target_url)
            domain = parsed.netloc.replace(".", "_").upper()
            self.username = self.username or os.getenv(f"WP_{domain}_USERNAME")
            self.app_password = self.app_password or os.getenv(f"WP_{domain}_PASSWORD")
            if self.username:
                self.logger.info(f"🔐 Resolved credentials for domain: {domain}")

        if not all([self.site_url, self.username, self.app_password]):
            raise ValueError(f"WordPress credentials missing. Checked WP_USERNAME/WP_APP_PASSWORD and domain-specific vars. Domain: {urlparse(target_url).netloc if target_url else 'None'}")
            
        self.publisher = WordPressPublisher(
            site_url=self.site_url,
            username=self.username,
            application_password=self.app_password
        )

    def push_optimization(
        self, 
        target_url: str, 
        optimized_data: Dict
    ) -> bool:
        """
        Pushes AI-optimized content to a live WordPress post.
        
        optimized_data expects:
        - title: New SEO title
        - categories: List of category names
        - tags: List of tag names
        - image_path: Local path to the new image
        - alt_text: Alt text for the image
        - update_date: ISO 8601 date string
        - comparison_table: Markdown table to append
        """
        self.logger.info(f"🚀 Preparing to push live updates to: {target_url}")
        
        # 1. Resolve Post ID
        post = self.publisher.find_post_or_page_by_url(target_url)
        if not post:
            self.logger.error(f"Could not find WordPress post for URL: {target_url}")
            return False
            
        post_id = post['id']
        post_type = post.get('_wp_type', 'post')
        current_content = post['content']['rendered']
        
        self.logger.info(f"✅ Found {post_type} (ID: {post_id})")

        # 2. Upload Image (Media Library)
        media_id = None
        image_path = optimized_data.get('image_path')
        if image_path and os.path.exists(image_path):
            self.logger.info(f"📸 Uploading featured image: {image_path}")
            with open(image_path, "rb") as img_file:
                media_result = self.publisher.upload_image(
                    image_bytes=img_file.read(),
                    filename=os.path.basename(image_path),
                    alt_text=optimized_data.get('alt_text', ''),
                    title=optimized_data.get('title', '')
                )
                if media_result:
                    media_id = media_result['id']
                    self.logger.info(f"✅ Image uploaded (Media ID: {media_id})")

        # 3. Handle Fusion / Formatting
        new_content = optimized_data.get('optimized_content')
        if not new_content:
            # Fallback to simple append if fusion wasn't used
            current_content = post['content']['raw'] or post['content']['rendered']
            new_content = current_content
            comparison_table = optimized_data.get('comparison_table')
            if comparison_table:
                table_html = markdown.markdown(comparison_table, extensions=['tables'])
                new_content += f"\n\n<!-- wp:separator -->\n<hr class=\"wp-block-separator\"/>\n<!-- /wp:separator -->\n\n"
                new_content += f"<!-- wp:heading -->\n<h2>Quick Comparison Guide</h2>\n<!-- /wp:heading -->\n\n"
                new_content += f"<!-- wp:table -->\n<figure class=\"wp-block-table\">{table_html}</figure>\n<!-- /wp:table -->"
        else:
            # Clean up potential LLM code leak (remove ```html ... ``` or ``` ... ```)
            new_content = re.sub(r'```(?:html)?', '', new_content)
            new_content = new_content.replace('```', '').strip()

            # 🛠️ Surgical Title Stripping (Prevent Double Titles)
            # Remove any leading H1 or H2 that matches the new SEO title
            title_to_match = optimized_data.get('title', '').strip()
            if title_to_match:
                # Patterns for <h1>Title</h1> or <h2>Title</h2> (case-insensitive)
                pattern = f'<(h1|h2)[^>]*>\\s*{re.escape(title_to_match)}\\s*</\\1>'
                new_content = re.sub(pattern, '', new_content, flags=re.IGNORECASE).strip()

            # Wrap the fused content for Gutenberg if it looks like raw HTML
            if "<!-- wp:" not in new_content:
                # Basic wrapping for classic-to-block transition
                new_content = f"<!-- wp:freeform -->\n{new_content}\n<!-- /wp:freeform -->"

        # 4. Perform Live Update
        self.logger.info("🛠️ Applying live updates to WordPress...")
        result = self.publisher.update_post(
            post_id=post_id,
            title=optimized_data.get('title'),
            content=new_content,
            meta_title=optimized_data.get('title'),
            meta_description=optimized_data.get('alt_text'), # Use alt-text as desc fallback if needed
            categories=optimized_data.get('categories'),
            tags=optimized_data.get('tags'),
            featured_media=media_id,
            update_date=optimized_data.get('update_date'),
            status='publish', # Force publish status
            item_type=post_type
        )
        
        if result.success:
            self.logger.info(f"🎉 SUCCESS! Post updated: {result.url}")
            return True
        else:
            self.logger.error(f"❌ Update failed: {result.error}")
            return False
