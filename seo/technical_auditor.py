"""
technical_auditor.py
====================
Comprehensive technical SEO audit system that crawls and analyzes WordPress sites.

Checks all technical SEO factors:
- Technical foundation (robots.txt, noindex, canonical, SSL, etc.)
- On-page SEO (title, meta, headings, content)
- Links & structure (internal/external, redirects, orphaned pages)
- Images & media (alt text, dimensions, file size)
- Performance (TTFB, minification, compression)
- Schema & social (JSON-LD, Open Graph, Twitter Cards)
"""

import requests
import time
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from collections import defaultdict

from data.sitemap_analyzer import SitemapAnalyzer
from seo.fix_tracker import SEOFixTracker


@dataclass
class AuditResult:
    """Result of a single check."""
    check_name: str
    status: str  # "optimal", "warning", "critical", "info", "error"
    severity: str  # "none", "low", "medium", "high"
    confidence: str  # "high", "medium", "low"
    message: str
    value: Optional[str] = None
    edge_case_detected: bool = False


@dataclass
class URLAuditResult:
    """Complete audit result for a single URL."""
    url: str
    status_code: int
    fetch_time: float
    issues: Dict[str, List[AuditResult]] = field(default_factory=dict)
    error: Optional[str] = None


class TechnicalSEOAuditor:
    """Comprehensive technical SEO auditor."""
    
    def __init__(
        self,
        site_url: str,
        rate_limit_delay: float = 2.0,
        timeout: int = 30,
        max_redirects: int = 5
    ):
        """
        Initialize technical SEO auditor.
        
        Args:
            site_url: Base URL of the site to audit
            rate_limit_delay: Seconds to wait between requests
            timeout: Request timeout in seconds
            max_redirects: Maximum redirect hops to follow
        """
        self.site_url = site_url.rstrip("/")
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.parsed_site_url = urlparse(self.site_url)
        self.site_domain = self.parsed_site_url.netloc
        
        # Cache for robots.txt and other shared resources
        self._robots_txt = None
        self._robots_parser = None
        self._sitemap_urls = None
        
        # Link graph for orphaned page detection
        self._link_graph = defaultdict(set)  # url -> set of URLs that link to it
        
        # Fix tracker to skip already-fixed URLs
        self.fix_tracker = SEOFixTracker(site_url=site_url)
        
    def _is_fully_fixed(self, url: str) -> bool:
        """
        Check if URL has been fixed for all common issues.
        This is a heuristic - we skip URLs that were fixed for multiple issues.
        """
        fix_history = self.fix_tracker.get_fix_history(url)
        if not fix_history:
            return False
        
        # Count successful fixes
        successful_fixes = sum(
            1 for issues in fix_history.values()
            for fix in issues
            if fix.get("success", False)
        )
        
        # If URL has 3+ successful fixes, consider it "fully fixed" and skip
        # This is a heuristic - adjust as needed
        return successful_fixes >= 3
    
    def audit_site(
        self,
        max_urls: Optional[int] = None,
        check_orphaned: bool = False,
        skip_fixed: bool = True
    ) -> Dict:
        """
        Audit entire site by crawling sitemap.
        
        Args:
            max_urls: Limit number of URLs to audit (None = all)
            check_orphaned: Whether to check for orphaned pages (requires full crawl)
            
        Returns:
            Complete audit results dictionary
        """
        print(f"🔍 Starting technical SEO audit for: {self.site_url}")
        print(f"   Rate limit: {self.rate_limit_delay}s between requests")
        
        # Fetch sitemap
        print("\n📋 Fetching sitemap...")
        sitemap_analyzer = SitemapAnalyzer(self.site_url)
        sitemap_urls = sitemap_analyzer.fetch_sitemap()
        
        if not sitemap_urls:
            return {
                "site_url": self.site_url,
                "audit_date": datetime.now().isoformat(),
                "error": "Could not fetch sitemap",
                "total_urls_checked": 0,
                "urls": []
            }
        
        urls_to_audit = [url_obj.url for url_obj in sitemap_urls]
        
        # Filter out URLs that were already fixed (if skip_fixed is enabled)
        if skip_fixed:
            original_count = len(urls_to_audit)
            urls_to_audit = [
                url for url in urls_to_audit
                if not self._is_fully_fixed(url)
            ]
            skipped_count = original_count - len(urls_to_audit)
            if skipped_count > 0:
                print(f"   Skipped {skipped_count} URLs that were already fixed")
        
        if max_urls:
            urls_to_audit = urls_to_audit[:max_urls]
            print(f"   Limited to first {max_urls} URLs")
        
        print(f"   Found {len(urls_to_audit)} URLs to audit\n")
        
        # Fetch robots.txt once
        self._fetch_robots_txt()
        
        # Audit each URL
        url_results = []
        total_urls = len(urls_to_audit)
        
        for i, url in enumerate(urls_to_audit, 1):
            print(f"[{i}/{total_urls}] Auditing: {url}")
            result = self.audit_url(url)
            url_results.append(result)
            
            # Rate limiting
            if i < total_urls:
                time.sleep(self.rate_limit_delay)
        
        # Build link graph for orphaned detection if requested
        if check_orphaned and len(url_results) > 1:
            print("\n🔗 Building link graph for orphaned page detection...")
            self._build_link_graph(url_results)
            self._check_orphaned_pages(url_results)
        
        # Generate summary
        summary = self._generate_summary(url_results)
        
        return {
            "site_url": self.site_url,
            "audit_date": datetime.now().isoformat(),
            "total_urls_checked": len(url_results),
            "summary": summary,
            "urls": [self._serialize_url_result(r) for r in url_results]
        }
    
    def audit_url(self, url: str) -> URLAuditResult:
        """
        Audit a single URL.
        
        Args:
            url: URL to audit
            
        Returns:
            URLAuditResult with all checks
        """
        start_time = time.time()
        issues = {
            "technical": [],
            "onpage": [],
            "links": [],
            "images": [],
            "performance": [],
            "schema": []
        }
        
        try:
            # Fetch robots.txt if not already fetched
            if self._robots_txt is None:
                self._fetch_robots_txt()
            
            # Fetch URL
            response = self._fetch_url(url)
            fetch_time = time.time() - start_time
            
            if response is None:
                return URLAuditResult(
                    url=url,
                    status_code=0,
                    fetch_time=fetch_time,
                    error="Failed to fetch URL"
                )
            
            html = response.text
            status_code = response.status_code
            
            # Run all checks
            issues["technical"] = self._check_technical_foundation(url, html, response)
            issues["onpage"] = self._check_onpage_seo(url, html)
            issues["links"] = self._check_links(url, html)
            issues["images"] = self._check_images(url, html)
            issues["performance"] = self._check_performance(url, response)
            issues["schema"] = self._check_schema_social(url, html)
            
            return URLAuditResult(
                url=url,
                status_code=status_code,
                fetch_time=fetch_time,
                issues=issues
            )
            
        except Exception as e:
            return URLAuditResult(
                url=url,
                status_code=0,
                fetch_time=time.time() - start_time,
                error=str(e)
            )
    
    def _fetch_url(self, url: str) -> Optional[requests.Response]:
        """Fetch URL with proper headers and error handling."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; TechnicalSEOAuditor/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Cache-Control": "no-cache"  # For accurate TTFB measurement
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True
            )
            
            # Read content
            response.text  # Trigger content download
            
            return response
            
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
    
    def _fetch_robots_txt(self):
        """Fetch and parse robots.txt."""
        try:
            robots_url = urljoin(self.site_url, "/robots.txt")
            response = requests.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                self._robots_txt = response.text
                self._robots_parser = RobotFileParser()
                self._robots_parser.set_url(robots_url)
                self._robots_parser.read()
            else:
                self._robots_txt = None
                self._robots_parser = None
                
        except Exception:
            self._robots_txt = None
            self._robots_parser = None
    
    def _check_technical_foundation(
        self,
        url: str,
        html: str,
        response: requests.Response
    ) -> List[AuditResult]:
        """Check technical foundation issues."""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. robots.txt
        if self._robots_txt is None:
            results.append(AuditResult(
                check_name="robots_txt",
                status="info",
                severity="none",
                confidence="high",
                message="robots.txt not found (not required, but recommended)"
            ))
        else:
            results.append(AuditResult(
                check_name="robots_txt",
                status="optimal",
                severity="none",
                confidence="high",
                message="robots.txt exists and is accessible"
            ))
        
        # 2. noindex detection (check all locations)
        noindex_found = False
        noindex_locations = []
        
        # Check HTML meta tag
        meta_robots = soup.find('meta', attrs={'name': re.compile(r'robots', re.I)})
        if meta_robots:
            content = meta_robots.get('content', '').lower()
            if 'noindex' in content:
                noindex_found = True
                noindex_locations.append("HTML meta tag")
        
        # Check X-Robots-Tag HTTP header
        x_robots = response.headers.get('X-Robots-Tag', '')
        if x_robots and 'noindex' in x_robots.lower():
            noindex_found = True
            noindex_locations.append("HTTP header")
        
        # Check robots.txt (if parser available)
        if self._robots_parser:
            try:
                if not self._robots_parser.can_fetch('*', url):
                    noindex_found = True
                    noindex_locations.append("robots.txt")
            except:
                pass
        
        if noindex_found:
            results.append(AuditResult(
                check_name="noindex",
                status="critical",
                severity="high",
                confidence="high",
                message=f"Page is marked as noindex in: {', '.join(noindex_locations)}",
                value=", ".join(noindex_locations)
            ))
        else:
            results.append(AuditResult(
                check_name="noindex",
                status="optimal",
                severity="none",
                confidence="high",
                message="Page is not marked as noindex"
            ))
        
        # 3. XML Sitemap (check once per site, not per URL)
        if self._sitemap_urls is None:
            sitemap_analyzer = SitemapAnalyzer(self.site_url)
            sitemap_urls = sitemap_analyzer.fetch_sitemap()
            self._sitemap_urls = sitemap_urls
            
            if sitemap_urls:
                results.append(AuditResult(
                    check_name="xml_sitemap",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message=f"XML sitemap exists with {len(sitemap_urls)} URLs"
                ))
            else:
                results.append(AuditResult(
                    check_name="xml_sitemap",
                    status="warning",
                    severity="medium",
                    confidence="high",
                    message="XML sitemap not found or not accessible"
                ))
        
        # 4. Canonical tags
        canonical_tags = soup.find_all('link', attrs={'rel': re.compile(r'canonical', re.I)})
        
        if not canonical_tags:
            results.append(AuditResult(
                check_name="canonical_tag",
                status="warning",
                severity="medium",
                confidence="high",
                message="No canonical tag found"
            ))
        elif len(canonical_tags) > 1:
            results.append(AuditResult(
                check_name="canonical_tag",
                status="critical",
                severity="high",
                confidence="high",
                message=f"Multiple canonical tags found ({len(canonical_tags)}) - invalid HTML",
                edge_case_detected=True
            ))
        else:
            canonical_url = canonical_tags[0].get('href', '')
            # Check if self-referencing
            canonical_parsed = urlparse(canonical_url)
            url_parsed = urlparse(url)
            
            if canonical_parsed.path == url_parsed.path or canonical_url == url:
                results.append(AuditResult(
                    check_name="canonical_tag",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message="Canonical tag is self-referencing"
                ))
            else:
                # Cross-domain canonical
                if canonical_parsed.netloc != url_parsed.netloc:
                    results.append(AuditResult(
                        check_name="canonical_tag",
                        status="warning",
                        severity="low",
                        confidence="high",
                        message=f"Canonical points to different domain: {canonical_url}",
                        edge_case_detected=True
                    ))
                else:
                    results.append(AuditResult(
                        check_name="canonical_tag",
                        status="warning",
                        severity="medium",
                        confidence="high",
                        message=f"Canonical points to different URL: {canonical_url}"
                    ))
        
        # 5. WWW vs non-WWW (check redirect)
        www_url = url.replace('://', '://www.') if '://www.' not in url else url.replace('://www.', '://')
        try:
            www_response = requests.head(www_url, timeout=5, allow_redirects=True)
            if www_response.url != url and www_response.status_code in [301, 302]:
                results.append(AuditResult(
                    check_name="www_redirect",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message="Site redirects between www/non-www versions correctly"
                ))
            else:
                results.append(AuditResult(
                    check_name="www_redirect",
                    status="warning",
                    severity="low",
                    confidence="medium",
                    message="Both www and non-www versions may be accessible (could split authority)"
                ))
        except:
            pass  # Skip if check fails
        
        # 6. SSL/HTTPS
        if url.startswith('https://'):
            results.append(AuditResult(
                check_name="ssl_https",
                status="optimal",
                severity="none",
                confidence="high",
                message="Site uses HTTPS"
            ))
        else:
            results.append(AuditResult(
                check_name="ssl_https",
                status="critical",
                severity="high",
                confidence="high",
                message="Site does not use HTTPS"
            ))
        
        # 7. Mixed content
        if url.startswith('https://'):
            http_resources = re.findall(r'http://[^\s"\'<>]+', html)
            # Filter out protocol-relative URLs (//example.com is valid)
            http_resources = [r for r in http_resources if not r.startswith('//')]
            
            if http_resources:
                results.append(AuditResult(
                    check_name="mixed_content",
                    status="critical",
                    severity="high",
                    confidence="high",
                    message=f"Found {len(http_resources)} HTTP resources on HTTPS page",
                    value=str(len(http_resources))
                ))
            else:
                results.append(AuditResult(
                    check_name="mixed_content",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message="No mixed content detected"
                ))
        
        # 8. Permalink structure
        if '?p=' in url or '?page_id=' in url:
            results.append(AuditResult(
                check_name="permalink_structure",
                status="warning",
                severity="medium",
                confidence="high",
                message="URL uses query parameters (ugly permalink structure)"
            ))
        else:
            results.append(AuditResult(
                check_name="permalink_structure",
                status="optimal",
                severity="none",
                confidence="high",
                message="URL uses pretty permalink structure"
            ))
        
        # 9. URL length
        url_length = len(url)
        base_url = url.split('?')[0]  # Remove query parameters
        
        if url_length < 100:
            results.append(AuditResult(
                check_name="url_length",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"URL length is {url_length} characters (optimal)"
            ))
        elif url_length <= 150:
            results.append(AuditResult(
                check_name="url_length",
                status="warning",
                severity="low",
                confidence="high",
                message=f"URL length is {url_length} characters (slightly long)"
            ))
        else:
            results.append(AuditResult(
                check_name="url_length",
                status="critical",
                severity="medium",
                confidence="high",
                message=f"URL length is {url_length} characters (very long, may be truncated in SERPs)"
            ))
        
        return results
    
    def _check_onpage_seo(self, url: str, html: str) -> List[AuditResult]:
        """Check on-page SEO factors."""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Title tag
        title_tag = soup.find('title')
        
        if not title_tag:
            results.append(AuditResult(
                check_name="title_presence",
                status="critical",
                severity="high",
                confidence="high",
                message="Title tag is missing"
            ))
        else:
            title_text = title_tag.get_text().strip()
            title_length = len(title_text)
            
            results.append(AuditResult(
                check_name="title_presence",
                status="optimal",
                severity="none",
                confidence="high",
                message="Title tag exists",
                value=title_text
            ))
            
            # Title length
            if 50 <= title_length <= 60:
                results.append(AuditResult(
                    check_name="title_length",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message=f"Title length is {title_length} characters (optimal)"
                ))
            elif 45 <= title_length < 50 or 60 < title_length <= 65:
                results.append(AuditResult(
                    check_name="title_length",
                    status="warning",
                    severity="low",
                    confidence="high",
                    message=f"Title length is {title_length} characters (slightly outside optimal 50-60 range)"
                ))
            elif title_length < 30 or title_length > 70:
                results.append(AuditResult(
                    check_name="title_length",
                    status="critical",
                    severity="high",
                    confidence="high",
                    message=f"Title length is {title_length} characters (too short or too long for SERPs)"
                ))
            else:
                results.append(AuditResult(
                    check_name="title_length",
                    status="warning",
                    severity="medium",
                    confidence="high",
                    message=f"Title length is {title_length} characters (outside optimal range)"
                ))
        
        # 2. Meta description
        meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
        
        if not meta_desc:
            results.append(AuditResult(
                check_name="meta_description_presence",
                status="warning",
                severity="medium",
                confidence="high",
                message="Meta description is missing"
            ))
        else:
            desc_text = meta_desc.get('content', '').strip()
            desc_length = len(desc_text)
            
            results.append(AuditResult(
                check_name="meta_description_presence",
                status="optimal",
                severity="none",
                confidence="high",
                message="Meta description exists"
            ))
            
            # Meta description length
            if 120 <= desc_length <= 160:
                results.append(AuditResult(
                    check_name="meta_description_length",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message=f"Meta description length is {desc_length} characters (optimal)"
                ))
            elif 100 <= desc_length < 120 or 160 < desc_length <= 180:
                results.append(AuditResult(
                    check_name="meta_description_length",
                    status="warning",
                    severity="low",
                    confidence="high",
                    message=f"Meta description length is {desc_length} characters (slightly outside optimal 120-160 range)"
                ))
            elif desc_length < 100 or desc_length > 180:
                results.append(AuditResult(
                    check_name="meta_description_length",
                    status="warning",
                    severity="medium",
                    confidence="high",
                    message=f"Meta description length is {desc_length} characters (may be truncated in SERPs)"
                ))
        
        # 3. Headings
        # Count H1s in main content area (ignore header/footer)
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            h1s = main_content.find_all('h1')
        else:
            h1s = soup.find_all('h1')
        
        h1_count = len(h1s)
        
        if h1_count == 0:
            results.append(AuditResult(
                check_name="h1_presence",
                status="critical",
                severity="high",
                confidence="high",
                message="No H1 tag found"
            ))
        elif h1_count == 1:
            results.append(AuditResult(
                check_name="h1_presence",
                status="optimal",
                severity="none",
                confidence="high",
                message="Exactly one H1 tag found (optimal)"
            ))
        else:
            results.append(AuditResult(
                check_name="h1_presence",
                status="warning",
                severity="medium",
                confidence="high",
                message=f"Multiple H1 tags found ({h1_count}) - should be exactly one",
                edge_case_detected=True
            ))
        
        # Heading hierarchy
        if main_content:
            headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        else:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        hierarchy_issues = []
        prev_level = 0
        
        for heading in headings[:20]:  # Check first 20 headings
            level = int(heading.name[1])
            
            if prev_level > 0 and level > prev_level + 1:
                hierarchy_issues.append(f"Skipped from H{prev_level} to H{level}")
            
            prev_level = level
        
        if hierarchy_issues:
            results.append(AuditResult(
                check_name="heading_hierarchy",
                status="warning",
                severity="low",
                confidence="medium",
                message=f"Non-standard heading hierarchy detected: {', '.join(hierarchy_issues[:3])}",
                edge_case_detected=True
            ))
        else:
            results.append(AuditResult(
                check_name="heading_hierarchy",
                status="optimal",
                severity="none",
                confidence="medium",
                message="Heading hierarchy appears correct"
            ))
        
        # 4. Content analysis
        if main_content:
            content_text = main_content.get_text()
        else:
            content_text = soup.get_text()
        
        # Remove extra whitespace
        content_text = ' '.join(content_text.split())
        word_count = len(content_text.split())
        
        # Context-aware word count thresholds
        page_type = self._detect_page_type(url, soup)
        min_words = 300 if page_type == 'blog' else 200 if page_type == 'product' else 150
        
        if word_count >= min_words:
            results.append(AuditResult(
                check_name="content_length",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Content has {word_count} words (meets minimum of {min_words})"
            ))
        elif word_count >= min_words * 0.7:
            results.append(AuditResult(
                check_name="content_length",
                status="warning",
                severity="low",
                confidence="high",
                message=f"Content has {word_count} words (slightly below recommended {min_words})"
            ))
        else:
            results.append(AuditResult(
                check_name="content_length",
                status="warning",
                severity="medium",
                confidence="high",
                message=f"Content has {word_count} words (below recommended {min_words} for {page_type} pages)"
            ))
        
        return results
    
    def _check_links(self, url: str, html: str) -> List[AuditResult]:
        """Check links and site structure."""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        all_links = soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        broken_links = []
        
        for link in all_links:
            href = link.get('href', '')
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            
            # Check if internal or external
            if parsed.netloc == self.site_domain or parsed.netloc == '':
                internal_links.append((absolute_url, link.get_text().strip()))
            else:
                external_links.append((absolute_url, link.get_text().strip()))
        
        # Internal link count
        internal_count = len(internal_links)
        if internal_count >= 3:
            results.append(AuditResult(
                check_name="internal_links",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Found {internal_count} internal links (good for site structure)"
            ))
        elif internal_count > 0:
            results.append(AuditResult(
                check_name="internal_links",
                status="warning",
                severity="low",
                confidence="high",
                message=f"Found {internal_count} internal links (recommend at least 3-5)"
            ))
        else:
            results.append(AuditResult(
                check_name="internal_links",
                status="warning",
                severity="medium",
                confidence="high",
                message="No internal links found (orphaned content risk)"
            ))
        
        # Anchor text analysis
        generic_anchors = ['click here', 'read more', 'here', 'link', 'more']
        generic_count = sum(1 for _, anchor in internal_links 
                           if anchor.lower() in generic_anchors)
        
        if generic_count > 0:
            results.append(AuditResult(
                check_name="anchor_text",
                status="warning",
                severity="low",
                confidence="high",
                message=f"Found {generic_count} internal links with generic anchor text (use descriptive text)"
            ))
        else:
            results.append(AuditResult(
                check_name="anchor_text",
                status="optimal",
                severity="none",
                confidence="high",
                message="Internal links use descriptive anchor text"
            ))
        
        # External link count
        external_count = len(external_links)
        if external_count >= 2:
            results.append(AuditResult(
                check_name="external_links",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Found {external_count} external links (good for authority)"
            ))
        elif external_count == 1:
            results.append(AuditResult(
                check_name="external_links",
                status="warning",
                severity="low",
                confidence="high",
                message="Found 1 external link (recommend 2-3 authoritative sources)"
            ))
        else:
            results.append(AuditResult(
                check_name="external_links",
                status="info",
                severity="none",
                confidence="high",
                message="No external links found (consider adding authoritative sources)"
            ))
        
        # Check for broken links (sample first 10 external links)
        for ext_url, _ in external_links[:10]:
            try:
                head_response = requests.head(ext_url, timeout=5, allow_redirects=True)
                if head_response.status_code >= 400:
                    broken_links.append(ext_url)
            except:
                # Try GET if HEAD fails
                try:
                    get_response = requests.get(ext_url, timeout=5, stream=True, allow_redirects=True)
                    if get_response.status_code >= 400:
                        broken_links.append(ext_url)
                    get_response.close()
                except:
                    broken_links.append(ext_url)  # Assume broken if can't connect
        
        if broken_links:
            results.append(AuditResult(
                check_name="broken_links",
                status="warning",
                severity="medium",
                confidence="medium",
                message=f"Found {len(broken_links)} potentially broken external links",
                value=str(broken_links[:5])  # Show first 5
            ))
        else:
            results.append(AuditResult(
                check_name="broken_links",
                status="optimal",
                severity="none",
                confidence="medium",
                message="No broken external links detected (checked sample)"
            ))
        
        # Store links for orphaned page detection
        for int_url, _ in internal_links:
            self._link_graph[int_url].add(url)
        
        return results
    
    def _check_images(self, url: str, html: str) -> List[AuditResult]:
        """Check images and media."""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        images = soup.find_all('img')
        
        if not images:
            results.append(AuditResult(
                check_name="images_presence",
                status="info",
                severity="none",
                confidence="high",
                message="No images found on page"
            ))
            return results
        
        missing_alt = []
        missing_dimensions = []
        large_images = []
        
        for img in images:
            # Check alt text
            alt = img.get('alt', None)
            if alt is None:
                # Check if decorative (common patterns)
                src = img.get('src', '')
                is_decorative = any(pattern in src.lower() for pattern in 
                                  ['spacer', 'divider', 'bullet', 'arrow', 'icon'])
                
                if not is_decorative:
                    missing_alt.append(src[:50])  # Store first 50 chars of src
            
            # Check dimensions
            width = img.get('width')
            height = img.get('height')
            if not width or not height:
                missing_dimensions.append(img.get('src', '')[:50])
            
            # Check file size (if src is absolute URL)
            img_src = img.get('src', '')
            if img_src.startswith('http'):
                try:
                    img_response = requests.head(img_src, timeout=5)
                    content_length = img_response.headers.get('Content-Length')
                    if content_length:
                        size_kb = int(content_length) / 1024
                        # Context-aware: check image dimensions if available
                        if size_kb > 200:  # 200KB threshold
                            large_images.append((img_src[:50], f"{size_kb:.0f}KB"))
                except:
                    pass  # Skip if can't check
        
        # Alt text results
        if missing_alt:
            results.append(AuditResult(
                check_name="image_alt_text",
                status="critical",
                severity="high",
                confidence="high",
                message=f"{len(missing_alt)} images missing alt text (accessibility & SEO issue)",
                value=str(len(missing_alt))
            ))
        else:
            results.append(AuditResult(
                check_name="image_alt_text",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"All {len(images)} images have alt text"
            ))
        
        # Dimensions results
        if missing_dimensions:
            results.append(AuditResult(
                check_name="image_dimensions",
                status="warning",
                severity="low",
                confidence="high",
                message=f"{len(missing_dimensions)} images missing width/height attributes (may cause layout shift)",
                value=str(len(missing_dimensions))
            ))
        else:
            results.append(AuditResult(
                check_name="image_dimensions",
                status="optimal",
                severity="none",
                confidence="high",
                message="All images have dimension attributes"
            ))
        
        # File size results
        if large_images:
            results.append(AuditResult(
                check_name="image_file_size",
                status="warning",
                severity="medium",
                confidence="medium",
                message=f"{len(large_images)} images exceed 200KB (may slow page load)",
                value=str(large_images[:3])  # Show first 3
            ))
        else:
            results.append(AuditResult(
                check_name="image_file_size",
                status="optimal",
                severity="none",
                confidence="medium",
                message="Image file sizes appear reasonable (checked sample)"
            ))
        
        return results
    
    def _check_performance(
        self,
        url: str,
        response: requests.Response
    ) -> List[AuditResult]:
        """Check performance factors."""
        results = []
        
        # 1. TTFB (Time to First Byte)
        ttfb = response.elapsed.total_seconds()
        
        if ttfb < 0.2:
            results.append(AuditResult(
                check_name="ttfb",
                status="optimal",
                severity="none",
                confidence="medium",
                message=f"TTFB is {ttfb:.3f}s (excellent)"
            ))
        elif ttfb < 0.5:
            results.append(AuditResult(
                check_name="ttfb",
                status="optimal",
                severity="none",
                confidence="medium",
                message=f"TTFB is {ttfb:.3f}s (good)"
            ))
        elif ttfb < 1.0:
            results.append(AuditResult(
                check_name="ttfb",
                status="warning",
                severity="low",
                confidence="medium",
                message=f"TTFB is {ttfb:.3f}s (acceptable, but could be improved)"
            ))
        else:
            results.append(AuditResult(
                check_name="ttfb",
                status="warning",
                severity="medium",
                confidence="medium",
                message=f"TTFB is {ttfb:.3f}s (slow, may impact user experience)"
            ))
        
        # 2. Compression
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        
        if 'gzip' in content_encoding or 'br' in content_encoding or 'deflate' in content_encoding:
            results.append(AuditResult(
                check_name="compression",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Content is compressed ({content_encoding})"
            ))
        else:
            results.append(AuditResult(
                check_name="compression",
                status="warning",
                severity="low",
                confidence="high",
                message="Content compression not detected (GZIP/Brotli recommended)"
            ))
        
        # 3. CSS/JS minification (check linked resources)
        # This is a simplified check - would need to fetch actual files for full analysis
        results.append(AuditResult(
            check_name="minification",
            status="info",
            severity="none",
            confidence="low",
            message="CSS/JS minification check requires fetching individual files (not performed in basic audit)"
        ))
        
        return results
    
    def _check_schema_social(self, url: str, html: str) -> List[AuditResult]:
        """Check schema markup and social tags."""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Schema markup (JSON-LD)
        schema_scripts = soup.find_all('script', type='application/ld+json')
        
        if not schema_scripts:
            results.append(AuditResult(
                check_name="schema_markup",
                status="warning",
                severity="low",
                confidence="high",
                message="No schema markup (JSON-LD) found"
            ))
        else:
            valid_schemas = []
            invalid_schemas = []
            
            for script in schema_scripts:
                try:
                    schema_data = json.loads(script.string)
                    if isinstance(schema_data, dict) and '@type' in schema_data:
                        valid_schemas.append(schema_data.get('@type', 'Unknown'))
                    elif isinstance(schema_data, list):
                        for item in schema_data:
                            if isinstance(item, dict) and '@type' in item:
                                valid_schemas.append(item.get('@type', 'Unknown'))
                except json.JSONDecodeError:
                    invalid_schemas.append("Invalid JSON")
            
            if invalid_schemas:
                results.append(AuditResult(
                    check_name="schema_markup",
                    status="critical",
                    severity="high",
                    confidence="high",
                    message=f"Schema markup found but {len(invalid_schemas)} are invalid JSON",
                    edge_case_detected=True
                ))
            elif valid_schemas:
                results.append(AuditResult(
                    check_name="schema_markup",
                    status="optimal",
                    severity="none",
                    confidence="high",
                    message=f"Valid schema markup found: {', '.join(set(valid_schemas))}"
                ))
            else:
                results.append(AuditResult(
                    check_name="schema_markup",
                    status="warning",
                    severity="low",
                    confidence="medium",
                    message="Schema markup found but structure unclear"
                ))
        
        # 2. Open Graph tags
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        required_og = ['og:title', 'og:image']
        found_og = [tag.get('property', '') for tag in og_tags]
        
        missing_required = [req for req in required_og if req not in found_og]
        
        if missing_required:
            results.append(AuditResult(
                check_name="open_graph",
                status="warning",
                severity="low",
                confidence="high",
                message=f"Missing Open Graph tags: {', '.join(missing_required)}"
            ))
        else:
            results.append(AuditResult(
                check_name="open_graph",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Open Graph tags present ({len(og_tags)} tags)"
            ))
        
        # 3. Twitter Cards
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        
        if not twitter_tags:
            results.append(AuditResult(
                check_name="twitter_cards",
                status="info",
                severity="none",
                confidence="high",
                message="No Twitter Card tags found (optional)"
            ))
        else:
            results.append(AuditResult(
                check_name="twitter_cards",
                status="optimal",
                severity="none",
                confidence="high",
                message=f"Twitter Card tags present ({len(twitter_tags)} tags)"
            ))
        
        return results
    
    def _detect_page_type(self, url: str, soup: BeautifulSoup) -> str:
        """Detect page type for context-aware checks."""
        url_lower = url.lower()
        
        if any(x in url_lower for x in ['/product/', '/shop/', '/buy/']):
            return 'product'
        elif any(x in url_lower for x in ['/blog/', '/post/', '/article/']):
            return 'blog'
        elif any(x in url_lower for x in ['/category/', '/tag/']):
            return 'archive'
        else:
            return 'page'
    
    def _build_link_graph(self, url_results: List[URLAuditResult]):
        """Build link graph from audit results for orphaned page detection."""
        # Link graph is built during _check_links
        pass
    
    def _check_orphaned_pages(self, url_results: List[URLAuditResult]):
        """Check for orphaned pages (no internal links pointing to them)."""
        for result in url_results:
            if result.error:
                continue
            
            url = result.url
            incoming_links = len(self._link_graph.get(url, set()))
            
            if incoming_links == 0:
                # Check if it's homepage or important page
                if url == self.site_url or url == self.site_url + '/':
                    continue  # Homepage is expected to have links
                
                result.issues.setdefault("links", []).append(AuditResult(
                    check_name="orphaned_page",
                    status="warning",
                    severity="medium",
                    confidence="high",
                    message="No internal links point to this page (orphaned content)"
                ))
    
    def _generate_summary(self, url_results: List[URLAuditResult]) -> Dict:
        """Generate summary statistics from audit results."""
        total_critical = 0
        total_warnings = 0
        total_passed = 0
        
        for result in url_results:
            if result.error:
                continue
            
            for category, issues in result.issues.items():
                for issue in issues:
                    if issue.status == "critical":
                        total_critical += 1
                    elif issue.status == "warning":
                        total_warnings += 1
                    elif issue.status == "optimal":
                        total_passed += 1
        
        return {
            "critical_issues": total_critical,
            "warnings": total_warnings,
            "passed": total_passed
        }
    
    def _serialize_url_result(self, result: URLAuditResult) -> Dict:
        """Serialize URLAuditResult to dictionary."""
        serialized = {
            "url": result.url,
            "status_code": result.status_code,
            "fetch_time": result.fetch_time,
            "issues": {}
        }
        
        if result.error:
            serialized["error"] = result.error
        
        for category, issues in result.issues.items():
            serialized["issues"][category] = [
                {
                    "check_name": issue.check_name,
                    "status": issue.status,
                    "severity": issue.severity,
                    "confidence": issue.confidence,
                    "message": issue.message,
                    "value": issue.value,
                    "edge_case_detected": issue.edge_case_detected
                }
                for issue in issues
            ]
        
        return serialized

