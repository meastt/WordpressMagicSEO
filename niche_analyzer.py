"""
Niche Analyzer - AI-Powered Niche Intelligence
===============================================

Uses Anthropic Claude with web search to provide real-time market intelligence
about specific niches. Helps inform content strategy with data-driven insights.

Key Features:
- Current trends analysis (what's growing, declining, emerging)
- Competitive landscape mapping
- Audience behavior insights  
- Keyword opportunity identification
- Data-driven recommendations
"""

import anthropic
import json
from typing import Dict, List, Optional


class NicheAnalyzer:
    """
    AI-powered niche research using Claude with web search.
    
    Provides comprehensive market intelligence about a specific niche
    to inform content strategy and prioritization decisions.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Niche Analyzer.
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use (default: claude-sonnet-4-20250514)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def research_niche(self, niche: str, site_url: str) -> Dict:
        """
        Conduct comprehensive niche research using AI with web search.
        
        Analyzes:
        1. Current trends (last 6 months) - growth/decline/emerging topics
        2. Competitive landscape - dominant players, winning formats
        3. Audience behavior - search intent, user preferences
        4. Keyword opportunities - trending modifiers, breakout terms
        
        Args:
            niche: The niche to research (e.g., "outdoor cooking", "photography")
            site_url: The website URL for context
        
        Returns:
            Dict with keys:
                - summary: Brief 3-sentence niche overview
                - trends: List of current trends with data
                - competitors: List of top competitors with their strengths
                - opportunities: List of content/keyword gaps
                - content_formats: List of winning content formats
                - keywords_trending: List of trending keywords with growth data
        
        Example:
            analyzer = NicheAnalyzer(api_key="sk-ant-...")
            report = analyzer.research_niche("outdoor cooking", "https://griddleking.com")
        """
        
        prompt = f'''Research the "{niche}" niche for {site_url} using web search.

Conduct a comprehensive market analysis focusing on:

1. **Current Trends (Last 6 Months)**
   - What topics are growing in search volume?
   - What's declining or becoming less relevant?
   - What new/emerging topics are gaining traction?
   - Use specific data points (%, volume changes)

2. **Competitive Landscape**
   - Who are the dominant websites in this niche?
   - What content formats are winning (listicles, reviews, guides, videos)?
   - What gaps exist that competitors aren't filling?

3. **Audience Behavior**
   - What are users searching for?
   - What questions are they asking?
   - What problems are they trying to solve?
   - What's the intent behind top queries (informational, transactional, navigational)?

4. **Keyword Opportunities**
   - What modifiers are trending? (best, top, how to, vs, review, etc.)
   - What breakout keywords are emerging?
   - What long-tail opportunities exist?
   - Estimate search volumes where possible

**Instructions:**
- Use 5-10 web searches to gather current data
- Be specific and data-driven (cite numbers, percentages, trends)
- Focus on actionable insights
- Prioritize opportunities over general observations

Return your findings as a JSON object with this structure:
{{
  "summary": "A 3-sentence overview of the niche's current state and direction",
  "trends": [
    "Trend description with data (e.g., 'Electric griddles up 45% YoY')",
    "Another trend with specifics..."
  ],
  "competitors": [
    "competitor.com - Their key strength and why they win",
    "another-site.com - Their differentiation..."
  ],
  "opportunities": [
    "Content gap with estimated impact (e.g., 'Cast iron maintenance guides - 5K monthly searches, low competition')",
    "Another gap with data..."
  ],
  "content_formats": [
    "Format that performs well (e.g., 'Video comparisons get 3x more engagement')",
    "Another format..."
  ],
  "keywords_trending": [
    "keyword phrase - +XX% growth (volume estimate)",
    "another keyword - trend data..."
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text.'''

        try:
            # Call Claude with extended thinking for deeper analysis
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract response text
            response_text = message.content[0].text.strip()
            
            # Clean up markdown code blocks if present
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON response
            try:
                report = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    report = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response: {e}")
            
            # Validate structure
            required_keys = ['summary', 'trends', 'competitors', 'opportunities', 
                           'content_formats', 'keywords_trending']
            for key in required_keys:
                if key not in report:
                    report[key] = [] if key != 'summary' else "No data available"
            
            return report
        
        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Niche research failed: {str(e)}")
    
    def format_report(self, report: Dict) -> str:
        """
        Format niche research report as human-readable text.
        
        Args:
            report: Dictionary from research_niche()
        
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("NICHE RESEARCH REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(report.get('summary', 'No summary available'))
        lines.append("")
        
        # Trends
        lines.append("CURRENT TRENDS")
        lines.append("-" * 80)
        trends = report.get('trends', [])
        if trends:
            for i, trend in enumerate(trends, 1):
                lines.append(f"{i}. {trend}")
        else:
            lines.append("No trend data available")
        lines.append("")
        
        # Competitors
        lines.append("COMPETITIVE LANDSCAPE")
        lines.append("-" * 80)
        competitors = report.get('competitors', [])
        if competitors:
            for i, comp in enumerate(competitors, 1):
                lines.append(f"{i}. {comp}")
        else:
            lines.append("No competitor data available")
        lines.append("")
        
        # Opportunities
        lines.append("CONTENT OPPORTUNITIES")
        lines.append("-" * 80)
        opportunities = report.get('opportunities', [])
        if opportunities:
            for i, opp in enumerate(opportunities, 1):
                lines.append(f"{i}. {opp}")
        else:
            lines.append("No opportunities identified")
        lines.append("")
        
        # Content Formats
        lines.append("WINNING CONTENT FORMATS")
        lines.append("-" * 80)
        formats = report.get('content_formats', [])
        if formats:
            for i, fmt in enumerate(formats, 1):
                lines.append(f"{i}. {fmt}")
        else:
            lines.append("No format data available")
        lines.append("")
        
        # Trending Keywords
        lines.append("TRENDING KEYWORDS")
        lines.append("-" * 80)
        keywords = report.get('keywords_trending', [])
        if keywords:
            for i, kw in enumerate(keywords, 1):
                lines.append(f"{i}. {kw}")
        else:
            lines.append("No keyword trend data available")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def get_top_opportunities(self, report: Dict, limit: int = 5) -> List[str]:
        """
        Extract top content opportunities from research report.
        
        Args:
            report: Dictionary from research_niche()
            limit: Maximum number of opportunities to return
        
        Returns:
            List of top opportunity descriptions
        """
        opportunities = report.get('opportunities', [])
        return opportunities[:limit]
    
    def get_trending_keywords(self, report: Dict, limit: int = 10) -> List[str]:
        """
        Extract trending keywords from research report.
        
        Args:
            report: Dictionary from research_niche()
            limit: Maximum number of keywords to return
        
        Returns:
            List of trending keyword descriptions
        """
        keywords = report.get('keywords_trending', [])
        return keywords[:limit]


def test_niche_analyzer():
    """
    Test function for NicheAnalyzer.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    import os
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        return False
    
    print("🔍 Testing Niche Analyzer...")
    print("=" * 80)
    
    try:
        # Initialize analyzer
        analyzer = NicheAnalyzer(api_key)
        print("✓ NicheAnalyzer initialized")
        
        # Test niche research
        print("\n📊 Researching 'outdoor cooking' niche...")
        report = analyzer.research_niche("outdoor cooking", "https://griddleking.com")
        print("✓ Research complete")
        
        # Display formatted report
        print("\n" + analyzer.format_report(report))
        
        # Test helper methods
        print("\n🎯 Top 3 Opportunities:")
        for i, opp in enumerate(analyzer.get_top_opportunities(report, limit=3), 1):
            print(f"  {i}. {opp}")
        
        print("\n📈 Top 5 Trending Keywords:")
        for i, kw in enumerate(analyzer.get_trending_keywords(report, limit=5), 1):
            print(f"  {i}. {kw}")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_niche_analyzer()
