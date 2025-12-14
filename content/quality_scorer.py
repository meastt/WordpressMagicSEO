"""
content_quality_scorer.py
==========================
AI-powered content quality analysis that scores content like Google's algorithms would.

Analyzes E-E-A-T signals, comprehensiveness, readability, user value, and technical SEO.
"""

import anthropic
from typing import Dict, List, Optional
import json
import re
from datetime import datetime


class ContentQualityScorer:
    """
    Comprehensive content quality analysis using AI to evaluate:

    1. **E-E-A-T Signals** (Experience, Expertise, Authoritativeness, Trust)
    2. **Comprehensiveness** (topic coverage depth)
    3. **Readability** (structure, formatting, scannability)
    4. **User Value** (does it actually help the user?)
    5. **Technical SEO** (meta tags, schema, images, etc.)
    6. **Freshness** (up-to-date information)
    7. **Engagement Potential** (likely to keep users on page)

    Returns actionable improvement recommendations.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def score_content_quality(
        self,
        content: str,
        meta_title: str = "",
        meta_description: str = "",
        target_keywords: List[str] = None,
        url: str = "",
        engagement_data: Optional[Dict] = None
    ) -> Dict:
        """
        Comprehensive AI-powered content quality analysis.

        Args:
            content: The full HTML or plain text content
            meta_title: SEO title tag
            meta_description: SEO meta description
            target_keywords: List of target keywords
            url: Page URL
            engagement_data: Optional dict with bounce_rate, avg_time, etc.

        Returns:
            Dictionary with scores, issues, and recommendations
        """

        if target_keywords is None:
            target_keywords = []

        # Calculate basic stats
        word_count = len(content.split())
        has_images = '<img' in content or '[image]' in content.lower()
        has_lists = '<ul>' in content or '<ol>' in content or '<li>' in content
        has_tables = '<table>' in content
        has_headings = '<h2>' in content or '<h3>' in content or '##' in content

        # Prepare engagement context
        engagement_context = ""
        if engagement_data:
            engagement_context = f"""
**ENGAGEMENT METRICS:**
- Bounce Rate: {engagement_data.get('bounce_rate', 'N/A')}%
- Avg Time on Page: {engagement_data.get('avg_time', 'N/A')}s
- Pages per Session: {engagement_data.get('pages_per_session', 'N/A')}
- Engagement Rate: {engagement_data.get('engagement_rate', 'N/A')}%

**ENGAGEMENT BENCHMARKS:**
- Good bounce rate: <50%
- Good time on page: >2 minutes
- Good engagement rate: >60%
"""

        # Extract preview
        content_preview = content[:4000]

        prompt = f"""You are a content quality analyst and SEO expert. Evaluate this content comprehensively.

**TARGET KEYWORDS:** {', '.join(target_keywords) if target_keywords else 'None specified'}
**URL:** {url}
**META TITLE:** {meta_title or 'Not set'}
**META DESCRIPTION:** {meta_description or 'Not set'}

**CONTENT PREVIEW:**
{content_preview}

**BASIC STATS:**
- Word Count: {word_count}
- Has Images: {has_images}
- Has Lists: {has_lists}
- Has Tables: {has_tables}
- Has Headings: {has_headings}
{engagement_context}

---

**ANALYZE THE FOLLOWING:**

## 1. E-E-A-T SIGNALS (Experience, Expertise, Authoritativeness, Trustworthiness)
- Does content show real experience/expertise?
- Are there specific examples, data, case studies?
- Is author expertise demonstrated?
- Are sources cited?
- Is information accurate and trustworthy?
- Score: 0-10

## 2. COMPREHENSIVENESS
- Does it thoroughly cover the topic?
- Are there obvious gaps or missing subtopics?
- Does it answer all related questions a user might have?
- Is depth appropriate for topic?
- Score: 0-10

## 3. READABILITY & STRUCTURE
- Is content well-structured with headings?
- Are paragraphs short and scannable?
- Are there formatting elements (lists, bold, etc.)?
- Is writing clear and easy to understand?
- Score: 0-10

## 4. USER VALUE
- Does this ACTUALLY help the user accomplish their goal?
- Is it actionable (not just theory)?
- Does it provide unique insights?
- Would user recommend this to others?
- Score: 0-10

## 5. TECHNICAL SEO
- Are meta title/description optimized?
- Are keywords naturally integrated?
- Are headings properly structured (H2, H3)?
- Are images optimized (if present)?
- Score: 0-10

## 6. FRESHNESS
- Does content feel current and up-to-date?
- Are there dates, recent examples?
- Is information still accurate?
- Score: 0-10

## 7. ENGAGEMENT POTENTIAL
- Is content engaging to read?
- Does it encourage further exploration?
- Are there calls-to-action or next steps?
- If engagement metrics are poor, why?
- Score: 0-10

---

Return JSON:

{{
  "overall_score": 0.0-10.0,
  "scores": {{
    "eeat": 0.0-10.0,
    "comprehensiveness": 0.0-10.0,
    "readability": 0.0-10.0,
    "user_value": 0.0-10.0,
    "technical_seo": 0.0-10.0,
    "freshness": 0.0-10.0,
    "engagement_potential": 0.0-10.0
  }},
  "strengths": [
    "What this content does well",
    "Another strength..."
  ],
  "critical_issues": [
    {{
      "issue": "Specific problem",
      "severity": "high|medium|low",
      "impact": "How this hurts rankings/engagement",
      "fix": "Specific action to fix it"
    }}
  ],
  "missing_elements": [
    "Specific thing to add (e.g., comparison table, FAQ section, etc.)"
  ],
  "engagement_analysis": {{
    "likely_bounce_reasons": [
      "Why users might bounce (if bounce rate is high)"
    ],
    "improvement_suggestions": [
      "Specific ways to improve engagement"
    ]
  }},
  "quick_wins": [
    {{
      "action": "Quick, high-impact improvement",
      "estimated_time": "5 minutes",
      "impact": "Expected result"
    }}
  ],
  "content_grade": "A|B|C|D|F",
  "ranking_potential": "This content could rank in top 10|20|30+ based on quality"
}}

Be SPECIFIC and ACTIONABLE in your recommendations."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=6000,
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

            # Add metadata
            analysis['analyzed_at'] = datetime.now().isoformat()
            analysis['word_count'] = word_count
            analysis['url'] = url

            return analysis

        except Exception as e:
            print(f"Error scoring content quality: {e}")
            return {
                'overall_score': 0.0,
                'error': str(e)
            }

    def get_improvement_priority_list(self, quality_score: Dict) -> List[Dict]:
        """
        Generate prioritized list of improvements to make.

        Takes output from score_content_quality() and returns actionable tasks
        sorted by impact/effort ratio.

        Args:
            quality_score: Output from score_content_quality()

        Returns:
            List of prioritized improvements
        """

        improvements = []

        # Add quick wins (highest priority)
        for quick_win in quality_score.get('quick_wins', []):
            improvements.append({
                'priority': 'immediate',
                'action': quick_win.get('action'),
                'estimated_time': quick_win.get('estimated_time', '15 minutes'),
                'impact': quick_win.get('impact'),
                'category': 'quick_win'
            })

        # Add critical issues
        for issue in quality_score.get('critical_issues', []):
            if issue.get('severity') == 'high':
                improvements.append({
                    'priority': 'high',
                    'action': issue.get('fix'),
                    'issue': issue.get('issue'),
                    'impact': issue.get('impact'),
                    'category': 'critical_fix'
                })

        # Add missing elements
        for missing in quality_score.get('missing_elements', [])[:5]:
            improvements.append({
                'priority': 'medium',
                'action': f"Add: {missing}",
                'category': 'missing_element',
                'impact': 'Improves comprehensiveness and user value'
            })

        # Add engagement improvements
        for suggestion in quality_score.get('engagement_analysis', {}).get('improvement_suggestions', [])[:3]:
            improvements.append({
                'priority': 'medium',
                'action': suggestion,
                'category': 'engagement',
                'impact': 'Reduces bounce rate, increases dwell time'
            })

        return improvements

    def generate_improvement_checklist(self, quality_score: Dict) -> str:
        """
        Generate a readable checklist for content improvement.

        Args:
            quality_score: Output from score_content_quality()

        Returns:
            Formatted checklist string
        """

        checklist = f"""# CONTENT IMPROVEMENT CHECKLIST

**Overall Score:** {quality_score.get('overall_score', 0):.1f}/10 (Grade: {quality_score.get('content_grade', 'N/A')})
**Ranking Potential:** {quality_score.get('ranking_potential', 'Unknown')}

---

## IMMEDIATE ACTIONS (Do First):
"""

        for i, qw in enumerate(quality_score.get('quick_wins', [])[:5], 1):
            checklist += f"\n{i}. [ ] **{qw.get('action')}**\n"
            checklist += f"   ⏱️ Time: {qw.get('estimated_time', '15 min')}\n"
            checklist += f"   📈 Impact: {qw.get('impact')}\n"

        checklist += "\n## CRITICAL FIXES:\n"
        for i, issue in enumerate(quality_score.get('critical_issues', []), 1):
            if issue.get('severity') == 'high':
                checklist += f"\n{i}. [ ] **{issue.get('fix')}**\n"
                checklist += f"   🔴 Issue: {issue.get('issue')}\n"
                checklist += f"   📉 Impact: {issue.get('impact')}\n"

        checklist += "\n## MISSING ELEMENTS TO ADD:\n"
        for i, missing in enumerate(quality_score.get('missing_elements', []), 1):
            checklist += f"{i}. [ ] {missing}\n"

        if quality_score.get('engagement_analysis'):
            checklist += "\n## ENGAGEMENT IMPROVEMENTS:\n"
            for i, suggestion in enumerate(quality_score.get('engagement_analysis', {}).get('improvement_suggestions', []), 1):
                checklist += f"{i}. [ ] {suggestion}\n"

        checklist += "\n---\n"
        checklist += f"\n**Analyzed:** {quality_score.get('analyzed_at', 'N/A')}\n"
        checklist += f"**Word Count:** {quality_score.get('word_count', 0):,}\n"

        return checklist


if __name__ == "__main__":
    # Test
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY to test")
        exit(1)

    scorer = ContentQualityScorer(api_key)

    test_content = """
    <h1>Best Cast Iron Griddles</h1>
    <p>Cast iron griddles are great for cooking. They're durable and heat evenly.</p>
    <p>Here are some options to consider when buying a griddle.</p>
    """

    print("Analyzing content quality...")
    result = scorer.score_content_quality(
        content=test_content,
        meta_title="Best Cast Iron Griddles",
        target_keywords=["cast iron griddle", "best griddles"],
        engagement_data={
            'bounce_rate': 75,
            'avg_time': 45,
            'engagement_rate': 0.25
        }
    )

    print(json.dumps(result, indent=2))
    print("\n" + "="*80)
    print(scorer.generate_improvement_checklist(result))
