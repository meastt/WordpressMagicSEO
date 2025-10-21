"""
AI Strategic Planner - Intelligent Action Prioritization
========================================================

Replaces hard-coded rules with AI-powered strategic planning.
Uses Claude to analyze GSC+GA4 data combined with niche intelligence
to create prioritized action plans with data-driven reasoning.

Key Features:
- Considers niche trends + current performance data
- Analyzes intent matching (GSC traffic vs GA4 engagement)
- Identifies competitive gaps and opportunities
- Calculates ROI (impressions × engagement × trend alignment)
- Provides specific reasoning for each action
"""

import anthropic
import pandas as pd
import json
from typing import Dict, List, Optional


class AIStrategicPlanner:
    """
    AI-powered strategic planner for SEO content actions.
    
    Uses Claude to create intelligent, prioritized action plans based on:
    - GSC + GA4 merged data (search performance + user behavior)
    - Niche research insights (trends, competitors, opportunities)
    - Completed actions history (avoid duplication)
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the AI Strategic Planner.
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use (default: claude-sonnet-4-20250514)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def create_plan(
        self, 
        site_config: Dict,
        merged_data: pd.DataFrame,
        niche_report: Dict,
        completed_actions: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Create AI-powered strategic action plan.
        
        Analyzes all available data to generate a prioritized list of actions
        (update, create, delete, redirect) with specific reasoning for each.
        
        Args:
            site_config: Site configuration dict with keys: url, niche, etc.
            merged_data: Pandas DataFrame with GSC + GA4 merged data
            niche_report: Dictionary from NicheAnalyzer.research_niche()
            completed_actions: List of already completed actions (to avoid duplication)
        
        Returns:
            List of action dictionaries with keys:
                - id: Unique action identifier (e.g., "action_001")
                - action_type: "update", "create", "delete", or "redirect"
                - url: Target URL (for update/delete) or None (for create)
                - title: Suggested title
                - keywords: List of target keywords
                - priority_score: Float 0-10 (10 = highest priority)
                - reasoning: Specific explanation based on data + trends
                - estimated_impact: "high", "medium", or "low"
                - redirect_target: URL to redirect to (if action_type="redirect")
        
        Example:
            planner = AIStrategicPlanner(api_key)
            actions = planner.create_plan(
                site_config={'url': 'https://example.com', 'niche': 'cooking'},
                merged_data=df,
                niche_report=report,
                completed_actions=[]
            )
        """
        
        if completed_actions is None:
            completed_actions = []
        
        # Prepare data summaries for AI
        gsc_summary = self._summarize_gsc(merged_data)
        ga4_summary = self._summarize_ga4(merged_data)
        completed_urls = [a.get('url') for a in completed_actions if a.get('url')]

        # Add current date context for year-aware recommendations
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.strftime('%B')

        # Build comprehensive prompt
        prompt = f"""You're an SEO strategist for {site_config['url']}.

**CURRENT DATE CONTEXT:**
Today is {current_date.strftime('%B %d, %Y')}
Current Year: {current_year}
Current Month: {current_month}

**CRITICAL: Content Freshness Rules**
- ALWAYS use {current_year} in titles for "Best", "Top", or time-sensitive content
- Flag any titles with old years (e.g., "Best X 2023", "Top Y 2024") as HIGH PRIORITY updates
- Titles should be: "Best X {current_year}", "Top Y for {current_year}"
- Content last updated >12 months ago needs freshness update
- Seasonal content should align with upcoming seasons

**NICHE:** {site_config['niche']}

**NICHE RESEARCH:**
{json.dumps(niche_report, indent=2)}

**GSC DATA (Last 12 months):**
{gsc_summary}

**GA4 ENGAGEMENT DATA:**
{ga4_summary}

**COMPLETED ACTIONS (don't repeat these URLs):**
{json.dumps(completed_urls, indent=2)}

---

**YOUR TASK:**
Create a prioritized content action plan with 20-30 actions.

**ACTION TYPES:**
1. **update** - Refresh existing content (fix intent mismatch, add trending info, improve quality)
2. **create** - New content for trending topics or gaps
3. **delete** - Remove low-value content (cannibalization, outdated, thin)
4. **redirect** - Consolidate duplicate/similar content

**PRIORITIZATION CRITERIA:**
- **Business Impact** = (impressions × engagement_rate × trend_alignment)
- **Urgency** = Is this topic trending NOW?
- **Effort vs Return** = Quick wins vs major projects
- **Strategic Fit** = Aligns with niche opportunities?

**ANALYSIS FRAMEWORK:**

1. **Intent Mismatches** (HIGH PRIORITY)
   - High GSC traffic + Low GA4 engagement = Content doesn't match search intent
   - Example: 10K impressions, 500 clicks, but 90% bounce rate → REWRITE

2. **Hidden Gems** (HIGH PRIORITY)
   - High GA4 engagement + Low GSC visibility = Great content, poor SEO
   - Example: 85% engagement, 300s avg time, but position #42 → OPTIMIZE SEO

3. **Trending Opportunities** (HIGH PRIORITY)
   - Topics from niche research growing +30%+ YoY
   - Competitor gaps we can fill
   - Low competition, high volume keywords

4. **Quality Issues** (MEDIUM PRIORITY)
   - High bounce rate (>70%) = UX or content quality problem
   - Low engagement time (<30s) = Thin/unhelpful content

5. **Cannibalization & Duplicate Content** (MEDIUM-HIGH PRIORITY)
   - Multiple pages targeting same keywords
   - **SEMANTIC DUPLICATES:** Pages about same topic with different titles/years
     * Example: "Best Griddles 2023" and "Top Griddles 2024" are DUPLICATES
     * Consolidate to single updated page with current year
   - Look for URL patterns: same topic, different years (redirect old → new)
   - Multiple "best X" or "top X" guides for same product category
   - Consolidate into one strong, updated page

6. **Outdated Content** (HIGH PRIORITY for year updates, otherwise MEDIUM)
   - Topics declining in niche research
   - Low impressions + low engagement
   - **CRITICAL:** Titles with old years (e.g., "Best X 2023") → Update to {current_year}
   - Content not updated in last 12 months
   - Seasonal content out of season

**OUTPUT FORMAT:**
Return a JSON array of 20-30 actions, sorted by priority_score (10 = most critical).

[
  {{
    "id": "action_001",
    "action_type": "update",
    "url": "https://example.com/best-griddles-2024",
    "title": "Best Griddles {current_year}",
    "keywords": ["best griddles {current_year}", "top griddles", "griddle reviews"],
    "priority_score": 9.8,
    "reasoning": "OUTDATED TITLE: Currently 'Best Griddles 2024' but it's {current_year}. High traffic (5K impressions, 250 clicks) but title year is stale. Update title and content to {current_year} immediately. Add latest {current_year} product releases. This is a quick win for maintaining rankings.",
    "estimated_impact": "high",
    "redirect_target": null
  }},
  {{
    "id": "action_002",
    "action_type": "update",
    "url": "https://example.com/page-url",
    "title": "Suggested Title for {current_year}",
    "keywords": ["primary keyword", "secondary keyword", "tertiary keyword"],
    "priority_score": 9.5,
    "reasoning": "High traffic (10K impressions, 500 clicks, position #2) but terrible engagement (90% bounce, 12s avg time). Content likely doesn't match search intent. Rewrite to focus on product comparisons instead of general info. Aligns with 'comparison content +45%' trend from niche research.",
    "estimated_impact": "high",
    "redirect_target": null
  }},
  {{
    "id": "action_003",
    "action_type": "create",
    "url": null,
    "title": "Cast Iron Griddle Seasoning Complete Guide {current_year}",
    "keywords": ["cast iron griddle seasoning", "how to season cast iron griddle", "griddle seasoning tips"],
    "priority_score": 9.2,
    "reasoning": "Major gap identified in niche research: 'Cast iron maintenance guides - 5K monthly searches, low competition'. No existing content on site. Highly engaged niche (from competitor analysis). Quick win opportunity.",
    "estimated_impact": "high",
    "redirect_target": null
  }},
  {{
    "id": "action_004",
    "action_type": "redirect",
    "url": "https://example.com/best-griddles-2023",
    "title": null,
    "keywords": [],
    "priority_score": 8.0,
    "reasoning": "Old year version (2023) competing with current {current_year} version. Consolidate to avoid keyword cannibalization and maintain authority on single updated page. Redirect to /best-griddles-{current_year}.",
    "estimated_impact": "high",
    "redirect_target": "https://example.com/best-griddles-{current_year}"
  }}
]

**IMPORTANT:**
- Be SPECIFIC in reasoning (cite exact numbers from data)
- Consider BOTH search performance (GSC) AND user behavior (GA4)
- Align with niche trends (reference specific trends)
- **CRITICAL:** Check ALL titles for old years - flag for immediate update to {current_year}
- Look for patterns like "2023", "2024" in URLs/titles - these need year updates
- Provide 20-30 diverse actions (mix of updates, creates, deletes, redirects)
- Prioritize year updates as HIGH PRIORITY (score 8.0+)
- Return ONLY the JSON array, no other text"""

        try:
            # Call Claude for strategic analysis
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract response
            response_text = message.content[0].text.strip()
            
            # Clean up markdown
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            try:
                actions = json.loads(response_text)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    actions = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response: {e}")
            
            # Validate and normalize actions
            for action in actions:
                # Ensure required fields
                if 'id' not in action:
                    action['id'] = f"action_{len(actions)}"
                if 'action_type' not in action:
                    action['action_type'] = 'update'
                if 'priority_score' not in action:
                    action['priority_score'] = 5.0
                if 'estimated_impact' not in action:
                    action['estimated_impact'] = 'medium'
                if 'reasoning' not in action:
                    action['reasoning'] = 'No reasoning provided'
                if 'keywords' not in action:
                    action['keywords'] = []
                if 'title' not in action:
                    action['title'] = 'Untitled'
                
                # Set default status
                action['status'] = 'pending'
                
                # Ensure redirect_target for redirect actions
                if action['action_type'] == 'redirect' and 'redirect_target' not in action:
                    action['redirect_target'] = None
            
            # Sort by priority
            actions.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
            
            return actions
            
        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Strategic planning failed: {str(e)}")
    
    def _summarize_gsc(self, df: pd.DataFrame, top_n: int = 50) -> str:
        """
        Summarize GSC data for AI prompt.
        
        Args:
            df: Merged DataFrame with GSC data
            top_n: Number of top pages to include
        
        Returns:
            Formatted text summary
        """
        try:
            # Group by page and aggregate
            by_page = df.groupby('page').agg({
                'impressions': 'sum',
                'clicks': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # Get top pages by impressions
            by_page = by_page.nlargest(top_n, 'impressions')
            
            # Format summary
            lines = ["Top performing pages by impressions:\n"]
            for _, row in by_page.iterrows():
                lines.append(
                    f"- {row['page']}: "
                    f"{int(row['impressions'])} impressions, "
                    f"{int(row['clicks'])} clicks, "
                    f"{row['ctr']:.2%} CTR, "
                    f"position {row['position']:.1f}"
                )
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error summarizing GSC data: {e}"
    
    def _summarize_ga4(self, df: pd.DataFrame, top_n: int = 50) -> str:
        """
        Summarize GA4 engagement data for AI prompt.
        
        Args:
            df: Merged DataFrame with GA4 data
            top_n: Number of top pages to include
        
        Returns:
            Formatted text summary
        """
        try:
            # Check if GA4 columns exist
            ga4_cols = ['engagement_rate', 'avg_engagement_time', 'bounce_rate', 'sessions']
            has_ga4 = any(col in df.columns for col in ga4_cols)
            
            if not has_ga4:
                return "No GA4 data available"
            
            # Get unique pages with GA4 data
            ga4_data = df[['page'] + [col for col in ga4_cols if col in df.columns]].copy()
            ga4_data = ga4_data.drop_duplicates('page').dropna(subset=['engagement_rate'] if 'engagement_rate' in ga4_data.columns else [])
            
            # Sort by engagement rate if available
            if 'engagement_rate' in ga4_data.columns:
                ga4_data = ga4_data.nlargest(top_n, 'engagement_rate')
            else:
                ga4_data = ga4_data.head(top_n)
            
            # Format summary
            lines = ["Engagement metrics:\n"]
            for _, row in ga4_data.iterrows():
                parts = [f"- {row['page']}:"]
                
                if 'engagement_rate' in row and not pd.isna(row['engagement_rate']):
                    parts.append(f"{row['engagement_rate']:.1%} engaged")
                
                if 'avg_engagement_time' in row and not pd.isna(row['avg_engagement_time']):
                    parts.append(f"{row['avg_engagement_time']:.0f}s avg time")
                
                if 'bounce_rate' in row and not pd.isna(row['bounce_rate']):
                    parts.append(f"{row['bounce_rate']:.1%} bounce")
                
                if 'sessions' in row and not pd.isna(row['sessions']):
                    parts.append(f"{int(row['sessions'])} sessions")
                
                lines.append(" ".join(parts))
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error summarizing GA4 data: {e}"
    
    def format_plan_summary(self, actions: List[Dict]) -> str:
        """
        Format action plan as human-readable summary.
        
        Args:
            actions: List of action dictionaries from create_plan()
        
        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("=" * 80)
        lines.append("AI STRATEGIC ACTION PLAN")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary stats
        total = len(actions)
        by_type = {}
        by_impact = {}
        
        for action in actions:
            action_type = action.get('action_type', 'unknown')
            by_type[action_type] = by_type.get(action_type, 0) + 1
            
            impact = action.get('estimated_impact', 'medium')
            by_impact[impact] = by_impact.get(impact, 0) + 1
        
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total actions: {total}")
        lines.append(f"By type: {', '.join(f'{k}={v}' for k, v in by_type.items())}")
        lines.append(f"By impact: {', '.join(f'{k}={v}' for k, v in by_impact.items())}")
        lines.append("")
        
        # Top 10 priority actions
        lines.append("TOP 10 PRIORITY ACTIONS")
        lines.append("-" * 80)
        
        for i, action in enumerate(actions[:10], 1):
            lines.append(f"\n{i}. [{action['action_type'].upper()}] {action.get('title', action.get('url', 'Untitled'))}")
            lines.append(f"   Score: {action['priority_score']:.1f}/10 | Impact: {action['estimated_impact']}")
            lines.append(f"   Keywords: {', '.join(action.get('keywords', [])[:3])}")
            lines.append(f"   Reasoning: {action['reasoning'][:200]}...")
            if action.get('url'):
                lines.append(f"   URL: {action['url']}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


def test_ai_planner():
    """
    Test function for AIStrategicPlanner.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    import os
    import pandas as pd
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        return False
    
    print("🎯 Testing AI Strategic Planner...")
    print("=" * 80)
    
    try:
        # Create sample data
        sample_data = {
            'page': [
                'https://example.com/best-griddles',
                'https://example.com/cast-iron-guide',
                'https://example.com/outdoor-cooking-tips'
            ],
            'query': ['best griddles', 'cast iron griddle', 'outdoor cooking'],
            'impressions': [10000, 500, 2000],
            'clicks': [500, 50, 100],
            'ctr': [0.05, 0.10, 0.05],
            'position': [2.5, 42.0, 15.0],
            'sessions': [400, 45, 80],
            'engagement_rate': [0.35, 0.85, 0.60],
            'avg_engagement_time': [45, 280, 120],
            'bounce_rate': [0.65, 0.15, 0.40]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Sample niche report
        niche_report = {
            'summary': 'Outdoor cooking niche growing 25% YoY with focus on electric and portable options',
            'trends': [
                'Electric griddles up 45% in search volume',
                'Portable cooking equipment trending for camping'
            ],
            'competitors': [
                'seriouseats.com - Dominates with detailed testing and reviews',
                'outdoorcookingpro.com - Strong in how-to guides'
            ],
            'opportunities': [
                'Cast iron maintenance guides - 5K monthly searches, low competition',
                'Griddle comparison charts - High engagement potential'
            ],
            'content_formats': [
                'Video comparisons get 3x more engagement',
                'Step-by-step guides with photos perform well'
            ],
            'keywords_trending': [
                'electric griddle for camping - +60% YoY',
                'portable griddle reviews - +40% YoY'
            ]
        }
        
        # Initialize planner
        planner = AIStrategicPlanner(api_key)
        print("✓ AIStrategicPlanner initialized")
        
        # Create plan
        print("\n📊 Creating strategic action plan...")
        actions = planner.create_plan(
            site_config={'url': 'https://example.com', 'niche': 'outdoor cooking'},
            merged_data=df,
            niche_report=niche_report,
            completed_actions=[]
        )
        print(f"✓ Generated {len(actions)} actions")
        
        # Display summary
        print("\n" + planner.format_plan_summary(actions))
        
        # Validate structure
        assert len(actions) > 0, "No actions generated"
        assert all('id' in a for a in actions), "Missing action IDs"
        assert all('priority_score' in a for a in actions), "Missing priority scores"
        print("\n✅ All tests passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_ai_planner()
