"""
page_type_detector.py
=====================
Utility to detect WordPress page types and determine appropriate update strategies.
"""

from typing import Dict, Optional
from enum import Enum
import re


class PageType(Enum):
    """WordPress page types."""
    POST = "post"           # Regular blog post - full content update
    PAGE = "page"           # Static page - full content update
    HOMEPAGE = "homepage"   # Homepage - SEO meta only (never update content!)
    CATEGORY = "category"   # Category archive - SEO meta only
    TAG = "tag"             # Tag archive - SEO meta only
    AUTHOR = "author"       # Author archive - SEO meta only
    DATE = "date"           # Date archive - SEO meta only
    SEARCH = "search"       # Search results - skip
    ATTACHMENT = "attachment"  # Media attachment - skip
    UNKNOWN = "unknown"     # Unknown type


class UpdateStrategy(Enum):
    """Update strategies for different page types."""
    FULL_CONTENT = "full_content"  # Can update full content (posts, pages)
    META_ONLY = "meta_only"        # Can only update SEO meta (categories, tags)
    SKIP = "skip"                  # Should not update (search, date archives)


class PageTypeDetector:
    """Detect WordPress page types from URLs and determine update strategies."""

    # URL patterns for different page types
    PATTERNS = {
        PageType.CATEGORY: [r'/category/[^/]+/?$'],
        PageType.TAG: [r'/tag/[^/]+/?$'],
        PageType.AUTHOR: [r'/author/[^/]+/?$'],
        PageType.DATE: [
            r'/\d{4}/?$',                    # /2025/
            r'/\d{4}/\d{2}/?$',              # /2025/01/
            r'/\d{4}/\d{2}/\d{2}/?$'         # /2025/01/15/
        ],
        PageType.SEARCH: [r'/\?s=', r'/search/'],
        PageType.ATTACHMENT: [r'/attachment/[^/]+/?$'],
    }

    @staticmethod
    def detect_page_type(url: str) -> PageType:
        """
        Detect the page type from a URL.

        Args:
            url: The page URL to analyze

        Returns:
            PageType enum value

        Examples:
            detect_page_type("https://site.com/category/bobcats/") -> PageType.CATEGORY
            detect_page_type("https://site.com/my-post/") -> PageType.POST (or PAGE)
            detect_page_type("https://site.com/tag/recipes/") -> PageType.TAG
            detect_page_type("https://site.com/") -> PageType.HOMEPAGE
        """
        if not url:
            return PageType.UNKNOWN

        # Check for homepage first (root URL)
        # Homepage URLs end with just "/" or domain only
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path or path == '':
            return PageType.HOMEPAGE

        # Check against known patterns
        for page_type, patterns in PageTypeDetector.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return page_type

        # If no pattern matches, assume it's a post or page
        # We'll distinguish between these when we fetch from WordPress
        return PageType.POST  # Default assumption

    @staticmethod
    def get_update_strategy(page_type: PageType) -> UpdateStrategy:
        """
        Get the appropriate update strategy for a page type.

        Args:
            page_type: The detected page type

        Returns:
            UpdateStrategy enum value
        """
        strategy_map = {
            PageType.POST: UpdateStrategy.FULL_CONTENT,
            PageType.PAGE: UpdateStrategy.FULL_CONTENT,
            PageType.HOMEPAGE: UpdateStrategy.META_ONLY,  # Homepage: SEO meta only, NEVER content
            PageType.CATEGORY: UpdateStrategy.META_ONLY,
            PageType.TAG: UpdateStrategy.META_ONLY,
            PageType.AUTHOR: UpdateStrategy.META_ONLY,
            PageType.DATE: UpdateStrategy.SKIP,
            PageType.SEARCH: UpdateStrategy.SKIP,
            PageType.ATTACHMENT: UpdateStrategy.SKIP,
            PageType.UNKNOWN: UpdateStrategy.SKIP,
        }
        return strategy_map.get(page_type, UpdateStrategy.SKIP)

    @staticmethod
    def can_update_content(url: str) -> bool:
        """
        Quick check if a URL allows full content updates.

        Args:
            url: The page URL

        Returns:
            True if full content updates are allowed, False otherwise
        """
        page_type = PageTypeDetector.detect_page_type(url)
        strategy = PageTypeDetector.get_update_strategy(page_type)
        return strategy == UpdateStrategy.FULL_CONTENT

    @staticmethod
    def should_skip(url: str) -> bool:
        """
        Check if a URL should be skipped entirely.

        Args:
            url: The page URL

        Returns:
            True if should skip, False otherwise
        """
        page_type = PageTypeDetector.detect_page_type(url)
        strategy = PageTypeDetector.get_update_strategy(page_type)
        return strategy == UpdateStrategy.SKIP

    @staticmethod
    def get_update_info(url: str) -> Dict:
        """
        Get complete information about how to update a URL.

        Args:
            url: The page URL

        Returns:
            Dictionary with page_type, strategy, can_update_content, should_skip
        """
        page_type = PageTypeDetector.detect_page_type(url)
        strategy = PageTypeDetector.get_update_strategy(page_type)

        return {
            'url': url,
            'page_type': page_type.value,
            'strategy': strategy.value,
            'can_update_content': strategy == UpdateStrategy.FULL_CONTENT,
            'can_update_meta': strategy in [UpdateStrategy.FULL_CONTENT, UpdateStrategy.META_ONLY],
            'should_skip': strategy == UpdateStrategy.SKIP,
            'explanation': PageTypeDetector._get_explanation(page_type, strategy)
        }

    @staticmethod
    def _get_explanation(page_type: PageType, strategy: UpdateStrategy) -> str:
        """Get human-readable explanation of the update strategy."""
        explanations = {
            (PageType.POST, UpdateStrategy.FULL_CONTENT):
                "Regular blog post - can update full content and SEO meta",
            (PageType.PAGE, UpdateStrategy.FULL_CONTENT):
                "Static page - can update full content and SEO meta",
            (PageType.HOMEPAGE, UpdateStrategy.META_ONLY):
                "Homepage - can ONLY update SEO meta (title, description, meta tags). Content will NOT be modified for safety.",
            (PageType.CATEGORY, UpdateStrategy.META_ONLY):
                "Category archive - can only update SEO title, description, and meta tags (no content body)",
            (PageType.TAG, UpdateStrategy.META_ONLY):
                "Tag archive - can only update SEO title, description, and meta tags (no content body)",
            (PageType.AUTHOR, UpdateStrategy.META_ONLY):
                "Author archive - can only update SEO meta (no content body)",
            (PageType.DATE, UpdateStrategy.SKIP):
                "Date archive - should not be updated (auto-generated)",
            (PageType.SEARCH, UpdateStrategy.SKIP):
                "Search results page - should not be updated (dynamic)",
            (PageType.ATTACHMENT, UpdateStrategy.SKIP):
                "Media attachment - should not be updated",
            (PageType.UNKNOWN, UpdateStrategy.SKIP):
                "Unknown page type - skipping for safety",
        }
        return explanations.get((page_type, strategy), "No explanation available")


if __name__ == "__main__":
    # Test cases
    test_urls = [
        "https://griddleking.com/best-griddles-2025/",
        "https://griddleking.com/category/bobcats/",
        "https://griddleking.com/tag/recipes/",
        "https://griddleking.com/author/john/",
        "https://griddleking.com/2025/01/",
        "https://griddleking.com/about/",
    ]

    print("Page Type Detection Tests:")
    print("=" * 80)
    for url in test_urls:
        info = PageTypeDetector.get_update_info(url)
        print(f"\nURL: {url}")
        print(f"  Type: {info['page_type']}")
        print(f"  Strategy: {info['strategy']}")
        print(f"  Can update content: {info['can_update_content']}")
        print(f"  Explanation: {info['explanation']}")
