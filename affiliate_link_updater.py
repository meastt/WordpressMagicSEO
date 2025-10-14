"""
Affiliate Link Updater
----------------------
Uses AI to intelligently update content with relevant affiliate links.
Removes outdated links and inserts new, contextually relevant affiliate links.
"""

import anthropic
import os
from typing import Dict, List, Optional
import json
import re


class AffiliateLinkUpdater:
    """AI-powered affiliate link updater for content."""
    
    def __init__(self, api_key: str = None):
        """Initialize with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def update_content_with_affiliate_links(
        self,
        content: str,
        title: str,
        available_links: List[Dict],
        keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        Use AI to update content with relevant affiliate links.
        
        Removes outdated/irrelevant links and adds new affiliate links where appropriate.
        
        Args:
            content: HTML content to update
            title: Title of the content/post
            available_links: List of available affiliate links with metadata
            keywords: Optional keywords associated with the content
            
        Returns:
            Dict with updated_content, links_added, links_removed, and analysis
        """
        
        # Prepare affiliate links information for the AI
        links_info = ""
        for i, link in enumerate(available_links, 1):
            links_info += f"{i}. {link['brand']} - {link['product_name']} ({link['product_type']})\n"
            links_info += f"   URL: {link['url']}\n"
            if link.get('keywords'):
                links_info += f"   Keywords: {', '.join(link['keywords'])}\n"
            links_info += "\n"
        
        keywords_text = f"Content keywords: {', '.join(keywords)}" if keywords else ""
        
        prompt = f"""You are an expert content editor specializing in affiliate marketing and SEO.

TASK: Update the following content by:
1. REMOVING any existing affiliate links that are:
   - Outdated or no longer relevant
   - Generic or low-quality
   - Not related to the current content topic
   
2. ADDING relevant affiliate links from the provided list by:
   - Naturally incorporating them where they add value
   - Matching products to mentions in the content
   - Creating helpful product recommendations
   - Ensuring links feel organic and helpful, not spammy

CONTENT TITLE: {title}
{keywords_text}

AVAILABLE AFFILIATE LINKS:
{links_info}

ORIGINAL CONTENT:
{content}

GUIDELINES:
- Only add affiliate links where they genuinely help the reader
- Use natural anchor text (product names, helpful phrases)
- Add 2-5 relevant links maximum (don't overdo it)
- Remove any existing affiliate links if they don't match our available products
- Maintain the content's helpfulness and readability
- DO NOT change the overall content structure or main message
- Keep all existing HTML formatting

OUTPUT FORMAT (JSON only):
{{
  "updated_content": "Full HTML content with updated links",
  "changes": {{
    "links_added": [
      {{
        "product": "Product name",
        "url": "affiliate URL",
        "placement": "Where it was added (brief description)"
      }}
    ],
    "links_removed": [
      {{
        "url": "URL that was removed",
        "reason": "Why it was removed"
      }}
    ]
  }},
  "analysis": "Brief explanation of changes made and why"
}}

Return ONLY valid JSON, no additional text."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            response_text = message.content[0].text.strip()
            # Remove markdown code blocks if present
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(response_text)
            
            return {
                "updated_content": result.get("updated_content", content),
                "links_added": result.get("changes", {}).get("links_added", []),
                "links_removed": result.get("changes", {}).get("links_removed", []),
                "analysis": result.get("analysis", "No changes made"),
                "success": True
            }
            
        except Exception as e:
            return {
                "updated_content": content,
                "links_added": [],
                "links_removed": [],
                "analysis": f"Error updating content: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def batch_update_posts(
        self,
        posts: List[Dict],
        available_links: List[Dict],
        delay_seconds: float = 1.0
    ) -> List[Dict]:
        """
        Update multiple posts with affiliate links.
        
        Args:
            posts: List of posts with 'content', 'title', 'id', 'keywords' keys
            available_links: List of available affiliate links
            delay_seconds: Delay between API calls to respect rate limits
            
        Returns:
            List of update results for each post
        """
        import time
        
        results = []
        
        for post in posts:
            result = self.update_content_with_affiliate_links(
                content=post.get('content', ''),
                title=post.get('title', ''),
                available_links=available_links,
                keywords=post.get('keywords', [])
            )
            
            results.append({
                "post_id": post.get('id'),
                "title": post.get('title'),
                **result
            })
            
            # Rate limiting
            time.sleep(delay_seconds)
        
        return results
    
    def extract_existing_affiliate_links(self, content: str) -> List[str]:
        """
        Extract existing affiliate links from content.
        Looks for URLs with common affiliate parameters.
        
        Args:
            content: HTML content to scan
            
        Returns:
            List of affiliate URLs found
        """
        # Common affiliate parameters/patterns
        affiliate_patterns = [
            r'affiliate=',
            r'aff_id=',
            r'ref=',
            r'tag=',
            r'tracking=',
            r'associate',
            r'partner',
        ]
        
        # Find all URLs in content
        url_pattern = r'href=["\'](https?://[^"\']+)["\']'
        urls = re.findall(url_pattern, content)
        
        # Filter for affiliate links
        affiliate_links = []
        for url in urls:
            if any(pattern in url.lower() for pattern in affiliate_patterns):
                affiliate_links.append(url)
        
        return affiliate_links
