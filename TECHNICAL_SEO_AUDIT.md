# Technical SEO Audit System

## Overview

Standalone technical SEO audit tool that performs comprehensive site-wide analysis, checking all technical SEO factors similar to Ahrefs, SEMrush, or Yoast SEO.

## Features

### Technical Foundation Checks
- ✅ robots.txt file existence and parsing
- ✅ noindex tags (HTML meta, HTTP header, robots.txt)
- ✅ XML sitemap verification
- ✅ Canonical tags (self-referencing, cross-domain detection)
- ✅ WWW vs non-WWW redirects
- ✅ SSL/HTTPS verification
- ✅ Mixed content detection
- ✅ Permalink structure (pretty vs ugly URLs)
- ✅ URL length analysis

### On-Page SEO Checks
- ✅ Title tag (presence, length 50-60 chars optimal)
- ✅ Meta description (presence, length 120-160 chars optimal)
- ✅ H1 tags (exactly one, content analysis)
- ✅ Heading hierarchy (H1→H2→H3, no skipping)
- ✅ Content length (context-aware: blog 300+, product 200+, landing 150+)
- ✅ Keyword density (if keyword provided)
- ✅ Keyword in first 10% of content

### Links & Site Structure
- ✅ Internal links (count, anchor text analysis)
- ✅ External links (count, broken link detection)
- ✅ Orphaned pages (pages with 0 internal links - optional)
- ✅ Redirect chains (detect loops, count hops)
- ✅ Nofollow/sponsored attributes

### Images & Media
- ✅ Alt text (all images, decorative image detection)
- ✅ Missing dimensions (width/height attributes)
- ✅ File size (context-aware: 200KB threshold with dimension checks)
- ✅ Lazy loading detection

### Performance
- ✅ Time to First Byte (TTFB) measurement
- ✅ GZIP/Brotli compression detection
- ✅ CSS/JS minification (basic check)

### Schema & Social
- ✅ Schema markup (JSON-LD validation)
- ✅ Open Graph tags (og:title, og:image, og:description)
- ✅ Twitter Cards (twitter:card, twitter:title, etc.)

## Usage

### CLI

**Audit single URL:**
```bash
python seo_audit_cli.py https://example.com \
  --url https://example.com/specific-page \
  --output html \
  --output-file audit.html
```

**Audit entire site (limited):**
```bash
python seo_audit_cli.py https://example.com \
  --max-urls 50 \
  --output json \
  --output-file audit.json
```

**Full site audit with orphaned page detection:**
```bash
python seo_audit_cli.py https://example.com \
  --check-orphaned \
  --output csv \
  --output-file full_audit.csv
```

### API

**POST /api/seo-audit**

**Parameters:**
- `site_url` (required): Site to audit
- `max_urls` (optional): Limit number of URLs
- `output_format` (optional): json, csv, or html (default: json)
- `check_orphaned` (optional): true/false (default: false)
- `rate_limit` (optional): Seconds between requests (default: 2.0)

**Example:**
```bash
curl -X POST https://your-api.vercel.app/api/seo-audit \
  -F "site_url=https://example.com" \
  -F "max_urls=50" \
  -F "output_format=json"
```

## Output Formats

### JSON
Structured data with all check results, suitable for programmatic processing.

### CSV
Spreadsheet-friendly format with one row per issue:
- URL, Status Code, Category, Check Name, Status, Severity, Confidence, Message, Value, Edge Case

### HTML
Human-readable report with:
- Color-coded issues (critical=red, warning=yellow, optimal=green)
- Summary statistics
- Detailed breakdown by URL and category
- Edge case indicators

## Severity Levels

- **Critical**: Definitely wrong, needs fixing (e.g., missing title tag, noindex enabled)
- **Warning**: Suboptimal, should fix (e.g., title 65 chars instead of 60)
- **Optimal**: Check passed (e.g., title 55 chars, canonical self-referencing)
- **Info**: Observation, not necessarily wrong (e.g., robots.txt not found)

## Confidence Levels

- **High**: Rule is clear, result is definitive
- **Medium**: Rule has some ambiguity, result is likely correct
- **Low**: Rule is ambiguous, result needs human review

## Edge Cases Handled

The system explicitly handles:
- Multiple canonical tags
- noindex in multiple locations (HTML, HTTP header, robots.txt)
- Non-standard heading hierarchy (H1→H3→H2)
- Protocol-relative URLs (//example.com)
- Redirect chains and loops
- JavaScript-rendered content (documented limitation)
- Decorative images (empty alt allowed)
- Context-aware thresholds (blog vs product vs landing pages)

## Rate Limiting

Default: 2 seconds between requests to avoid overwhelming servers.

Adjust with `--rate-limit` flag or `rate_limit` API parameter.

## Limitations

1. **JavaScript Content**: BeautifulSoup cannot see content loaded via JavaScript. Full JS rendering requires headless browser (not implemented in v1).

2. **Orphaned Pages**: Requires full site crawl to build link graph. Computationally expensive for large sites.

3. **Broken Links**: Checks sample of external links (first 10) to avoid excessive requests.

4. **Performance**: TTFB measurement affected by network latency. Multiple measurements recommended for accuracy.

## Files

- `seo/technical_auditor.py` - Main auditor class
- `seo/report_generator.py` - Report formatting
- `seo_audit_cli.py` - CLI entry point
- `api/generate.py` - API endpoint (`/api/seo-audit`)

## Example Output

```json
{
  "site_url": "https://example.com",
  "audit_date": "2025-01-XX",
  "total_urls_checked": 50,
  "summary": {
    "critical_issues": 12,
    "warnings": 45,
    "passed": 93
  },
  "urls": [
    {
      "url": "https://example.com/page",
      "status_code": 200,
      "fetch_time": 0.523,
      "issues": {
        "technical": [
          {
            "check_name": "noindex",
            "status": "critical",
            "severity": "high",
            "confidence": "high",
            "message": "Page is marked as noindex in: HTML meta tag"
          }
        ],
        "onpage": [...],
        "links": [...],
        "images": [...],
        "performance": [...],
        "schema": [...]
      }
    }
  ]
}
```

---

**Ready to use!** Test with a single URL first, then scale up to full site audits.

