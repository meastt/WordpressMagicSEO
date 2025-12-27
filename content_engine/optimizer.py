import logging
import os
from urllib.parse import urlparse
from typing import List, Optional

import anthropic
import markdown
from analysis.competitive_analyzer import CompetitiveAnalyzer

class ContentOptimizer:
    """
    The 'Writer' of the AI Content Engine.
    Responsible for text-based improvements driven by strategy.
    Uses Anthropic (Claude 3.5 Sonnet) for high-quality generation.
    """
    
    def __init__(self, api_key=None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.analyzer = CompetitiveAnalyzer(api_key=self.api_key)
        else:
            self.logger.warning("No Anthropic API Key found. Optimizer running in MOCK mode.")
            self.client = None
            self.analyzer = None
        
        # Updated to Sonnet 4.5
        self.model = "claude-sonnet-4-5-20250929"

    def _call_claude(self, system: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """Helper to call Claude API."""
        if not self.client:
            return "MOCK_RESPONSE: API Key missing."
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return message.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API Error: {e}")
            return f"ERROR: {e}"

    def rewrite_title(self, current_title: str, target_keyword: str, competitive_brief: Optional[str] = None) -> str:
        """
        Rewrites a page title to improve CTR and include the target keyword.
        """
        context_str = f"\nCompetitive Analysis Context:\n{competitive_brief}" if competitive_brief else ""
        system = "You are an expert SEO Copywriter. You write catchy, high-CTR titles that are under 60 characters."
        prompt = (
            f"Rewrite this blog post title to improve Click-Through Rate (CTR). "
            f"Current Date: December 2025 (Use 2026 for early-access guides if appropriate). "
            f"MUST include the keyword '{target_keyword}'. "
            f"Keep it under 60 characters. "
            f"Current Title: '{current_title}'\n"
            f"{context_str}\n"
            f"Return ONLY the new title text, no quotes or explanations."
        )
        
        self.logger.info(f"Optimizing title: {current_title}")
        return self._call_claude(system, prompt)

    def generate_comparison_table(self, topic: str, products: List[str]) -> str:
        """
        Generates a Markdown comparison table for a list of products.
        """
        product_list = ", ".join(products)
        system = "You are a specialized Product Review Editor. You verify specs and create accurate comparison tables."
        prompt = (
            f"Create a Markdown comparison table for the following {topic}: {product_list}. "
            f"Columns: Product Name, Key Feature (2-3 words), Rating (1-5), Price Range ($-$$$$). "
            f"Ensure to mention specific unique features for each. Return ONLY the Markdown table."
        )
        
        self.logger.info(f"Generating table for: {topic}")
        return self._call_claude(system, prompt)

    def expand_section(self, heading: str, context_points: List[str]) -> str:
        """
        Writes a comprehensive paragraph for a specific heading.
        """
        context = "\n- ".join(context_points)
        system = "You are an expert Outdoor Cooking Writer. Your tone is helpful, authoritative, and enthusiastic."
        prompt = (
            f"Write a content section for the heading: '{heading}'. "
            f"Use these context points:\n- {context}\n"
            f"Write in short, readable paragraphs. Use bolding for key terms. Return ONLY the content."
        )
        
        self.logger.info(f"Expanding section: {heading}")
        return self._call_claude(system, prompt)

    def smart_fusion(self, original_html: str, competitive_brief: str, table_md: str) -> str:
        """
        Performs a semantic fusion of original content with strategic insights.
        Returns a complete, optimized HTML body.
        """
        system = (
            "You are a Senior SEO Content Editor. Your job is to 'fuse' a blog post with competitive intelligence. "
            "You MUST keep the original author's authentic voice and key stories, but improve the structure, "
            "add missing facts from the brief, and integrate a comparison table naturally. "
            "Output valid HTML that is compatible with the WordPress Block Editor."
        )
        prompt = (
            f"Current Date: December 2025. This post MUST be framed as a '2026 Guide'.\n\n"
            f"Original Content (HTML):\n{original_html}\n\n"
            f"Competitive Analysis Brief:\n{competitive_brief}\n\n"
            f"Comparison Table (Markdown):\n{table_md}\n\n"
            "INSTRUCTIONS:\n"
            "1. Rewrite the content to be comprehensive but CONCISE. Prioritize signal over noise.\n"
            "2. Integrate the comparison table where it makes the most sense (not just at the bottom).\n"
            "3. Use ONLY <h2> and <h3> tags for a better hierarchy. NEVER use <h1> as the theme renders it automatically.\n"
            "4. NEVER repeat the main post title at the beginning of your response. Start directly with the intro paragraph.\n"
            "5. Ensure the first paragraph is punchy and includes the target keyword early.\n"
            "6. All year references MUST be 2026.\n"
            "7. **CRITICAL**: You MUST finish the article. If you are approaching your output limit, wrap up the current point quickly and provide a proper 'Conclusion' section. NEVER leave a sentence unfinished.\n"
            "8. Return ONLY raw HTML content. DO NOT use markdown code fences."
        )
        
        self.logger.info("🔥 Performing Full-Body Smart Fusion (High-Token Mode)...")
        raw_output = self._call_claude(system, prompt, max_tokens=8192)
        
        # 🛡️ Truncation Safeguard: Detect incomplete articles and generate a proper conclusion
        stripped = raw_output.rstrip()
        
        # Check if the article has a proper ending (conclusion section or final verdict)
        has_conclusion = any(term in stripped.lower() for term in [
            'final verdict', 'conclusion', 'closing thoughts', 'bottom line', 
            'the winner is', 'my recommendation', 'in summary'
        ])
        
        # Also check if it ends mid-sentence (no proper punctuation before closing tag)
        ends_properly = stripped.endswith(('>', '.', '!', '?'))
        
        if not has_conclusion or not ends_properly:
            self.logger.warning("⚠️ Article appears truncated. Generating conclusion section...")
            
            # Trim to last complete sentence first
            import re
            last_period_tag = stripped.rfind('.</p>')
            last_period = stripped.rfind('. ')
            cut_point = max(last_period_tag, last_period)
            if cut_point > len(stripped) // 2:
                if last_period_tag > last_period:
                    raw_output = stripped[:last_period_tag + 5]  # Include </p>
                else:
                    raw_output = stripped[:last_period + 1]
            
            # Generate a proper conclusion section
            conclusion_prompt = (
                f"The following article about '{competitive_brief[:100]}...' was cut short. "
                f"Write ONLY a brief, satisfying conclusion section (2-3 paragraphs max) that:\n"
                f"1. Starts with an <h2>Final Verdict</h2> or similar\n"
                f"2. Summarizes the key takeaway (which cut is best for what use case)\n"
                f"3. Ends with a call-to-action or encouragement to try both\n"
                f"Return ONLY raw HTML. NO markdown fences."
            )
            conclusion = self._call_claude(
                "You are a food blogger wrapping up an article. Be warm, helpful, and concise.",
                conclusion_prompt,
                max_tokens=800
            )
            
            # Clean the conclusion
            conclusion = re.sub(r'```(?:html)?', '', conclusion).replace('```', '').strip()
            
            raw_output = raw_output + "\n\n" + conclusion
            self.logger.info("✅ Conclusion section added successfully.")
        
        return raw_output
