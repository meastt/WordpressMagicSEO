import logging
import json
from typing import List, Dict, Optional

class TaxonomyManager:
    """
    The 'Librarian' of the AI Content Engine.
    Responsible for categories, tags, and internal linking structure.
    """

    def __init__(self, llm_client=None):
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client

    def suggest_categories(self, content_summary: str, existing_categories: List[str]) -> List[str]:
        """
        Selects the best fitting categories from the existing list using Claude.
        """
        if not self.llm_client:
            return ["Uncategorized"]

        categories_str = ", ".join(existing_categories)
        system = "You are a WordPress Content Strategist. Select 1 or 2 most relevant categories."
        prompt = (
            f"Given this content summary: '{content_summary}'\n"
            f"And these existing categories: {categories_str}\n"
            f"Select the 1-2 most relevant categories. Return ONLY a JSON list of category names."
        )

        try:
            response = self.llm_client._call_claude(system, prompt)
            # Find JSON in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            return [existing_categories[0]] if existing_categories else ["Uncategorized"]
        except Exception as e:
            self.logger.error(f"Error suggesting categories: {e}")
            return ["Uncategorized"]

    def generate_tags(self, content_summary: str) -> List[str]:
        """
        Generates relevant SEO tags using Claude.
        """
        if not self.llm_client:
            return ["Grilling"]

        system = "You are an SEO Expert. Generate relevant WordPress tags (3-5 max)."
        prompt = (
            f"Generate 3-5 high-traffic WordPress tags for this content: '{content_summary}'\n"
            f"Return ONLY a JSON list of strings."
        )

        try:
            response = self.llm_client._call_claude(system, prompt)
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            return ["Cooking", "Griddle"]
        except Exception as e:
            self.logger.error(f"Error generating tags: {e}")
            return ["Grilling"]

    def suggest_internal_links(self, content_summary: str, pillar_pages: List[Dict]) -> List[Dict]:
        """
        Identifies relevant pillar pages to link to within the content.
        """
        self.logger.info("Finding internal link opportunities...")
        # Mock logic: returns list of {url, anchor_text}
        return [
            {"url": "https://griddleking.com/best-cast-iron/", "anchor_text": "best cast iron guide"}
        ]
