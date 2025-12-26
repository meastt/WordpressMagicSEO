
import json
import time
import os
import sys
from seo.technical_auditor import TechnicalSEOAuditor
from seo.issue_grouper import IssueGrouper
from seo.issue_fixer import SEOIssueFixer

def fix_batch_1():
    site_url = "https://tigertribe.net"
    # Use the credentials provided by the user
    wp_username = "meastt09@gmail.com"
    wp_app_password = "q2dX q7cQ LPz8 vmTV IqvJ uJ80"
    
    print(f"🚀 Starting Batch 1 Fixes for {site_url}")
    
    # 1. Load baseline audit
    audit_file = "baseline_audit_tigertribe.json"
    if not os.path.exists(audit_file):
        print(f"❌ Audit file {audit_file} not found.")
        return
        
    with open(audit_file, 'r') as f:
        audit_data = json.load(f)
        
    # 2. Identify fixable issues
    fixable, _ = IssueGrouper.get_fixable_vs_manual(audit_data)
    
    # Batch 1 targets: Meta Description and Title polish
    targets = ['meta_description_presence', 'title_length']
    
    fixer = SEOIssueFixer(
        site_url=site_url,
        wp_username=wp_username,
        wp_app_password=wp_app_password
    )
    
    for issue_type in targets:
        urls = fixable.get(issue_type, [])
        if not urls:
            print(f"✅ No issues of type '{issue_type}' found.")
            continue
            
        print(f"🛠️ Fixing '{issue_type}' for {len(urls)} URLs...")
        
        # We'll fix them one by one for maximum safety and logging
        for url in urls:
            print(f"  > Fixing: {url}")
            try:
                result = fixer.fix_issue(
                    issue_type=issue_type,
                    category='onpage',
                    urls=[url]
                )
                if result.get('fixed_count', 0) > 0:
                    print(f"    ✅ Fixed!")
                else:
                    print(f"    ⚠️ Not fixed: {result.get('error', 'Unknown reason')}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
            
            # Safety delay on live site
            time.sleep(2)
            
    print("✅ Batch 1 Complete!")

if __name__ == "__main__":
    fix_batch_1()
