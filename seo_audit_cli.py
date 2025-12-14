"""
seo_audit_cli.py
================
Command-line interface for technical SEO audits.
"""

import argparse
import sys
from seo.technical_auditor import TechnicalSEOAuditor
from seo.report_generator import SEOReportGenerator


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Technical SEO Audit Tool - Comprehensive site-wide SEO analysis"
    )
    
    parser.add_argument(
        "site_url",
        help="Site URL to audit (e.g., https://example.com)"
    )
    
    parser.add_argument(
        "--url",
        help="Single URL to audit (instead of full site crawl)"
    )
    
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Limit number of URLs to crawl (default: all)"
    )
    
    parser.add_argument(
        "--output",
        choices=["json", "csv", "html"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--output-file",
        help="Save report to file (default: print to stdout)"
    )
    
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Seconds to wait between requests (default: 2.0)"
    )
    
    parser.add_argument(
        "--check-orphaned",
        action="store_true",
        help="Check for orphaned pages (requires full site crawl)"
    )
    
    args = parser.parse_args()
    
    # Initialize auditor
    auditor = TechnicalSEOAuditor(
        site_url=args.site_url,
        rate_limit_delay=args.rate_limit
    )
    
    # Run audit
    if args.url:
        print(f"🔍 Auditing single URL: {args.url}")
        result = auditor.audit_url(args.url)
        from datetime import datetime
        audit_results = {
            "site_url": args.site_url,
            "audit_date": datetime.now().isoformat(),
            "total_urls_checked": 1,
            "summary": {
                "critical_issues": sum(1 for cat_issues in result.issues.values() 
                                      for issue in cat_issues if issue.status == "critical"),
                "warnings": sum(1 for cat_issues in result.issues.values() 
                               for issue in cat_issues if issue.status == "warning"),
                "passed": sum(1 for cat_issues in result.issues.values() 
                             for issue in cat_issues if issue.status == "optimal")
            },
            "urls": [auditor._serialize_url_result(result)]
        }
    else:
        print(f"🔍 Auditing site: {args.site_url}")
        audit_results = auditor.audit_site(
            max_urls=args.max_urls,
            check_orphaned=args.check_orphaned
        )
    
    # Generate report
    generator = SEOReportGenerator(audit_results)
    
    if args.output == "json":
        report = generator.generate_json()
    elif args.output == "csv":
        report = generator.generate_csv()
    elif args.output == "html":
        report = generator.generate_html()
    
    # Output report
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ Report saved to: {args.output_file}")
    else:
        print("\n" + "=" * 80)
        print("AUDIT REPORT")
        print("=" * 80)
        print(report)
    
    # Print summary
    summary = audit_results.get('summary', {})
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Critical Issues: {summary.get('critical_issues', 0)}")
    print(f"Warnings: {summary.get('warnings', 0)}")
    print(f"Passed: {summary.get('passed', 0)}")
    print(f"Total URLs Checked: {audit_results.get('total_urls_checked', 0)}")
    print("=" * 80)


if __name__ == "__main__":
    main()

