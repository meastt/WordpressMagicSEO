"""
competitive_analyzer.py
=======================
AI-powered competitive gap analysis to identify what top-ranking content has that yours doesn't.

This is the "secret weapon" - analyze top 10 results for target keywords and create
content that's MORE comprehensive, better structured, and more valuable.
"""

import anthropic
from typing import List, Dict, Optional
import json


class CompetitiveAnalyzer:
    """
    Analyze top-ranking competitors to identify content gaps and opportunities.

    Uses Claude AI with extended thinking to deeply analyze:
    - What topics competitors cover that you don't
    - What makes their content rank well
    - Content gaps you can fill
    - Unique angles you can take
    - Features/formats that work (tables, comparisons, FAQs, etc.)
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze_competitive_gap(
        self,
        target_keyword: str,
        your_current_content: str,
        your_current_position: int,
        impressions: int,
        clicks: int,
        engagement_data: Optional[Dict] = None
    ) -> Dict:
        """
        Deep AI analysis of competitive landscape for a specific keyword.

        Uses Claude with extended thinking to:
        1. Analyze what's missing from your content vs top 10
        2. Identify winning content patterns
        3. Find unique angles and opportunities
        4. Suggest specific improvements

        Args:
            target_keyword: The main keyword you're targeting
            your_current_content: Your existing content (HTML stripped)
            your_current_position: Current ranking position
            impressions: Monthly impressions from GSC
            clicks: Monthly clicks from GSC
            engagement_data: Optional dict with bounce_rate, avg_time, etc.

        Returns:
            Dictionary with gap_analysis, opportunities, action_plan
        """

        # Prepare engagement context
        engagement_context = ""
        if engagement_data:
            engagement_context = f"""
**YOUR ENGAGEMENT METRICS:**
- Bounce Rate: {engagement_data.get('bounce_rate', 'N/A')}%
- Avg Time on Page: {engagement_data.get('avg_time', 'N/A')}s
- Pages per Session: {engagement_data.get('pages_per_session', 'N/A')}
- Engagement Rate: {engagement_data.get('engagement_rate', 'N/A')}%
"""

        # Extract content summary (first 3000 chars to save tokens)
        content_preview = your_current_content[:3000] if your_current_content else "No content yet"

        prompt = f"""You are an elite SEO strategist and content analyst. Your job is to perform DEEP competitive analysis.

**TARGET KEYWORD:** "{target_keyword}"

**CURRENT SITUATION:**
- Your Position: #{your_current_position}
- Monthly Impressions: {impressions:,}
- Monthly Clicks: {clicks:,}
- CTR: {(clicks/impressions*100) if impressions > 0 else 0:.2f}%
{engagement_context}

**YOUR CURRENT CONTENT (preview):**
{content_preview}

---

**YOUR MISSION:**

1. **Use Web Search** to analyze the top 10 ranking results for "{target_keyword}"
   - What topics/subtopics do they all cover?
   - What content formats work? (guides, comparisons, lists, tables, FAQs)
   - What depth/length is typical for top results?
   - What unique angles do top results take?

2. **Identify Content Gaps:**
   - What topics are competitors covering that you're NOT?
   - What questions are they answering that you're missing?
   - What data/statistics/examples do they include?
   - What multimedia elements (images, tables, videos) do they use?

3. **Analyze Why You're Not Ranking Higher:**
   - Is your content too short/shallow?
   - Are you missing key subtopics?
   - Is your content structure poor?
   - Are engagement signals weak? (high bounce = wrong format/intent)
   - Is search intent mismatched? (they want X, you give Y)

4. **Find Opportunities:**
   - Unique angles competitors haven't taken
   - Outdated information you can update
   - Better ways to structure/present info
   - Content that could rank for featured snippets
   - Internal linking opportunities

5. **Create Action Plan:**
   - Specific sections/topics to add
   - Content format recommendations
   - Length target (word count)
   - Multimedia elements to include
   - FAQ questions to answer
   - Schema markup to add
   - Internal links to create

**CRITICAL:** Actually search the web for "{target_keyword}" and analyze REAL top-ranking pages. Don't guess.

Return your analysis as JSON:

{{
  "search_intent": "informational|commercial|transactional|navigational",
  "intent_match_score": 0.0-10.0,
  "content_depth_score": 0.0-10.0,
  "top_ranking_patterns": [
    "Common pattern 1 across top results",
    "Common pattern 2..."
  ],
  "missing_topics": [
    "Specific topic/subtopic you're missing",
    "Another important gap..."
  ],
  "missing_questions": [
    "Question competitors answer that you don't",
    "Another key question..."
  ],
  "engagement_issues": [
    "Specific issue causing poor engagement",
    "Another engagement problem..."
  ],
  "unique_opportunities": [
    "Unique angle you can take",
    "Differentiation opportunity..."
  ],
  "content_format_recommendation": "ultimate guide|comparison table|step-by-step tutorial|product reviews|etc",
  "target_word_count": 2500,
  "multimedia_needed": [
    "Comparison table showing X vs Y",
    "Infographic about Z",
    "Process diagram for ABC"
  ],
  "schema_opportunities": [
    "FAQ schema for these questions...",
    "HowTo schema for this process...",
    "Product schema if applicable..."
  ],
  "featured_snippet_opportunity": {{
    "possible": true,
    "format": "paragraph|list|table",
    "target_question": "Specific question to target",
    "how_to_optimize": "Specific instructions"
  }},
  "action_plan": [
    {{
      "priority": "high|medium|low",
      "action": "Add section about X with Y details",
      "why": "Specific reason this will help rankings",
      "estimated_impact": "high|medium|low"
    }}
  ],
  "internal_linking_strategy": [
    "Link to related article about X",
    "Create hub page for Y topic cluster"
  ],
  "estimated_ranking_improvement": "+5 positions (based on gap severity)",
  "estimated_time_to_rank": "2-4 weeks with proper optimization"
}}

**IMPORTANT:**
- Be SPECIFIC (don't say "add more content", say "add 800-word section on X with Y examples")
- Base analysis on ACTUAL search results, not assumptions
- Prioritize actions by impact vs effort
- Consider both content AND technical SEO"""

        try:
            # Call Claude with extended thinking for deep analysis
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
                thinking={
                    "type": "enabled",
                    "budget_tokens": 5000  # Give Claude time to think deeply
                }
            )

            # Extract response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Parse JSON
            response_text = response_text.replace("```json", "").replace("```", "").strip()

            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse competitive analysis JSON")

            # Add metadata
            analysis['keyword'] = target_keyword
            analysis['analyzed_at'] = self._get_timestamp()

            return analysis

        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    def generate_improvement_brief(self, gap_analysis: Dict) -> str:
        """
        Generate a clear, actionable brief for content improvement based on gap analysis.

        This is what gets passed to the content generator to guide the rewrite.

        Args:
            gap_analysis: Output from analyze_competitive_gap()

        Returns:
            Formatted brief string for content generator
        """

        brief = f"""# COMPETITIVE IMPROVEMENT BRIEF

**Target Keyword:** {gap_analysis.get('keyword', 'N/A')}
**Search Intent:** {gap_analysis.get('search_intent', 'N/A')}
**Recommended Format:** {gap_analysis.get('content_format_recommendation', 'N/A')}
**Target Word Count:** {gap_analysis.get('target_word_count', 2000):,} words

## CRITICAL GAPS TO FILL:

### Missing Topics (MUST INCLUDE):
"""

        for topic in gap_analysis.get('missing_topics', [])[:10]:
            brief += f"- {topic}\n"

        brief += "\n### Questions to Answer:\n"
        for question in gap_analysis.get('missing_questions', [])[:10]:
            brief += f"- {question}\n"

        brief += f"\n## TOP RANKING PATTERNS:\n"
        for pattern in gap_analysis.get('top_ranking_patterns', [])[:5]:
            brief += f"- {pattern}\n"

        brief += "\n## CONTENT STRUCTURE:\n"
        brief += f"- Format: {gap_analysis.get('content_format_recommendation', 'comprehensive guide')}\n"
        brief += f"- Target Length: {gap_analysis.get('target_word_count', 2000):,} words\n"

        if gap_analysis.get('multimedia_needed'):
            brief += "\n### Multimedia Elements Needed:\n"
            for media in gap_analysis.get('multimedia_needed', [])[:5]:
                brief += f"- {media}\n"

        if gap_analysis.get('featured_snippet_opportunity', {}).get('possible'):
            snippet = gap_analysis['featured_snippet_opportunity']
            brief += f"\n## FEATURED SNIPPET OPPORTUNITY:\n"
            brief += f"- Format: {snippet.get('format', 'N/A')}\n"
            brief += f"- Target Question: {snippet.get('target_question', 'N/A')}\n"
            brief += f"- Optimization: {snippet.get('how_to_optimize', 'N/A')}\n"

        brief += "\n## UNIQUE ANGLES (Differentiate from competitors):\n"
        for angle in gap_analysis.get('unique_opportunities', [])[:5]:
            brief += f"- {angle}\n"

        brief += "\n## PRIORITY ACTIONS:\n"
        high_priority = [a for a in gap_analysis.get('action_plan', []) if a.get('priority') == 'high']
        for i, action in enumerate(high_priority[:10], 1):
            brief += f"{i}. **{action.get('action', 'N/A')}**\n"
            brief += f"   Why: {action.get('why', 'N/A')}\n"
            brief += f"   Impact: {action.get('estimated_impact', 'N/A')}\n\n"

        if gap_analysis.get('schema_opportunities'):
            brief += "## SCHEMA MARKUP TO ADD:\n"
            for schema in gap_analysis.get('schema_opportunities', [])[:3]:
                brief += f"- {schema}\n"

        brief += f"\n## EXPECTED RESULTS:\n"
        brief += f"- Ranking Improvement: {gap_analysis.get('estimated_ranking_improvement', 'N/A')}\n"
        brief += f"- Time to Rank: {gap_analysis.get('estimated_time_to_rank', 'N/A')}\n"

        return brief

    @staticmethod
    def _get_timestamp():
        from datetime import datetime
        return datetime.now().isoformat()


if __name__ == "__main__":
    # Test
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY env var to test")
        exit(1)

    analyzer = CompetitiveAnalyzer(api_key)

    print("Testing competitive analysis...")
    print("=" * 80)

    result = analyzer.analyze_competitive_gap(
        target_keyword="best cast iron griddle",
        your_current_content="A short guide about cast iron griddles with basic info...",
        your_current_position=15,
        impressions=5000,
        clicks=150,
        engagement_data={
            'bounce_rate': 75,
            'avg_time': 45,
            'engagement_rate': 0.25
        }
    )

    print(json.dumps(result, indent=2))
    print("\n" + "=" * 80)
    print("IMPROVEMENT BRIEF:")
    print("=" * 80)
    print(analyzer.generate_improvement_brief(result))
