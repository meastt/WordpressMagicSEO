"""
claude_content_generator.py
===========================
Enhanced content generator using Claude API for intelligent, research-based content creation.
"""

import os
import anthropic
from typing import List, Dict
import time


class ClaudeContentGenerator:
    """Generate high-quality content using Claude API with web research."""
    
    def __init__(self, api_key: str = None):
        """Initialize with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def research_topic(self, topic_title: str, keywords: List[str]) -> str:
        """Use Claude to research a topic with web search."""
        prompt = f"""Research the topic "{topic_title}" focusing on these keywords: {', '.join(keywords)}.

Provide:
1. Current market trends and latest information
2. What people are searching for related to this topic
3. Key facts and data points
4. Common questions people have
5. Top competing content angles

Be thorough and cite recent sources."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    
    def generate_article(
        self, 
        topic_title: str, 
        keywords: List[str],
        research: str,
        meta_description: str,
        existing_content: str = None,
        internal_links: List[Dict] = None
    ) -> Dict[str, str]:
        """Generate complete article with metadata."""
        
        action = "update this existing content" if existing_content else "create new content"
        existing_context = f"\n\nEXISTING CONTENT TO UPDATE:\n{existing_content}" if existing_content else ""
        
        internal_links_text = ""
        if internal_links:
            internal_links_text = "\n\nINTERNAL LINKS to include naturally:\n"
            for link in internal_links:
                internal_links_text += f"- {link['title']}: {link['url']}\n"
        
        prompt = f"""You are an expert SEO content writer. {action.capitalize()} about: "{topic_title}"

TARGET KEYWORDS: {', '.join(keywords)}

RESEARCH DATA:
{research}
{existing_context}
{internal_links_text}

Create a comprehensive, helpful article that:
1. Uses natural, engaging writing (not robotic)
2. Includes the target keywords naturally (don't force them)
3. Provides genuine value to readers
4. Includes specific examples and actionable advice
5. Incorporates 2-3 external links to authoritative sources
6. Naturally weaves in the provided internal links where relevant
7. Uses proper HTML formatting (h2, h3, p, ul, ol, strong, em tags)
8. Follows Google's helpful content guidelines
9. Is optimized for both traditional SEO and AI search (LLMs)

ARTICLE STRUCTURE:
- Engaging introduction (hook the reader immediately)
- 4-6 main sections with descriptive H2 headers
- Subsections with H3 headers where needed
- Bullet points or numbered lists for clarity
- Strong conclusion with actionable next steps

LENGTH: 1500-2500 words

META DATA NEEDED:
- SEO Title (under 60 chars, include primary keyword)
- Meta Description: {meta_description}
- 3-5 category tags
- 5-8 relevant tags

OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "title": "SEO-optimized title here",
  "content": "Full HTML article content here",
  "categories": ["cat1", "cat2"],
  "tags": ["tag1", "tag2", "tag3"],
  "meta_title": "SEO title under 60 chars",
  "meta_description": "Meta description under 155 chars"
}}

DO NOT include any text outside the JSON structure."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        import json
        response_text = message.content[0].text.strip()
        # Remove markdown code blocks if present
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(response_text)
    
    def analyze_competitor_content(self, topic: str, top_urls: List[str]) -> str:
        """Analyze top-ranking competitor content to inform strategy."""
        urls_text = "\n".join([f"- {url}" for url in top_urls[:3]])
        
        prompt = f"""Analyze the top-ranking content for "{topic}".

TOP RANKING URLs:
{urls_text}

Based on what typically ranks well, provide:
1. Common content structure and length
2. Key topics covered
3. Content depth and detail level
4. Multimedia elements used
5. Unique angles to differentiate our content

Be specific and actionable."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    
    def rate_limit_delay(self, delay_seconds: float = 1.0):
        """Add delay between API calls to respect rate limits."""
        time.sleep(delay_seconds)