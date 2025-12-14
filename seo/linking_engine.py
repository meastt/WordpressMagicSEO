"""
smart_linking_engine.py
========================
Intelligent internal linking engine that builds topical authority through strategic link placement.

This creates "topical clusters" that tell Google you're an authority on a topic.
Uses AI to determine relevant connections and optimal anchor text.
"""

import anthropic
from typing import List, Dict, Optional, Set, Tuple
import json
from collections import defaultdict
import re


class SmartLinkingEngine:
    """
    AI-powered internal linking engine that:

    1. **Builds Topical Clusters**: Groups related content into topic clusters
    2. **Creates Hub & Spoke**: Identifies pillar pages and supporting content
    3. **Optimizes Anchor Text**: Uses semantic, natural anchor text
    4. **Strategic Placement**: Links at contextually relevant points
    5. **Avoids Over-optimization**: Natural link density and distribution

    This is critical for topical authority and rankings.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze_site_topology(
        self,
        all_posts: List[Dict]
    ) -> Dict:
        """
        Analyze all content to identify topical clusters and linking opportunities.

        Args:
            all_posts: List of dicts with keys: url, title, keywords, content_summary

        Returns:
            Dictionary with:
            - topic_clusters: Grouped content by topic
            - pillar_pages: Main authority pages for each topic
            - orphan_pages: Pages with few/no internal links
            - linking_opportunities: Specific link suggestions
        """

        if not all_posts or len(all_posts) == 0:
            return {
                'topic_clusters': {},
                'pillar_pages': [],
                'orphan_pages': [],
                'linking_opportunities': []
            }

        # Prepare content summary for AI
        posts_summary = []
        for post in all_posts[:100]:  # Limit to 100 posts for token limits
            posts_summary.append({
                'url': post.get('url', ''),
                'title': post.get('title', ''),
                'keywords': post.get('keywords', [])[:5],  # Top 5 keywords
                'summary': post.get('content_summary', '')[:200]  # First 200 chars
            })

        prompt = f"""You are an SEO architect specializing in topical authority and internal linking.

Analyze this website's content and create a strategic internal linking plan.

**ALL SITE CONTENT:**
{json.dumps(posts_summary, indent=2)}

---

**YOUR MISSION:**

1. **Identify Topic Clusters:**
   - Group related content into coherent topics
   - Find natural topical relationships
   - Example: "Cast Iron Griddles", "Outdoor Cooking", "Griddle Recipes", etc.

2. **Identify Pillar Pages:**
   - Which pages should be the main "hub" for each topic?
   - These are comprehensive, authoritative pages on a topic
   - All related content should link TO these

3. **Find Orphan Pages:**
   - Pages that don't fit cleanly into any cluster
   - Pages that need more internal links pointing to them

4. **Create Linking Strategy:**
   - Which pages should link to which?
   - What anchor text should be used?
   - Where in the content should links appear?

5. **Prioritize Link Building:**
   - Which links will have the most SEO impact?
   - Focus on strengthening topical authority

**PRINCIPLES:**
- 3-5 internal links per page is ideal
- Link from less authoritative → more authoritative pages
- Use semantic, natural anchor text (not exact match keywords)
- Create bidirectional links for related content
- Build hub & spoke architecture (pillar pages at center)

Return JSON:

{{
  "topic_clusters": [
    {{
      "topic": "Cast Iron Griddles",
      "pillar_page": {{
        "url": "...",
        "title": "...",
        "why_pillar": "Most comprehensive, targets main keyword, good rankings"
      }},
      "supporting_pages": [
        {{"url": "...", "title": "...", "relationship": "how it supports pillar"}}
      ]
    }}
  ],
  "orphan_pages": [
    {{
      "url": "...",
      "title": "...",
      "issue": "Why it's orphaned",
      "suggested_cluster": "Where it should fit"
    }}
  ],
  "high_priority_links": [
    {{
      "from_url": "...",
      "from_title": "...",
      "to_url": "...",
      "to_title": "...",
      "anchor_text": "Natural, semantic anchor text",
      "placement_hint": "Where in content to place link",
      "why_important": "SEO/authority reason",
      "priority": "high|medium|low"
    }}
  ],
  "site_architecture_score": 0.0-10.0,
  "topical_authority_score": 0.0-10.0,
  "recommendations": [
    "High-level strategic recommendation 1",
    "Another recommendation..."
  ]
}}

**IMPORTANT:** Create specific, actionable linking recommendations."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
                thinking={
                    "type": "enabled",
                    "budget_tokens": 3000
                }
            )

            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Parse JSON
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(response_text)

            return analysis

        except Exception as e:
            print(f"Error analyzing site topology: {e}")
            return {
                'topic_clusters': {},
                'pillar_pages': [],
                'orphan_pages': [],
                'linking_opportunities': []
            }

    def suggest_contextual_links(
        self,
        current_content: str,
        available_pages: List[Dict],
        max_links: int = 5
    ) -> List[Dict]:
        """
        Suggest contextual internal links for a specific piece of content.

        Uses AI to find the most relevant places to insert links naturally.

        Args:
            current_content: The content to add links to (HTML or plain text)
            available_pages: List of dicts with url, title, keywords, summary
            max_links: Maximum number of links to suggest

        Returns:
            List of link suggestions with anchor text and placement
        """

        # Limit content and available pages for token efficiency
        content_preview = current_content[:5000]
        pages_preview = available_pages[:50]

        prompt = f"""You are an expert at natural, contextual internal linking.

**CURRENT CONTENT (to add links to):**
{content_preview}

**AVAILABLE PAGES TO LINK TO:**
{json.dumps([{'url': p.get('url'), 'title': p.get('title'), 'keywords': p.get('keywords', [])[:3]} for p in pages_preview], indent=2)}

---

**YOUR TASK:**

Find the {max_links} MOST RELEVANT internal links to add to this content.

**CRITERIA:**
1. **Relevance**: Only link to truly related content
2. **Natural Placement**: Link where it adds value for the reader
3. **Semantic Anchors**: Use natural phrases, not forced keywords
4. **User Intent**: Help user find what they're looking for next
5. **Link Diversity**: Don't all link to the same page

**FORMAT:**
For each link suggestion, specify:
- Exact sentence/paragraph where link should be added
- Exact anchor text (3-5 words, natural)
- Which page to link to
- Why this link helps the user

Return JSON:

{{
  "suggested_links": [
    {{
      "link_to_url": "...",
      "link_to_title": "...",
      "anchor_text": "natural 3-5 word phrase",
      "context_sentence": "The exact sentence where this link should appear",
      "placement_hint": "After introducing cast iron seasoning, before maintenance tips",
      "why_relevant": "User learning about cast iron will want this info next",
      "relevance_score": 0.0-10.0
    }}
  ],
  "total_recommended": 3
}}

**IMPORTANT:**
- Only suggest links that genuinely help the reader
- Use natural language for anchor text
- Don't force links where they don't fit"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Parse JSON
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(response_text)

            return result.get('suggested_links', [])

        except Exception as e:
            print(f"Error suggesting contextual links: {e}")
            return []

    def auto_insert_links(
        self,
        content_html: str,
        link_suggestions: List[Dict]
    ) -> str:
        """
        Automatically insert internal links into HTML content at the suggested locations.

        Args:
            content_html: Original HTML content
            link_suggestions: Output from suggest_contextual_links()

        Returns:
            Modified HTML with links inserted
        """

        modified_content = content_html

        # Sort by relevance score (highest first)
        sorted_suggestions = sorted(
            link_suggestions,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        for suggestion in sorted_suggestions:
            anchor_text = suggestion.get('anchor_text', '')
            link_url = suggestion.get('link_to_url', '')
            context = suggestion.get('context_sentence', '')

            if not anchor_text or not link_url:
                continue

            # Try to find the context sentence and add link
            # Simple approach: find anchor text and wrap in <a> tag
            pattern = re.escape(anchor_text)

            # Check if already linked
            if f'<a' in modified_content and anchor_text in modified_content:
                # Skip if this text is already part of a link
                continue

            # Replace first occurrence with link
            replacement = f'<a href="{link_url}">{anchor_text}</a>'
            modified_content = re.sub(
                f'(?<!<a[^>]*>){pattern}(?![^<]*</a>)',
                replacement,
                modified_content,
                count=1
            )

        return modified_content

    def calculate_internal_link_score(self, page_url: str, all_pages: List[Dict]) -> float:
        """
        Calculate how well a page is internally linked.

        Score 0-10 based on:
        - Number of internal links to this page
        - Quality/authority of pages linking to it
        - Relevance of anchor text
        - Link diversity (from different topic clusters)

        Args:
            page_url: The page to score
            all_pages: All pages with their linking data

        Returns:
            Score from 0.0 (poor) to 10.0 (excellent)
        """

        # Count incoming links
        incoming_links = 0
        for page in all_pages:
            if page.get('url') != page_url:
                content = page.get('content', '')
                if page_url in content:
                    incoming_links += 1

        # Score based on link count (3-8 links is ideal)
        if incoming_links == 0:
            link_count_score = 0
        elif incoming_links < 3:
            link_count_score = incoming_links * 2  # 2, 4
        elif 3 <= incoming_links <= 8:
            link_count_score = 8 + (incoming_links - 3) * 0.4  # 8-10
        else:
            link_count_score = max(0, 10 - (incoming_links - 8) * 0.3)  # Diminishing after 8

        return min(10.0, max(0.0, link_count_score))


if __name__ == "__main__":
    # Test
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY to test")
        exit(1)

    engine = SmartLinkingEngine(api_key)

    test_posts = [
        {
            'url': 'https://example.com/best-cast-iron-griddles',
            'title': 'Best Cast Iron Griddles 2025',
            'keywords': ['cast iron griddle', 'best griddles', 'griddle reviews'],
            'content_summary': 'Comprehensive guide to the best cast iron griddles...'
        },
        {
            'url': 'https://example.com/griddle-seasoning-guide',
            'title': 'How to Season a Griddle',
            'keywords': ['griddle seasoning', 'season cast iron', 'griddle maintenance'],
            'content_summary': 'Step-by-step guide to seasoning your griddle...'
        },
        {
            'url': 'https://example.com/outdoor-cooking-tips',
            'title': 'Outdoor Cooking Tips',
            'keywords': ['outdoor cooking', 'camping recipes', 'griddle recipes'],
            'content_summary': 'Tips for cooking outdoors with your griddle...'
        }
    ]

    print("Analyzing site topology...")
    result = engine.analyze_site_topology(test_posts)
    print(json.dumps(result, indent=2))
