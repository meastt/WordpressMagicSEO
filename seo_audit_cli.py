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

    # Fix arguments
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix identified issues"
    )
    
    parser.add_argument(
        "--fix-type",
        nargs="+",
        help="Specific issue types to fix (e.g. h1_presence schema_markup)"
    )
    
    parser.add_argument(
        "--username",
        help="WordPress username for fixing"
    )
    
    parser.add_argument(
        "--app-password",
        help="WordPress application password for fixing"
    )

    parser.add_argument(
        "--audit-file",
        help="Load issues from existing audit JSON file instead of re-crawling"
    )
    
    args = parser.parse_args()
    
    audit_results = {}
    
    # Load or Run audit
    if args.audit_file:
        import json
        import os
        if not os.path.exists(args.audit_file):
            print(f"❌ Audit file {args.audit_file} not found.")
            return
        print(f"📂 Loading audit from: {args.audit_file}")
        with open(args.audit_file, 'r') as f:
            audit_results = json.load(f)
    else:
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
            
        # Output audit report if not loaded from file
        generator = SEOReportGenerator(audit_results)
        if args.output == "json":
            report = generator.generate_json()
        elif args.output == "csv":
            report = generator.generate_csv()
        elif args.output == "html":
            report = generator.generate_html()
        
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ Report saved to: {args.output_file}")
        else:
            # print(report) # Suppress full report when fixing unless asked? Keep standard behavior.
            pass

    # Execute Fixes
    if args.fix:
        if not args.username or not args.app_password:
            print("❌ Error: --username and --app-password are required for fixing.")
            return

        from seo.issue_grouper import IssueGrouper
        from seo.issue_fixer import SEOIssueFixer
        
        print("\n" + "=" * 80)
        print("FIX EXECUTION")
        print("=" * 80)
        
        fixable, _ = IssueGrouper.get_fixable_vs_manual(audit_results)
        
        targets = args.fix_type if args.fix_type else fixable.keys()
        
        fixer = SEOIssueFixer(
            site_url=args.site_url,
            wp_username=args.username,
            wp_app_password=args.app_password
        )
        
        total_fixed = 0
        
        for issue_type in targets:
            urls = fixable.get(issue_type, [])
            if not urls:
                print(f"ℹ️  No issues of type '{issue_type}' found.")
                continue
                
            print(f"🛠️ Fixing '{issue_type}' for {len(urls)} URLs...")
            
            # Use batch fixing from IssueFixer if available, or loop
            # Here we loop for better visibility as per batch script
            import time
            for url in urls:
                print(f"  > Fixing: {url}")
                try:
                    result = fixer.fix_issue(
                        issue_type=issue_type,
                        category='onpage', # Default assumption, fixer might handle others
                        urls=[url]
                    )
                    if result.get('fixed_count', 0) > 0:
                        print(f"    ✅ Fixed!")
                        total_fixed += 1
                    else:
                        error = result.get('error', 'Unknown reason')
                        print(f"    ⚠️ Not fixed: {error}")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                
                # Rate limit safety
                time.sleep(1.0)
                
        print(f"\n✅ Fix Execution Complete. Total fixed: {total_fixed}")


if __name__ == "__main__":
    main()

