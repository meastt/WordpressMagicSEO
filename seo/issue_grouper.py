"""
SEO Issue Grouper
=================
Groups and batches SEO issues from audit results for efficient fixing.
"""

from typing import Dict, List, Tuple, Any
from collections import defaultdict


# Issues that have fix handlers implemented
FIXABLE_ISSUES = {
    # On-page SEO
    "h1_presence",
    "title_presence",
    "meta_description_presence",
    "title_length",
    "meta_description_length",
    "multiple_h1s",
    "heading_hierarchy",
    "content_length",
    
    # Links
    "anchor_text",
    "internal_links",
    "external_links",
    "broken_links",
    
    # Images
    "image_alt_text",
    "image_dimensions",
    
    # Technical
    "canonical_tag",
    "schema_markup",
    "open_graph",
    "noindex",  # Can remove noindex via SEO plugin meta
}

# Issues that require manual intervention
MANUAL_FIX_ISSUES = {
    "robots_txt",
    "sitemap",
    "ssl_https",
    "mixed_content",
    "www_redirect",
    "image_size",
    "ttfb",
    "compression",
}

# URL patterns that can't be edited via WordPress REST API
NON_EDITABLE_PATTERNS = [
    '/category/',
    '/tag/',
    '/author/',
    '/page/',  # Pagination
    '/feed/',
    '/wp-json/',
    '/wp-admin/',
    '/wp-content/',
]

# Fix impact scores: higher = more impactful for rankings
# Used to prioritize which fixes to run first
FIX_IMPACT_SCORES = {
    # Critical SEO factors (9-10)
    "noindex": {
        "score": 10,
        "ranking_boost": "+100% visibility",
        "why": "Removes block preventing Google from seeing your page"
    },
    "h1_presence": {
        "score": 9,
        "ranking_boost": "+5-10 positions",
        "why": "Google uses H1 as primary signal for page topic"
    },
    "title_presence": {
        "score": 9,
        "ranking_boost": "+5-10 positions", 
        "why": "Page title appears in search results and is a top ranking factor"
    },
    "canonical_tag": {
        "score": 9,
        "ranking_boost": "Prevents duplicate penalties",
        "why": "Tells Google which version of the page to index"
    },
    
    # High impact (7-8)
    "meta_description_presence": {
        "score": 8,
        "ranking_boost": "+10-30% click rate",
        "why": "Shows in search results, affects whether people click"
    },
    "title_length": {
        "score": 7,
        "ranking_boost": "+5-10% click rate",
        "why": "Optimal length prevents truncation in search results"
    },
    "meta_description_length": {
        "score": 7,
        "ranking_boost": "+5-10% click rate",
        "why": "Optimal length shows full description in search results"
    },
    "multiple_h1s": {
        "score": 7,
        "ranking_boost": "+2-5 positions",
        "why": "Multiple H1s confuse Google about page topic"
    },
    
    # Medium impact (5-6)
    "schema_markup": {
        "score": 6,
        "ranking_boost": "Rich snippets in search",
        "why": "Enables star ratings, FAQs, and other rich results"
    },
    "heading_hierarchy": {
        "score": 5,
        "ranking_boost": "+1-3 positions",
        "why": "Proper structure helps Google understand content organization"
    },
    "image_alt_text": {
        "score": 5,
        "ranking_boost": "Image search traffic",
        "why": "Enables images to rank in Google Image search"
    },
    "open_graph": {
        "score": 5,
        "ranking_boost": "Better social sharing",
        "why": "Controls how page looks when shared on social media"
    },
    "image_dimensions": {
        "score": 4,
        "ranking_boost": "Better UX & Speed",
        "why": "Prevents layout shift (CLS) for a smoother mobile experience"
    },
    
    # Lower impact (3-4)
    "internal_links": {
        "score": 4,
        "ranking_boost": "+1-2 positions",
        "why": "Helps Google discover and understand related content"
    },
    "external_links": {
        "score": 4,
        "ranking_boost": "+1 position",
        "why": "Citing sources increases content trustworthiness"
    },
    "anchor_text": {
        "score": 3,
        "ranking_boost": "Better UX",
        "why": "Descriptive links help users and search engines"
    },
    "broken_links": {
        "score": 3,
        "ranking_boost": "Prevents UX issues",
        "why": "Broken links frustrate users and waste crawl budget"
    },
    "content_length": {
        "score": 3,
        "ranking_boost": "+1-5 positions (topic dependent)",
        "why": "Thin content may not satisfy user search intent"
    },
}

def is_editable_url(url: str, site_url: str = None) -> bool:
    """
    Check if a URL can be edited via WordPress REST API.
    
    Returns False for:
    - Category pages
    - Tag pages
    - Author archives
    - Pagination pages
    - Home page
    - Feed URLs
    - WordPress system URLs
    """
    url_lower = url.lower()
    
    # Check for non-editable patterns
    for pattern in NON_EDITABLE_PATTERNS:
        if pattern in url_lower:
            return False
    
    # Check for home page
    if site_url:
        site_clean = site_url.rstrip('/')
        url_clean = url.rstrip('/')
        if url_clean == site_clean:
            return False
    else:
        # Heuristic: if URL path is just the domain with trailing slash
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.path or parsed.path == '/':
            return False
    
    # Check for common archive patterns (date-based)
    import re
    # Matches /2024/, /2024/12/, /2024/12/26/
    if re.search(r'/\d{4}/(\d{2}/)?(\d{2}/)?$', url):
        return False
    
    return True


class IssueGrouper:
    """Groups and organizes SEO issues for batch fixing."""
    
    @staticmethod
    def group_by_issue_type(audit_json: dict) -> Dict[str, List[str]]:
        """
        Group all URLs by issue type.
        
        Args:
            audit_json: Full audit result JSON
            
        Returns:
            Dict mapping issue type -> list of URLs with that issue
        """
        groups = defaultdict(list)
        
        for url_result in audit_json.get("urls", []):
            url = url_result.get("url", "")
            issues = url_result.get("issues", {})
            
            for category, issue_list in issues.items():
                for issue in issue_list:
                    check_name = issue.get("check_name", "")
                    status = issue.get("status", "")
                    
                    # Only include critical and warning issues
                    if status in ["critical", "warning"]:
                        groups[check_name].append(url)
        
        return dict(groups)
    
    @staticmethod
    def group_by_severity(audit_json: dict) -> Dict[str, List[dict]]:
        """
        Group all issues by severity level.
        
        Args:
            audit_json: Full audit result JSON
            
        Returns:
            Dict with 'critical', 'warning', 'optimal' keys
        """
        groups = {
            "critical": [],
            "warning": [],
            "optimal": []
        }
        
        for url_result in audit_json.get("urls", []):
            url = url_result.get("url", "")
            issues = url_result.get("issues", {})
            
            for category, issue_list in issues.items():
                for issue in issue_list:
                    status = issue.get("status", "")
                    if status in groups:
                        groups[status].append({
                            "url": url,
                            "category": category,
                            "issue": issue
                        })
        
        return groups
    
    @staticmethod
    def get_fixable_vs_manual(audit_json: dict) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Separate issues into fixable (automated) vs manual.
        Filters out URLs that can't be edited (category pages, archives, etc.)
        
        Args:
            audit_json: Full audit result JSON
            
        Returns:
            Tuple of (fixable_issues, manual_issues) dicts
        """
        fixable = defaultdict(list)
        manual = defaultdict(list)
        
        site_url = audit_json.get("site_url", "")
        
        for url_result in audit_json.get("urls", []):
            url = url_result.get("url", "")
            issues = url_result.get("issues", {})
            
            # Skip non-editable URLs entirely for fixable issues
            url_is_editable = is_editable_url(url, site_url)
            
            for category, issue_list in issues.items():
                for issue in issue_list:
                    check_name = issue.get("check_name", "")
                    status = issue.get("status", "")
                    
                    if status not in ["critical", "warning"]:
                        continue
                    
                    if check_name in FIXABLE_ISSUES:
                        # Only add to fixable if URL can actually be edited
                        if url_is_editable:
                            fixable[check_name].append(url)
                        # else: silently skip - user doesn't need to see these
                    else:
                        manual[check_name].append(url)
        
        return dict(fixable), dict(manual)
    
    @staticmethod
    def get_batch_fix_plan(
        audit_json: dict, 
        max_batch_size: int = 50,
        priority_order: List[str] = None
    ) -> List[dict]:
        """
        Create a prioritized batch fix plan.
        
        Args:
            audit_json: Full audit result JSON
            max_batch_size: Maximum URLs per batch
            priority_order: Custom priority order for issue types
            
        Returns:
            List of batch dicts with issue_type, urls, and priority
        """
        if priority_order is None:
            # Default priority: most impactful issues first
            priority_order = [
                "h1_presence",
                "title_presence",
                "title_length",
                "meta_description_presence",
                "meta_description_length",
                "image_alt_text",
                "heading_hierarchy",
                "multiple_h1s",
                "anchor_text",
                "internal_links",
                "canonical_tag",
                "schema_markup",
                "open_graph",
                "broken_links",
                "external_links",
                "content_length",
            ]
        
        fixable, _ = IssueGrouper.get_fixable_vs_manual(audit_json)
        
        batches = []
        for priority, issue_type in enumerate(priority_order):
            if issue_type in fixable:
                urls = fixable[issue_type]
                
                # Split into batches if needed
                for i in range(0, len(urls), max_batch_size):
                    batch_urls = urls[i:i + max_batch_size]
                    batches.append({
                        "issue_type": issue_type,
                        "urls": batch_urls,
                        "count": len(batch_urls),
                        "priority": priority + 1,
                        "is_fixable": True
                    })
        
        return batches
    
    @staticmethod
    def get_summary(audit_json: dict) -> dict:
        """
        Get a high-level summary of issues for the dashboard.
        
        Args:
            audit_json: Full audit result JSON
            
        Returns:
            Summary dict with counts and percentages
        """
        fixable, manual = IssueGrouper.get_fixable_vs_manual(audit_json)
        severity_groups = IssueGrouper.group_by_severity(audit_json)
        
        total_fixable = sum(len(urls) for urls in fixable.values())
        total_manual = sum(len(urls) for urls in manual.values())
        total_critical = len(severity_groups.get("critical", []))
        total_warnings = len(severity_groups.get("warning", []))
        
        # Build top issues with impact scores, sorted by impact
        all_issues = {**fixable, **manual}
        top_issues = []
        for issue_type, urls in all_issues.items():
            impact_info = FIX_IMPACT_SCORES.get(issue_type, {})
            top_issues.append({
                "type": issue_type,
                "friendly_name": IssueGrouper.get_friendly_issue_name(issue_type),
                "count": len(urls),
                "fixable": issue_type in FIXABLE_ISSUES,
                "impact_score": impact_info.get("score", 1),
                "ranking_boost": impact_info.get("ranking_boost", ""),
                "why": impact_info.get("why", "")
            })
        
        # Sort by impact score (highest first)
        top_issues.sort(key=lambda x: (-x["impact_score"], -x["count"]))
        
        return {
            "total_urls": len(audit_json.get("urls", [])),
            "critical_count": total_critical,
            "warning_count": total_warnings,
            "total_issues": total_critical + total_warnings,
            "fixable_count": total_fixable,
            "manual_count": total_manual,
            "fixable_percentage": round(total_fixable / max(total_fixable + total_manual, 1) * 100),
            "issue_types_fixable": len(fixable),
            "issue_types_manual": len(manual),
            "top_issues": top_issues[:15]  # Top 15 by impact
        }
    
    @staticmethod
    def get_friendly_issue_name(issue_type: str) -> str:
        """Convert technical issue names to user-friendly labels."""
        friendly_names = {
            "h1_presence": "Missing main heading (H1)",
            "title_presence": "Missing page title",
            "title_length": "Page title too long/short",
            "meta_description_presence": "Missing page description",
            "meta_description_length": "Description too long/short",
            "multiple_h1s": "Multiple main headings",
            "heading_hierarchy": "Heading order issues",
            "content_length": "Content too short",
            "image_alt_text": "Images missing descriptions",
            "anchor_text": "Links say 'click here'",
            "internal_links": "Missing links to related pages",
            "external_links": "Missing external references",
            "broken_links": "Broken links found",
            "canonical_tag": "Missing canonical tag",
            "schema_markup": "Missing structured data",
            "open_graph": "Missing social sharing info",
            "noindex": "Page hidden from Google",
            "ssl_https": "Security issues",
            "mixed_content": "Mixed HTTP/HTTPS content",
            "www_redirect": "WWW redirect issues",
        }
        return friendly_names.get(issue_type, issue_type.replace("_", " ").title())


# Utility function for quick access
def group_audit_issues(audit_json: dict) -> dict:
    """
    Quick utility to get all groupings at once.
    
    Returns dict with:
    - summary: High-level stats
    - by_type: Issues grouped by type
    - by_severity: Issues grouped by severity
    - fixable: Auto-fixable issues
    - manual: Manual-fix issues
    - fix_plan: Prioritized fix batches
    """
    grouper = IssueGrouper()
    fixable, manual = grouper.get_fixable_vs_manual(audit_json)
    
    return {
        "summary": grouper.get_summary(audit_json),
        "by_type": grouper.group_by_issue_type(audit_json),
        "by_severity": grouper.group_by_severity(audit_json),
        "fixable": fixable,
        "manual": manual,
        "fix_plan": grouper.get_batch_fix_plan(audit_json)
    }
