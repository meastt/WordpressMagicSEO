import logging
import os
from typing import List
import anthropic

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
        else:
            self.logger.warning("No Anthropic API Key found. Optimizer running in MOCK mode.")
            self.client = None
        
        # Updated to Sonnet 4.5 (Released Sep 2025)
        self.model = "claude-sonnet-4-5-20250929"

    def _call_claude(self, system: str, user_prompt: str) -> str:
        """Helper to call Claude API."""
        if not self.client:
            return "MOCK_RESPONSE: API Key missing."
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return message.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API Error: {e}")
            return f"ERROR: {e}"

    def rewrite_title(self, current_title: str, target_keyword: str) -> str:
        """
        Rewrites a page title to improve CTR and include the target keyword.
        """
        system = "You are an expert SEO Copywriter. You write catchy, high-CTR titles that are under 60 characters."
        prompt = (
            f"Rewrite this blog post title to improve Click-Through Rate (CTR). "
            f"MUST include the keyword '{target_keyword}'. "
            f"Keep it under 60 characters. "
            f"Current Title: '{current_title}'\n"
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
