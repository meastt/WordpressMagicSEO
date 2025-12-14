"""
content_qa_validator.py
=======================
Comprehensive QA validation for generated content to ensure quality and completeness.
"""

import re
from typing import Dict, List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup


class ContentQAValidator:
    """
    Validates generated content for quality, completeness, and contextual appropriateness.
    """

    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []

    def validate_article(
        self,
        article_data: Dict,
        topic_title: str,
        expected_elements: Dict = None
    ) -> Tuple[bool, Dict]:
        """
        Comprehensive validation of generated article content.

        Args:
            article_data: Generated article data with 'content', 'title', etc.
            topic_title: The original topic/title requested
            expected_elements: Dict with expectations like:
                {
                    'min_word_count': 2000,
                    'recipe_count': 15,
                    'image_count': 5,
                    'table_count': 1,
                    'temporal_check': True
                }

        Returns:
            Tuple of (is_valid, validation_report)
        """
        self.errors = []
        self.warnings = []
        self.validation_results = []

        content = article_data.get('content', '')
        title = article_data.get('title', '')

        # 1. Basic content validation
        self._validate_basic_content(content, title)

        # 2. Word count validation
        expected_min_words = expected_elements.get('min_word_count', 2000) if expected_elements else 2000
        self._validate_word_count(content, expected_min_words)

        # 3. Recipe/list completeness validation
        if expected_elements and expected_elements.get('recipe_count'):
            self._validate_recipe_completeness(content, expected_elements['recipe_count'], topic_title)

        # 4. Image placeholder validation
        if expected_elements and expected_elements.get('image_count'):
            self._validate_images(content, expected_elements['image_count'])

        # 5. Table validation
        if expected_elements and expected_elements.get('table_count'):
            self._validate_tables(content, expected_elements['table_count'])

        # 6. Temporal context validation
        if expected_elements and expected_elements.get('temporal_check', True):
            self._validate_temporal_context(content, title)

        # 7. Structure validation
        self._validate_structure(content)

        # 8. SEO metadata validation
        self._validate_seo_metadata(article_data)

        # Compile report
        is_valid = len(self.errors) == 0
        report = {
            'is_valid': is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'validation_results': self.validation_results,
            'summary': self._generate_summary()
        }

        return is_valid, report

    def _validate_basic_content(self, content: str, title: str):
        """Validate basic content requirements."""
        if not content or len(content.strip()) == 0:
            self.errors.append("Content is empty")
        else:
            self.validation_results.append("✅ Content is not empty")

        if not title or len(title.strip()) == 0:
            self.errors.append("Title is empty")
        else:
            self.validation_results.append("✅ Title is present")

    def _validate_word_count(self, content: str, min_word_count: int):
        """Validate minimum word count."""
        # Strip HTML and count words
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        word_count = len(text.split())

        if word_count < min_word_count:
            self.errors.append(
                f"Word count too low: {word_count} words (minimum: {min_word_count})"
            )
        else:
            self.validation_results.append(
                f"✅ Word count sufficient: {word_count} words (minimum: {min_word_count})"
            )

    def _validate_recipe_completeness(self, content: str, expected_count: int, topic_title: str):
        """
        Validate that all promised recipes/items are complete with full content.

        This checks for incomplete recipes that are just headers with no actual content.
        """
        soup = BeautifulSoup(content, 'html.parser')

        # Find all recipe sections (typically H3 headers for individual recipes)
        recipe_headers = soup.find_all(['h3', 'h4'])

        # Filter to likely recipe headers based on numbering or recipe-related keywords
        recipe_keywords = ['recipe', 'dish', 'meal', 'breakfast', 'lunch', 'dinner', 'dessert', 'snack']
        likely_recipes = []

        for header in recipe_headers:
            header_text = header.get_text().lower()
            # Check if it's numbered (1., 2., etc.) or contains recipe keywords
            if (re.match(r'^\d+\.', header_text.strip()) or
                any(keyword in header_text for keyword in recipe_keywords)):
                likely_recipes.append(header)

        found_count = len(likely_recipes)

        if found_count < expected_count:
            self.errors.append(
                f"Recipe count mismatch: Found {found_count} recipe headers, expected {expected_count}"
            )
        else:
            self.validation_results.append(
                f"✅ Recipe count matches: {found_count} recipes found"
            )

        # Check each recipe for completeness
        incomplete_recipes = []
        for i, recipe_header in enumerate(likely_recipes[:expected_count], 1):
            # Get content after this header until the next header
            recipe_content = []
            next_element = recipe_header.find_next_sibling()

            while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                if next_element.name in ['p', 'ul', 'ol', 'div']:
                    recipe_content.append(next_element.get_text())
                next_element = next_element.find_next_sibling()

            # Check if recipe has substantial content (at least 100 chars of actual recipe content)
            content_text = ' '.join(recipe_content).strip()

            if len(content_text) < 100:
                incomplete_recipes.append({
                    'number': i,
                    'header': recipe_header.get_text()[:50],
                    'content_length': len(content_text)
                })

        if incomplete_recipes:
            self.errors.append(
                f"Found {len(incomplete_recipes)} incomplete recipes (less than 100 chars of content): " +
                ', '.join([f"#{r['number']} ({r['header']})" for r in incomplete_recipes[:5]])
            )
        else:
            self.validation_results.append(
                f"✅ All {min(found_count, expected_count)} recipes appear complete"
            )

    def _validate_images(self, content: str, expected_count: int):
        """Validate image presence and handling."""
        # Count both image tags and image placeholders
        img_tags = len(re.findall(r'<img[^>]+>', content))
        img_placeholders = len(re.findall(r'\[Image:[^\]]+\]', content))

        total_images = img_tags + img_placeholders

        if img_placeholders > 0:
            self.warnings.append(
                f"Found {img_placeholders} unprocessed image placeholders - images may have failed to generate"
            )

        if total_images < expected_count:
            self.warnings.append(
                f"Image count low: Found {total_images} images (expected {expected_count})"
            )
        else:
            self.validation_results.append(
                f"✅ Image count good: {img_tags} images, {img_placeholders} placeholders"
            )

    def _validate_tables(self, content: str, expected_count: int):
        """Validate table presence."""
        table_count = len(re.findall(r'<table[^>]*>', content))
        table_placeholders = len(re.findall(r'\[Table:[^\]]+\]', content))

        total_tables = table_count + table_placeholders

        if table_placeholders > 0:
            self.warnings.append(
                f"Found {table_placeholders} unprocessed table placeholders"
            )

        if total_tables < expected_count:
            self.warnings.append(
                f"Table count low: Found {total_tables} tables (expected {expected_count})"
            )
        else:
            self.validation_results.append(
                f"✅ Table count good: {table_count} tables, {table_placeholders} placeholders"
            )

    def _validate_temporal_context(self, content: str, title: str):
        """
        Validate that temporal language is appropriate for the current time of year.

        Checks for inappropriate time-of-year references.
        """
        current_date = datetime.now()
        month = current_date.month
        day = current_date.day

        content_lower = (content + ' ' + title).lower()

        # Define inappropriate phrases for different times of year
        temporal_checks = []

        # "Kick off the year" language is only appropriate in early January
        if not (month == 1 and day <= 15):
            kick_off_phrases = [
                'kick off the year',
                'kick the year off',
                'start the year right',
                'begin the year',
                'start of the year',
                'new year resolution'
            ]
            for phrase in kick_off_phrases:
                if phrase in content_lower:
                    temporal_checks.append(f"Inappropriate phrase for {current_date.strftime('%B %d')}: '{phrase}'")

        # Check for summer language in winter and vice versa
        if month in [12, 1, 2]:  # Winter
            summer_phrases = ['perfect for summer', 'summer grilling', 'hot summer day']
            for phrase in summer_phrases:
                if phrase in content_lower:
                    temporal_checks.append(f"Summer reference in winter: '{phrase}'")

        elif month in [6, 7, 8]:  # Summer
            winter_phrases = ['cozy winter', 'cold weather', 'winter warming']
            for phrase in winter_phrases:
                if phrase in content_lower:
                    temporal_checks.append(f"Winter reference in summer: '{phrase}'")

        if temporal_checks:
            self.warnings.append(
                f"Temporal context issues found: {'; '.join(temporal_checks[:3])}"
            )
        else:
            self.validation_results.append(
                f"✅ Temporal context appropriate for {current_date.strftime('%B %Y')}"
            )

    def _validate_structure(self, content: str):
        """Validate HTML structure and formatting."""
        soup = BeautifulSoup(content, 'html.parser')

        # Check for proper heading hierarchy
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))

        if h2_count < 3:
            self.warnings.append(
                f"Low H2 count: {h2_count} (recommended: 6-10 for comprehensive content)"
            )
        else:
            self.validation_results.append(f"✅ Good H2 structure: {h2_count} sections")

        # Check for lists
        list_count = len(soup.find_all(['ul', 'ol']))
        if list_count < 2:
            self.warnings.append("Few lists found - consider adding more bullet points")
        else:
            self.validation_results.append(f"✅ Good use of lists: {list_count} lists")

    def _validate_seo_metadata(self, article_data: Dict):
        """Validate SEO metadata."""
        meta_title = article_data.get('meta_title', '')
        meta_description = article_data.get('meta_description', '')

        if not meta_title:
            self.errors.append("Missing meta_title")
        elif len(meta_title) > 60:
            self.warnings.append(f"Meta title too long: {len(meta_title)} chars (recommended: <60)")
        else:
            self.validation_results.append(f"✅ Meta title good: {len(meta_title)} chars")

        if not meta_description:
            self.errors.append("Missing meta_description")
        elif len(meta_description) < 120:
            self.warnings.append(f"Meta description short: {len(meta_description)} chars (recommended: 150-155)")
        elif len(meta_description) > 160:
            self.warnings.append(f"Meta description too long: {len(meta_description)} chars (recommended: 150-155)")
        else:
            self.validation_results.append(f"✅ Meta description good: {len(meta_description)} chars")

        # Check categories and tags
        categories = article_data.get('categories', [])
        tags = article_data.get('tags', [])

        if not categories:
            self.warnings.append("No categories assigned")
        else:
            self.validation_results.append(f"✅ Categories: {len(categories)}")

        if not tags:
            self.warnings.append("No tags assigned")
        else:
            self.validation_results.append(f"✅ Tags: {len(tags)}")

    def _generate_summary(self) -> str:
        """Generate a summary of validation results."""
        summary = []
        if self.errors:
            summary.append(f"❌ {len(self.errors)} ERRORS found")
        if self.warnings:
            summary.append(f"⚠️  {len(self.warnings)} warnings")
        if not self.errors and not self.warnings:
            summary.append("✅ All validation checks passed")

        return ' | '.join(summary)

    def print_report(self, report: Dict):
        """Pretty print the validation report."""
        print("\n" + "="*80)
        print("📋 CONTENT QA VALIDATION REPORT")
        print("="*80)
        print(f"\n{report['summary']}\n")

        if report['errors']:
            print("❌ ERRORS (MUST FIX):")
            for error in report['errors']:
                print(f"   - {error}")
            print()

        if report['warnings']:
            print("⚠️  WARNINGS (SHOULD FIX):")
            for warning in report['warnings']:
                print(f"   - {warning}")
            print()

        if report['validation_results']:
            print("✅ PASSED CHECKS:")
            for result in report['validation_results']:
                print(f"   {result}")
            print()

        print("="*80)
        print()

        return report['is_valid']
