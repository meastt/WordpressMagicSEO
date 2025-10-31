"""
seo_checklist_validator.py
===========================
Comprehensive SEO checklist validator that ensures all SEO elements meet professional standards.

This validator checks:
- Title tags (length, keywords, uniqueness)
- Meta descriptions (length, call-to-action, keywords)
- Taxonomies (categories, tags)
- Internal links (presence, anchor text, relevance)
- External links (presence, quality, attributes)
- Image SEO (alt text, titles, file names)
- Schema markup (type, completeness)
- Header structure (H1/H2/H3 hierarchy)
- Keyword optimization
- Content quality
"""

import re
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class SEOChecklistValidator:
    """
    Comprehensive SEO checklist validator for WordPress content.
    """

    def __init__(self):
        self.critical_issues = []  # Must fix before publishing
        self.warnings = []  # Should fix for better SEO
        self.passed = []  # Checks that passed
        self.seo_score = 0  # Out of 100

    def validate_seo(
        self,
        article_data: Dict,
        primary_keyword: str = None,
        site_url: str = None
    ) -> Tuple[bool, Dict]:
        """
        Run comprehensive SEO validation.

        Args:
            article_data: Article data with title, content, meta, categories, tags
            primary_keyword: Primary target keyword
            site_url: Site URL to identify internal vs external links

        Returns:
            Tuple of (is_valid, seo_report)
        """
        self.critical_issues = []
        self.warnings = []
        self.passed = []

        content = article_data.get('content', '')
        title = article_data.get('title', '')
        meta_title = article_data.get('meta_title', title)
        meta_description = article_data.get('meta_description', '')
        categories = article_data.get('categories', [])
        tags = article_data.get('tags', [])
        schema_markup = article_data.get('schema_markup', {})

        # Extract primary keyword if not provided
        if not primary_keyword and article_data.get('keywords'):
            keywords = article_data.get('keywords', [])
            primary_keyword = keywords[0] if keywords else None

        soup = BeautifulSoup(content, 'html.parser')

        # 1. Title Tag Validation
        self._validate_title_tag(meta_title, title, primary_keyword)

        # 2. Meta Description Validation
        self._validate_meta_description(meta_description, primary_keyword)

        # 3. Taxonomies Validation
        self._validate_taxonomies(categories, tags, primary_keyword)

        # 4. Header Structure Validation
        self._validate_header_structure(soup, primary_keyword)

        # 5. Keyword Optimization Validation
        self._validate_keyword_optimization(soup, title, primary_keyword)

        # 6. Internal Links Validation
        self._validate_internal_links(soup, site_url)

        # 7. External Links Validation
        self._validate_external_links(soup, site_url)

        # 8. Image SEO Validation
        self._validate_image_seo(soup, primary_keyword)

        # 9. Schema Markup Validation
        self._validate_schema_markup(schema_markup)

        # 10. Content Quality Validation
        self._validate_content_quality(soup, primary_keyword)

        # Calculate SEO score
        total_checks = len(self.critical_issues) + len(self.warnings) + len(self.passed)
        if total_checks > 0:
            # Critical issues heavily penalize score
            penalty = (len(self.critical_issues) * 10) + (len(self.warnings) * 3)
            self.seo_score = max(0, 100 - penalty)
        else:
            self.seo_score = 100

        # Is valid if no critical issues
        is_valid = len(self.critical_issues) == 0

        report = {
            'is_valid': is_valid,
            'seo_score': self.seo_score,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'passed': self.passed,
            'summary': self._generate_summary()
        }

        return is_valid, report

    def _validate_title_tag(self, meta_title: str, title: str, primary_keyword: Optional[str]):
        """Validate title tag for SEO best practices."""
        if not meta_title or not meta_title.strip():
            self.critical_issues.append("❌ Meta title is missing")
            return

        title_len = len(meta_title)

        # Length check (50-60 optimal for Google)
        if title_len < 30:
            self.warnings.append(f"⚠️  Meta title too short: {title_len} chars (recommended: 50-60)")
        elif title_len > 60:
            self.warnings.append(f"⚠️  Meta title too long: {title_len} chars (recommended: 50-60, will be truncated in SERPs)")
        else:
            self.passed.append(f"✅ Meta title length optimal: {title_len} chars")

        # Keyword presence
        if primary_keyword:
            if primary_keyword.lower() in meta_title.lower():
                self.passed.append(f"✅ Primary keyword '{primary_keyword}' in meta title")
            else:
                self.warnings.append(f"⚠️  Primary keyword '{primary_keyword}' not in meta title")

        # Check for duplicate with article title (should be similar but optimized)
        if meta_title == title:
            self.warnings.append("⚠️  Meta title identical to article title (consider optimizing for CTR)")

        # Check for power words / CTR optimization
        power_words = ['best', 'ultimate', 'guide', 'complete', 'essential', 'proven', 'easy', 'simple', 'top']
        has_power_word = any(word in meta_title.lower() for word in power_words)
        if has_power_word:
            self.passed.append("✅ Meta title contains engagement words")
        else:
            self.warnings.append("⚠️  Consider adding power words to meta title for better CTR")

    def _validate_meta_description(self, meta_description: str, primary_keyword: Optional[str]):
        """Validate meta description for SEO best practices."""
        if not meta_description or not meta_description.strip():
            self.critical_issues.append("❌ Meta description is missing")
            return

        desc_len = len(meta_description)

        # Length check (150-160 optimal)
        if desc_len < 120:
            self.warnings.append(f"⚠️  Meta description too short: {desc_len} chars (recommended: 150-160)")
        elif desc_len > 160:
            self.warnings.append(f"⚠️  Meta description too long: {desc_len} chars (will be truncated in SERPs)")
        else:
            self.passed.append(f"✅ Meta description length optimal: {desc_len} chars")

        # Keyword presence
        if primary_keyword:
            if primary_keyword.lower() in meta_description.lower():
                self.passed.append(f"✅ Primary keyword '{primary_keyword}' in meta description")
            else:
                self.warnings.append(f"⚠️  Primary keyword '{primary_keyword}' not in meta description")

        # Check for call-to-action
        cta_words = ['learn', 'discover', 'find out', 'explore', 'read', 'see how', 'get', 'buy', 'shop', 'compare']
        has_cta = any(word in meta_description.lower() for word in cta_words)
        if has_cta:
            self.passed.append("✅ Meta description includes call-to-action")
        else:
            self.warnings.append("⚠️  Meta description lacks call-to-action (reduces CTR)")

    def _validate_taxonomies(self, categories: List[str], tags: List[str], primary_keyword: Optional[str]):
        """Validate categories and tags."""
        # Categories
        if not categories:
            self.critical_issues.append("❌ No categories assigned")
        elif len(categories) < 2:
            self.warnings.append(f"⚠️  Only {len(categories)} category (recommended: 2-4 for better organization)")
        elif len(categories) > 5:
            self.warnings.append(f"⚠️  Too many categories: {len(categories)} (recommended: 2-4, too many dilutes relevance)")
        else:
            self.passed.append(f"✅ Good category count: {len(categories)} categories")

        # Tags
        if not tags:
            self.critical_issues.append("❌ No tags assigned")
        elif len(tags) < 5:
            self.warnings.append(f"⚠️  Only {len(tags)} tags (recommended: 5-10 for better discoverability)")
        elif len(tags) > 15:
            self.warnings.append(f"⚠️  Too many tags: {len(tags)} (recommended: 5-10, too many looks spammy)")
        else:
            self.passed.append(f"✅ Good tag count: {len(tags)} tags")

        # Tag relevance - check if primary keyword is in tags
        if primary_keyword and tags:
            keyword_in_tags = any(primary_keyword.lower() in tag.lower() for tag in tags)
            if keyword_in_tags:
                self.passed.append(f"✅ Primary keyword in tags")
            else:
                self.warnings.append(f"⚠️  Consider adding '{primary_keyword}' as a tag")

    def _validate_header_structure(self, soup: BeautifulSoup, primary_keyword: Optional[str]):
        """Validate H1/H2/H3 header hierarchy."""
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        h3_tags = soup.find_all('h3')

        # H1 validation (WordPress title is usually H1, so content shouldn't have H1)
        if len(h1_tags) > 0:
            self.warnings.append(f"⚠️  Content contains {len(h1_tags)} H1 tags (WordPress title is H1, avoid duplicates)")

        # H2 validation (main sections)
        if len(h2_tags) < 3:
            self.warnings.append(f"⚠️  Only {len(h2_tags)} H2 headers (recommended: 6-10 for comprehensive content)")
        elif len(h2_tags) > 15:
            self.warnings.append(f"⚠️  Too many H2 headers: {len(h2_tags)} (content may be too fragmented)")
        else:
            self.passed.append(f"✅ Good H2 structure: {len(h2_tags)} main sections")

        # H3 validation (subsections)
        if len(h3_tags) > 0:
            self.passed.append(f"✅ Has {len(h3_tags)} H3 subsections (good depth)")

        # Keyword in headers
        if primary_keyword:
            h2_with_keyword = sum(1 for h2 in h2_tags if primary_keyword.lower() in h2.get_text().lower())
            if h2_with_keyword >= 2:
                self.passed.append(f"✅ Primary keyword in {h2_with_keyword} H2 headers")
            elif h2_with_keyword == 1:
                self.warnings.append("⚠️  Primary keyword only in 1 H2 (consider adding to 1-2 more headers)")
            else:
                self.warnings.append("⚠️  Primary keyword not in any H2 headers (important for SEO)")

    def _validate_keyword_optimization(self, soup: BeautifulSoup, title: str, primary_keyword: Optional[str]):
        """Validate keyword placement and density."""
        if not primary_keyword:
            self.warnings.append("⚠️  No primary keyword specified (cannot validate keyword optimization)")
            return

        text = soup.get_text().lower()
        keyword_lower = primary_keyword.lower()

        # Keyword in title
        if keyword_lower in title.lower():
            self.passed.append(f"✅ Primary keyword in article title")
        else:
            self.critical_issues.append(f"❌ Primary keyword '{primary_keyword}' NOT in article title")

        # Keyword in first paragraph
        paragraphs = soup.find_all('p')
        if paragraphs and keyword_lower in paragraphs[0].get_text().lower():
            self.passed.append("✅ Primary keyword in first paragraph")
        else:
            self.warnings.append("⚠️  Primary keyword should appear in first paragraph")

        # Keyword density (1-2% is optimal)
        word_count = len(text.split())
        keyword_count = text.count(keyword_lower)
        if word_count > 0:
            density = (keyword_count / word_count) * 100
            if density < 0.5:
                self.warnings.append(f"⚠️  Keyword density too low: {density:.2f}% (recommended: 1-2%)")
            elif density > 3:
                self.warnings.append(f"⚠️  Keyword density too high: {density:.2f}% (may trigger keyword stuffing penalty)")
            else:
                self.passed.append(f"✅ Keyword density optimal: {density:.2f}% ({keyword_count} occurrences)")

    def _validate_internal_links(self, soup: BeautifulSoup, site_url: Optional[str]):
        """Validate internal links presence and quality."""
        all_links = soup.find_all('a', href=True)

        if not all_links:
            self.critical_issues.append("❌ No links found in content")
            return

        internal_links = []
        if site_url:
            site_domain = urlparse(site_url).netloc
            internal_links = [
                link for link in all_links
                if site_domain in link.get('href', '')
                or link.get('href', '').startswith('/')
            ]
        else:
            # Assume relative URLs are internal
            internal_links = [link for link in all_links if link.get('href', '').startswith('/')]

        # Check minimum internal links
        if len(internal_links) == 0:
            self.critical_issues.append("❌ No internal links (critical for SEO and site structure)")
        elif len(internal_links) < 2:
            self.warnings.append(f"⚠️  Only {len(internal_links)} internal link (recommended: 3-5)")
        elif len(internal_links) > 10:
            self.warnings.append(f"⚠️  Too many internal links: {len(internal_links)} (may dilute link value)")
        else:
            self.passed.append(f"✅ Good internal linking: {len(internal_links)} internal links")

        # Check anchor text quality
        empty_anchors = [link for link in internal_links if not link.get_text().strip()]
        if empty_anchors:
            self.warnings.append(f"⚠️  {len(empty_anchors)} internal links have empty anchor text")

        # Check for "click here" or "here" anchor text (poor SEO practice)
        poor_anchors = [
            link for link in internal_links
            if link.get_text().strip().lower() in ['click here', 'here', 'this', 'link', 'read more']
        ]
        if poor_anchors:
            self.warnings.append(f"⚠️  {len(poor_anchors)} internal links use non-descriptive anchor text (use keywords instead)")
        else:
            self.passed.append("✅ Internal links use descriptive anchor text")

    def _validate_external_links(self, soup: BeautifulSoup, site_url: Optional[str]):
        """Validate external links presence and quality."""
        all_links = soup.find_all('a', href=True)

        external_links = []
        if site_url:
            site_domain = urlparse(site_url).netloc
            external_links = [
                link for link in all_links
                if link.get('href', '').startswith('http')
                and site_domain not in link.get('href', '')
            ]
        else:
            # Assume http/https URLs are external
            external_links = [link for link in all_links if link.get('href', '').startswith('http')]

        # Check minimum external links
        if len(external_links) == 0:
            self.warnings.append("⚠️  No external links (linking to authoritative sources improves E-E-A-T)")
        elif len(external_links) < 2:
            self.warnings.append(f"⚠️  Only {len(external_links)} external link (recommended: 2-3 to authoritative sources)")
        elif len(external_links) > 10:
            self.warnings.append(f"⚠️  Many external links: {len(external_links)} (ensure they add value)")
        else:
            self.passed.append(f"✅ Good external linking: {len(external_links)} authoritative links")

        # Check for proper attributes (nofollow for affiliate/sponsored)
        affiliate_keywords = ['amazon', 'affiliate', 'partner', 'buy', 'shop']
        affiliate_links = [
            link for link in external_links
            if any(keyword in link.get('href', '').lower() for keyword in affiliate_keywords)
        ]

        if affiliate_links:
            links_with_nofollow = [
                link for link in affiliate_links
                if 'nofollow' in link.get('rel', [])
            ]
            if len(links_with_nofollow) < len(affiliate_links):
                self.warnings.append(f"⚠️  {len(affiliate_links) - len(links_with_nofollow)} affiliate links missing rel='nofollow' (Google guideline)")
            else:
                self.passed.append(f"✅ All {len(affiliate_links)} affiliate links have proper nofollow attribute")

        # Check for target="_blank" on external links
        links_with_target_blank = [link for link in external_links if link.get('target') == '_blank']
        if len(links_with_target_blank) == len(external_links):
            self.passed.append("✅ All external links open in new tab (good UX)")
        else:
            self.warnings.append("⚠️  Some external links don't open in new tab (consider adding target='_blank')")

    def _validate_image_seo(self, soup: BeautifulSoup, primary_keyword: Optional[str]):
        """Validate image SEO (alt text, titles, file names)."""
        images = soup.find_all('img')

        if not images:
            self.warnings.append("⚠️  No images in content (images improve engagement and SEO)")
            return

        total_images = len(images)

        # Check for alt text on all images
        images_without_alt = [img for img in images if not img.get('alt') or not img.get('alt').strip()]
        if images_without_alt:
            self.critical_issues.append(f"❌ {len(images_without_alt)} of {total_images} images missing alt text (CRITICAL for accessibility and SEO)")
        else:
            self.passed.append(f"✅ All {total_images} images have alt text")

        # Check for descriptive alt text (not just "image" or "photo")
        generic_alt_words = ['image', 'photo', 'picture', 'img']
        images_with_generic_alt = [
            img for img in images
            if img.get('alt', '').strip().lower() in generic_alt_words
        ]
        if images_with_generic_alt:
            self.warnings.append(f"⚠️  {len(images_with_generic_alt)} images have generic alt text (be more descriptive)")

        # Check if alt text includes primary keyword
        if primary_keyword:
            images_with_keyword = [
                img for img in images
                if primary_keyword.lower() in img.get('alt', '').lower()
            ]
            if images_with_keyword:
                self.passed.append(f"✅ {len(images_with_keyword)} images include target keyword in alt text")
            else:
                self.warnings.append(f"⚠️  No images include primary keyword '{primary_keyword}' in alt text")

        # Check for title attributes
        images_with_title = [img for img in images if img.get('title')]
        if len(images_with_title) == total_images:
            self.passed.append(f"✅ All images have title attributes")
        elif len(images_with_title) > 0:
            self.warnings.append(f"⚠️  Only {len(images_with_title)} of {total_images} images have title attributes")
        else:
            self.warnings.append("⚠️  No images have title attributes (adds extra keyword opportunity)")

        # Check for SEO-friendly file names (if src is visible)
        images_with_bad_names = []
        for img in images:
            src = img.get('src', '')
            filename = src.split('/')[-1].split('?')[0]  # Get filename without query params
            # Check for generic names like "image1.jpg", "photo.png", "IMG_1234.jpg"
            if re.match(r'^(image|photo|img|picture|screenshot)[-_]?\d*\.(jpg|jpeg|png|gif|webp)$', filename.lower()):
                images_with_bad_names.append(filename)
            elif re.match(r'^IMG[-_]\d+\.(jpg|jpeg|png|gif|webp)$', filename, re.IGNORECASE):
                images_with_bad_names.append(filename)

        if images_with_bad_names and len(images_with_bad_names) > total_images * 0.5:
            self.warnings.append(f"⚠️  {len(images_with_bad_names)} images have non-descriptive file names (use keyword-rich names)")
        elif len(images_with_bad_names) == 0:
            self.passed.append("✅ Images have SEO-friendly file names")

    def _validate_schema_markup(self, schema_markup: Dict):
        """Validate schema.org structured data."""
        if not schema_markup or not isinstance(schema_markup, dict):
            self.warnings.append("⚠️  No schema markup (structured data helps search engines understand content)")
            return

        # Check for @context and @type
        if '@context' not in schema_markup:
            self.warnings.append("⚠️  Schema markup missing @context")
        if '@type' not in schema_markup:
            self.critical_issues.append("❌ Schema markup missing @type")
            return

        schema_type = schema_markup.get('@type')
        self.passed.append(f"✅ Schema markup present: {schema_type}")

        # Validate common required fields based on type
        if schema_type == 'Article':
            required_fields = ['headline', 'datePublished', 'author', 'publisher']
            missing_fields = [field for field in required_fields if field not in schema_markup]
            if missing_fields:
                self.warnings.append(f"⚠️  Article schema missing fields: {', '.join(missing_fields)}")
            else:
                self.passed.append("✅ Article schema has all required fields")

        elif schema_type == 'Product':
            required_fields = ['name', 'description', 'offers']
            missing_fields = [field for field in required_fields if field not in schema_markup]
            if missing_fields:
                self.warnings.append(f"⚠️  Product schema missing fields: {', '.join(missing_fields)}")

        elif schema_type == 'HowTo':
            if 'step' not in schema_markup:
                self.warnings.append("⚠️  HowTo schema missing 'step' field")
            else:
                self.passed.append("✅ HowTo schema includes steps")

    def _validate_content_quality(self, soup: BeautifulSoup, primary_keyword: Optional[str]):
        """Validate overall content quality metrics."""
        text = soup.get_text()
        word_count = len(text.split())

        # Word count
        if word_count < 300:
            self.critical_issues.append(f"❌ Content too short: {word_count} words (minimum: 300, recommended: 1500+)")
        elif word_count < 1000:
            self.warnings.append(f"⚠️  Content somewhat short: {word_count} words (recommended: 1500+ for competitive keywords)")
        else:
            self.passed.append(f"✅ Good content length: {word_count} words")

        # Check for lists (improve readability)
        lists = soup.find_all(['ul', 'ol'])
        if len(lists) >= 2:
            self.passed.append(f"✅ Good use of lists: {len(lists)} lists")
        elif len(lists) == 0:
            self.warnings.append("⚠️  No lists found (bullet points improve readability)")

        # Check for tables (good for data presentation)
        tables = soup.find_all('table')
        if len(tables) > 0:
            self.passed.append(f"✅ Includes {len(tables)} tables (good for comparisons/data)")

        # Check for strong/em tags (emphasis)
        strong_tags = soup.find_all(['strong', 'b', 'em', 'i'])
        if len(strong_tags) > 5:
            self.passed.append("✅ Good use of text emphasis")
        else:
            self.warnings.append("⚠️  Consider emphasizing important keywords with <strong> or <em>")

    def _generate_summary(self) -> str:
        """Generate summary of SEO validation."""
        summary_parts = []

        if self.seo_score >= 90:
            summary_parts.append(f"🌟 EXCELLENT SEO: {self.seo_score}/100")
        elif self.seo_score >= 70:
            summary_parts.append(f"✅ GOOD SEO: {self.seo_score}/100")
        elif self.seo_score >= 50:
            summary_parts.append(f"⚠️  NEEDS IMPROVEMENT: {self.seo_score}/100")
        else:
            summary_parts.append(f"❌ POOR SEO: {self.seo_score}/100")

        if self.critical_issues:
            summary_parts.append(f"{len(self.critical_issues)} CRITICAL issues")
        if self.warnings:
            summary_parts.append(f"{len(self.warnings)} warnings")
        if self.passed:
            summary_parts.append(f"{len(self.passed)} passed")

        return " | ".join(summary_parts)

    def print_report(self, report: Dict):
        """Pretty print the SEO validation report."""
        print("\n" + "="*80)
        print("🔍 SEO CHECKLIST VALIDATION REPORT")
        print("="*80)
        print(f"\n{report['summary']}\n")

        if report['critical_issues']:
            print("❌ CRITICAL ISSUES (MUST FIX BEFORE PUBLISHING):")
            for issue in report['critical_issues']:
                print(f"   {issue}")
            print()

        if report['warnings']:
            print("⚠️  WARNINGS (SHOULD FIX FOR BETTER SEO):")
            for warning in report['warnings']:
                print(f"   {warning}")
            print()

        if report['passed']:
            print("✅ PASSED CHECKS:")
            for passed in report['passed'][:10]:  # Show first 10
                print(f"   {passed}")
            if len(report['passed']) > 10:
                print(f"   ... and {len(report['passed']) - 10} more passed checks")
            print()

        print("="*80)
        print(f"SEO SCORE: {report['seo_score']}/100")
        print("="*80)
        print()

        return report['is_valid']
