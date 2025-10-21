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
        """Use Claude with web search to research a topic thoroughly."""
        from datetime import datetime
        current_date = datetime.now().strftime('%B %d, %Y')

        prompt = f"""IMPORTANT: Use web search to find current, up-to-date information about this topic.

Research the topic "{topic_title}" focusing on these keywords: {', '.join(keywords)}.

Today's date is {current_date}. Search for information from the last 6-12 months.

Using web search, provide:
1. **Current market trends** - What's happening NOW in this space (search for recent articles, reviews, discussions)
2. **Latest product releases or updates** - Any new developments in the last 6 months
3. **What people are searching for** - Current search trends and questions
4. **Key facts and data points** - Statistics, prices, specifications (verify with searches)
5. **Top competing content** - What are the best articles/guides ranking for these keywords
6. **Common questions** - What are people asking on forums, Reddit, review sites

**Critical: Actually search the web for each of these points. Cite specific sources with URLs and dates.**

Format your research with clear sections and bullet points. Include source URLs where possible."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            thinking={
                "type": "enabled",
                "budget_tokens": 2000
            }
        )

        # Extract text from response (handle thinking blocks)
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text

        return response_text
    
    def generate_article(
        self,
        topic_title: str,
        keywords: List[str],
        research: str,
        meta_description: str,
        existing_content: str = None,
        internal_links: List[Dict] = None,
        affiliate_links: List[Dict] = None
    ) -> Dict[str, str]:
        """Generate complete article with metadata and affiliate links."""

        # Get current date for context
        from datetime import datetime
        current_date = datetime.now()
        date_context = f"\n\nCURRENT DATE CONTEXT: Today is {current_date.strftime('%B %d, %Y')} (Month: {current_date.strftime('%B')}, Year: {current_date.year})"
        date_context += "\nIMPORTANT: Use the current year in any time-sensitive content (e.g., 'Best X in 2025', 'Top X for 2025'). Keep content fresh and current."

        action = "update this existing content" if existing_content else "create new content"
        existing_context = f"\n\nEXISTING CONTENT TO UPDATE:\n{existing_content}" if existing_content else ""
        
        internal_links_text = ""
        if internal_links:
            internal_links_text = "\n\nINTERNAL LINKS to include naturally:\n"
            for link in internal_links:
                internal_links_text += f"- {link['title']}: {link['url']}\n"
        
        affiliate_links_text = ""
        if affiliate_links:
            affiliate_links_text = "\n\nAFFILIATE PRODUCT LINKS to include naturally:\n"
            for link in affiliate_links:
                affiliate_links_text += f"- {link['brand']} {link['product_name']} ({link['product_type']}): {link['url']}\n"
        
        prompt = f"""You are an expert SEO content writer. {action.capitalize()} about: "{topic_title}"
{date_context}

TARGET KEYWORDS: {', '.join(keywords)}

RESEARCH DATA:
{research}
{existing_context}
{internal_links_text}
{affiliate_links_text}

Create a comprehensive, helpful article that:
1. Uses natural, engaging writing (not robotic)
2. Includes the target keywords naturally (don't force them)
3. Provides genuine value to readers
4. Includes specific examples and actionable advice
5. Incorporates 2-3 external links to authoritative sources
6. Naturally weaves in the provided internal links where relevant
7. Naturally incorporates affiliate product links where they add value (don't force them)
8. Uses proper HTML formatting (h2, h3, p, ul, ol, strong, em tags)
9. Follows Google's helpful content guidelines
10. Is optimized for both traditional SEO and AI search (LLMs)

ARTICLE STRUCTURE:
- Engaging introduction (hook the reader immediately)
- 4-6 main sections with descriptive H2 headers
- Subsections with H3 headers where needed
- Bullet points or numbered lists for clarity
- Strong conclusion with actionable next steps

LENGTH: 1500-2500 words

META DATA & TAXONOMIES:
- Create a NEW, SEO-optimized title (under 60 chars, include primary keyword, must be different from old title)
- Meta Title: Similar to title but optimized for SERP click-through
- Meta Description: Compelling 150-155 char description that drives clicks
- Categories: 3-5 relevant, broad categories (e.g., "Photography Tips", "Camera Reviews")
- Tags: 5-8 specific, relevant tags (e.g., "astrophotography", "ZWO cameras", "planetary imaging")
  * Tags should be highly specific to the content
  * Include product names, techniques, or specific topics mentioned
  * Help users discover related content

SCHEMA MARKUP (JSON-LD):
Generate appropriate schema.org structured data for this content:
- **Article schema** (ALWAYS include): datePublished, headline, author, image, publisher
- **FAQ schema** (if content has Q&A sections): Include questions and answers
- **HowTo schema** (if step-by-step instructions): Include steps with details
- **Product/Review schema** (if reviewing products): Include ratings, products

OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "title": "SEO-optimized title here",
  "content": "Full HTML article content here",
  "categories": ["cat1", "cat2"],
  "tags": ["tag1", "tag2", "tag3"],
  "meta_title": "SEO title under 60 chars",
  "meta_description": "Meta description under 155 chars",
  "schema_markup": {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Article headline",
    "datePublished": "{current_date.isoformat()}",
    "author": {{"@type": "Organization", "name": "Site Name"}},
    "publisher": {{"@type": "Organization", "name": "Site Name"}}
  }}
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

        article_data = json.loads(response_text)

        # QUALITY VALIDATION
        self._validate_content_quality(article_data)

        # INJECT SCHEMA MARKUP into content
        if 'schema_markup' in article_data and article_data['schema_markup']:
            schema_json = article_data['schema_markup']
            schema_script = f'\n<script type="application/ld+json">\n{json.dumps(schema_json, indent=2)}\n</script>\n'

            # Append schema to end of content
            article_data['content'] += schema_script
            print(f"✅ Schema markup injected: {schema_json.get('@type', 'Unknown')}")

        return article_data

    def _validate_content_quality(self, article_data: Dict) -> None:
        """
        Validate generated content meets quality standards.

        Raises:
            ValueError: If content fails quality checks
        """
        content = article_data.get('content', '')
        title = article_data.get('title', '')

        # Check 1: Minimum word count
        word_count = len(content.split())
        if word_count < 1500:
            raise ValueError(f"Content too short: {word_count} words (minimum: 1500)")

        # Check 2: Detect AI disclosure language
        ai_patterns = [
            "as an ai",
            "i cannot",
            "i don't have access",
            "i am an ai",
            "as a language model"
        ]
        content_lower = content.lower()
        for pattern in ai_patterns:
            if pattern in content_lower:
                raise ValueError(f"Content contains AI disclosure: '{pattern}' - regenerate required")

        # Check 3: Ensure title exists and is reasonable length
        if not title or len(title) < 10:
            raise ValueError("Title missing or too short")

        if len(title) > 70:
            print(f"⚠️  Warning: Title may be too long ({len(title)} chars): {title}")

        # Check 4: Ensure content has HTML structure
        if '<h2' not in content and '<h3' not in content:
            raise ValueError("Content lacks proper HTML heading structure (no H2/H3 tags)")

        # Check 5: Check for categories and tags
        categories = article_data.get('categories', [])
        tags = article_data.get('tags', [])

        if len(categories) < 2:
            print(f"⚠️  Warning: Only {len(categories)} categories (recommended: 3-5)")

        if len(tags) < 4:
            print(f"⚠️  Warning: Only {len(tags)} tags (recommended: 5-8)")

        # Passed all checks
        print(f"✅ Content quality validated: {word_count} words, {len(categories)} categories, {len(tags)} tags")
    
    def analyze_competitor_content(self, topic: str, top_urls: List[str]) -> str:
        """Analyze top-ranking competitor content using web search."""
        urls_text = "\n".join([f"- {url}" for url in top_urls[:3]])

        prompt = f"""IMPORTANT: Use web search to fetch and analyze these competitor URLs.

Analyze the top-ranking content for "{topic}".

TOP RANKING URLs TO SEARCH AND ANALYZE:
{urls_text}

**Search the web** to access each of these URLs and analyze their content. Provide:

1. **Content structure and length** - How are the top articles organized? Typical word count?
2. **Key topics covered** - What subtopics do ALL top articles include?
3. **Content depth** - How detailed are they? Surface-level or comprehensive?
4. **Multimedia elements** - Images, videos, infographics, charts?
5. **Unique angles** - What makes each stand out? What gaps exist?
6. **Content formats** - Lists, how-to guides, comparisons, reviews?

**Critical: Actually search and analyze the actual URLs provided above.**

Be specific and actionable. Cite examples from the URLs."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            thinking={
                "type": "enabled",
                "budget_tokens": 1000
            }
        )

        # Extract text from response (handle thinking blocks)
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text

        return response_text
    
    def rate_limit_delay(self, delay_seconds: float = 1.0):
        """Add delay between API calls to respect rate limits."""
        time.sleep(delay_seconds)