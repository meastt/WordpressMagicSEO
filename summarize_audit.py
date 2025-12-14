#!/usr/bin/env python3
"""
Summarize SEO Audit Results
============================
Reads audit.json and provides a human-readable summary of issues.
"""

import json
import sys
from collections import defaultdict
from typing import Dict, List


def load_audit(file_path: str = "audit.json") -> Dict:
    """Load audit results from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def summarize_audit(audit_results: Dict):
    """Generate and print comprehensive summary."""
    print("=" * 80)
    print("SEO AUDIT SUMMARY")
    print("=" * 80)
    print(f"Site: {audit_results.get('site_url', 'Unknown')}")
    print(f"Audit Date: {audit_results.get('audit_date', 'Unknown')}")
    print(f"Total URLs Checked: {audit_results.get('total_urls_checked', 0)}")
    print()
    
    # Overall summary
    summary = audit_results.get('summary', {})
    print("📊 OVERALL SUMMARY")
    print("-" * 80)
    print(f"  ✅ Passed Checks: {summary.get('passed', 0)}")
    print(f"  ⚠️  Warnings: {summary.get('warnings', 0)}")
    print(f"  🔴 Critical Issues: {summary.get('critical_issues', 0)}")
    print()
    
    # Breakdown by category
    category_stats = defaultdict(lambda: {'critical': 0, 'warning': 0, 'optimal': 0, 'info': 0})
    issue_counts = defaultdict(int)
    urls_with_issues = defaultdict(int)
    
    for url_data in audit_results.get('urls', []):
        url = url_data.get('url', 'Unknown')
        has_critical = False
        has_warning = False
        
        for category, issues in url_data.get('issues', {}).items():
            for issue in issues:
                status = issue.get('status', 'unknown')
                check_name = issue.get('check_name', 'unknown')
                
                category_stats[category][status] += 1
                issue_counts[f"{category}.{check_name}"] += 1
                
                if status == 'critical':
                    has_critical = True
                elif status == 'warning':
                    has_warning = True
        
        if has_critical:
            urls_with_issues['critical'] += 1
        if has_warning:
            urls_with_issues['warning'] += 1
    
    # Category breakdown
    print("📋 BREAKDOWN BY CATEGORY")
    print("-" * 80)
    category_names = {
        'technical': '🔧 Technical Foundation',
        'onpage': '📝 On-Page SEO',
        'links': '🔗 Links & Structure',
        'images': '🖼️  Images & Media',
        'performance': '⚡ Performance',
        'schema': '📱 Schema & Social'
    }
    
    for category, stats in sorted(category_stats.items()):
        name = category_names.get(category, category.title())
        total = sum(stats.values())
        critical = stats.get('critical', 0)
        warning = stats.get('warning', 0)
        optimal = stats.get('optimal', 0)
        
        print(f"\n{name}:")
        print(f"  Total Checks: {total}")
        print(f"  ✅ Optimal: {optimal} ({optimal/total*100:.1f}%)" if total > 0 else "  ✅ Optimal: 0")
        print(f"  ⚠️  Warnings: {warning} ({warning/total*100:.1f}%)" if total > 0 else "  ⚠️  Warnings: 0")
        print(f"  🔴 Critical: {critical} ({critical/total*100:.1f}%)" if total > 0 else "  🔴 Critical: 0")
    
    print()
    
    # Most common issues
    print("🔍 TOP 10 MOST COMMON ISSUES")
    print("-" * 80)
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    
    for i, (issue_key, count) in enumerate(sorted_issues[:10], 1):
        category, check = issue_key.split('.', 1)
        print(f"  {i:2d}. {check} ({category}): {count} occurrences")
    
    print()
    
    # URLs with most issues
    print("🌐 URLS WITH MOST ISSUES")
    print("-" * 80)
    url_issue_counts = []
    
    for url_data in audit_results.get('urls', []):
        url = url_data.get('url', 'Unknown')
        critical_count = 0
        warning_count = 0
        
        for category, issues in url_data.get('issues', {}).items():
            for issue in issues:
                status = issue.get('status', 'unknown')
                if status == 'critical':
                    critical_count += 1
                elif status == 'warning':
                    warning_count += 1
        
        if critical_count > 0 or warning_count > 0:
            url_issue_counts.append((url, critical_count, warning_count))
    
    # Sort by critical first, then warnings
    url_issue_counts.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    for i, (url, critical, warning) in enumerate(url_issue_counts[:10], 1):
        print(f"  {i:2d}. {url}")
        print(f"      🔴 {critical} critical, ⚠️  {warning} warnings")
    
    print()
    
    # Critical issues breakdown
    print("🔴 CRITICAL ISSUES BREAKDOWN")
    print("-" * 80)
    critical_by_check = defaultdict(int)
    
    for url_data in audit_results.get('urls', []):
        for category, issues in url_data.get('issues', {}).items():
            for issue in issues:
                if issue.get('status') == 'critical':
                    check_name = issue.get('check_name', 'unknown')
                    critical_by_check[f"{category}.{check_name}"] += 1
    
    if critical_by_check:
        for check, count in sorted(critical_by_check.items(), key=lambda x: x[1], reverse=True):
            category, check_name = check.split('.', 1)
            print(f"  • {check_name} ({category}): {count} URLs affected")
    else:
        print("  ✅ No critical issues found!")
    
    print()
    print("=" * 80)
    print("💡 TIP: Use --detailed flag to see full issue details per URL")
    print("=" * 80)


def show_detailed_issues(audit_results: Dict):
    """Show detailed issues for each URL."""
    print("=" * 80)
    print("DETAILED ISSUES BY URL")
    print("=" * 80)
    print()
    
    for url_data in audit_results.get('urls', []):
        url = url_data.get('url', 'Unknown')
        has_issues = False
        
        # Count issues
        critical_count = 0
        warning_count = 0
        
        for category, issues in url_data.get('issues', {}).items():
            for issue in issues:
                if issue.get('status') == 'critical':
                    critical_count += 1
                    has_issues = True
                elif issue.get('status') == 'warning':
                    warning_count += 1
                    has_issues = True
        
        if has_issues:
            print(f"🌐 {url}")
            print(f"   Status: {url_data.get('status_code', 'Unknown')} | "
                  f"Fetch Time: {url_data.get('fetch_time', 0):.2f}s")
            print(f"   Issues: 🔴 {critical_count} critical, ⚠️  {warning_count} warnings")
            print()
            
            for category, issues in url_data.get('issues', {}).items():
                category_issues = [i for i in issues if i.get('status') in ['critical', 'warning']]
                if category_issues:
                    print(f"   {category.upper()}:")
                    for issue in category_issues:
                        status_icon = "🔴" if issue.get('status') == 'critical' else "⚠️"
                        print(f"     {status_icon} {issue.get('check_name', 'unknown')}: {issue.get('message', 'No message')}")
                    print()
            
            print("-" * 80)
            print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Summarize SEO audit results from audit.json"
    )
    parser.add_argument(
        'file',
        nargs='?',
        default='audit.json',
        help='Path to audit.json file (default: audit.json)'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed issues for each URL'
    )
    
    args = parser.parse_args()
    
    audit_results = load_audit(args.file)
    
    if args.detailed:
        show_detailed_issues(audit_results)
    else:
        summarize_audit(audit_results)


if __name__ == "__main__":
    main()

