"""
Automation Scheduler
====================
Manages recurring SEO audits and auto-fixes.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.state_manager import StateManager
from utils.notifications import SEONotifier
from seo.technical_auditor import TechnicalSEOAuditor
from seo.issue_grouper import IssueGrouper
from seo.issue_fixer import SEOIssueFixer

class SEOScheduler:
    def __init__(self, sites_config: Dict):
        self.sites_config = sites_config
        self.notifier = SEONotifier()
        self.settings_file = os.path.join(os.getcwd(), "automation_settings.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving automation settings: {e}")

    def get_site_settings(self, site_name: str) -> Dict:
        """Get automation settings for a specific site."""
        default = {
            "enabled": False,
            "auto_fix": False,
            "frequency": "weekly",  # "daily", "weekly", "monthly"
            "last_run": None,
            "next_run": None,
            "webhook_url": None
        }
        return self.settings.get(site_name, default).copy() if site_name in self.settings else default

    def update_site_settings(self, site_name: str, settings: Dict):
        """Update automation settings for a site."""
        current = self.get_site_settings(site_name)
        current.update(settings)
        
        # Calculate next run if enabled and not set
        if current["enabled"] and not current["next_run"]:
            current["next_run"] = self._calculate_next_run(current["frequency"])
            
        self.settings[site_name] = current
        self._save_settings()

    def _calculate_next_run(self, frequency: str) -> str:
        now = datetime.now()
        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "monthly":
            next_run = now + timedelta(days=30)
        else: # weekly
            next_run = now + timedelta(days=7)
        
        # Set to 3 AM for less traffic interference
        next_run = next_run.replace(hour=3, minute=0, second=0, microsecond=0)
        return next_run.isoformat()

    def get_pending_tasks(self) -> List[Dict]:
        """Identify which sites need an audit or fix based on schedule."""
        now = datetime.now()
        pending = []
        
        for site_name, config in self.sites_config.items():
            settings = self.get_site_settings(site_name)
            if not settings["enabled"]:
                continue
                
            next_run_str = settings.get("next_run")
            if not next_run_str:
                # If enabled but no next_run, it's pending (likely just enabled)
                pending.append({
                    "site_name": site_name,
                    "type": "audit_and_fix" if settings["auto_fix"] else "audit_only",
                    "settings": settings,
                    "config": config
                })
                continue
                
            next_run = datetime.fromisoformat(next_run_str)
            if now >= next_run:
                pending.append({
                    "site_name": site_name,
                    "type": "audit_and_fix" if settings["auto_fix"] else "audit_only",
                    "settings": settings,
                    "config": config
                })
        
        return pending

    def process_automation(self, force_site: Optional[str] = None):
        """Run pending automation tasks across all sites."""
        tasks = []
        if force_site:
            if force_site in self.sites_config:
                settings = self.get_site_settings(force_site)
                tasks = [{
                    "site_name": force_site,
                    "type": "audit_and_fix" if settings["auto_fix"] else "audit_only",
                    "settings": settings,
                    "config": self.sites_config[force_site]
                }]
        else:
            tasks = self.get_pending_tasks()

        results = []
        for task in tasks:
            site_name = task["site_name"]
            site_url = task["config"].get("url")
            settings = task["settings"]
            
            if not site_url:
                continue

            print(f"🤖 Processing automation for {site_name} ({task['type']})...")
            
            try:
                # 1. Run Audit
                auditor = TechnicalSEOAuditor(site_url=site_url)
                audit_result = auditor.audit_site(max_urls=100)
                
                # Group issues
                summary = IssueGrouper.get_summary(audit_result)
                score = 100 - (summary.get('critical_count', 0) * 5) - (summary.get('warning_count', 0) * 1)
                score = max(0, min(100, score))
                
                fixed_count = 0
                failures = 0
                
                # 2. Run Fixes if enabled
                if task["type"] == "audit_and_fix":
                    wp_user = task["config"].get("wp_username")
                    wp_pass = task["config"].get("wp_app_password")
                    
                    if wp_user and wp_pass:
                        fixer = SEOIssueFixer(
                            site_url=site_url,
                            wp_username=wp_user,
                            wp_app_password=wp_pass
                        )
                        
                        fixable, _ = IssueGrouper.get_fixable_vs_manual(audit_result)
                        priority_issues = ['h1_presence', 'title_presence', 'meta_description_presence']
                        
                        for issue_type in priority_issues:
                            if issue_type in fixable:
                                urls = fixable[issue_type][:10] # Batch limit
                                if urls:
                                    fix_res = fixer.fix_issue(issue_type, 'onpage', urls)
                                    fixed_count += fix_res.get('fixed_count', 0)
                                    failures += fix_res.get('error_count', 0)
                    else:
                        print(f"  ⚠️ No WordPress credentials for {site_name}. Skipping fixes.")

                # 3. Send Notification
                # Set temporary webhook override if provided in settings
                old_webhook = os.getenv("NOTIFIER_WEBHOOK_URL")
                if settings.get("webhook_url"):
                    os.environ["NOTIFIER_WEBHOOK_URL"] = settings["webhook_url"]
                    self.notifier.webhook_url = settings["webhook_url"]

                # 3. Check for Foundation Failures (High Priority Alerts)
                foundation_issues = self._get_foundation_failures(audit_result, site_url)
                if foundation_issues:
                    self.notifier.send_urgent_alert(site_name, foundation_issues)

                self.notifier.send_audit_summary(
                    site_name, 
                    score, 
                    summary.get('critical_count', 0), 
                    summary.get('warning_count', 0)
                )
                
                if fixed_count > 0 or failures > 0:
                    self.notifier.send_fix_summary(site_name, fixed_count, failures)

                # Restore original webhook
                if old_webhook:
                    os.environ["NOTIFIER_WEBHOOK_URL"] = old_webhook
                    self.notifier.webhook_url = old_webhook

                # 4. Update schedule
                settings["last_run"] = datetime.now().isoformat()
                settings["next_run"] = self._calculate_next_run(settings["frequency"])
                self.settings[site_name] = settings
                self._save_settings()
                
                self._log_automation_run(site_name, "success", score=score, fixed=fixed_count)
                results.append({
                    "site": site_name,
                    "status": "success",
                    "score": score,
                    "fixed": fixed_count,
                    "next_run": settings["next_run"]
                })
                
            except Exception as e:
                print(f"❌ Automation failed for {site_name}: {e}")
                self._log_automation_run(site_name, "error", error=str(e))
                results.append({
                    "site": site_name,
                    "status": "error",
                    "error": str(e)
                })
            
        return results

    def _get_foundation_failures(self, audit_result: Dict, site_url: str) -> List[str]:
        """Detect critical foundation failures like noindex or robots block."""
        failures = []
        for url_data in audit_result.get("urls", []):
            # Only check homepage for global foundation issues (usually first URL)
            if url_data["url"].rstrip("/") == site_url.rstrip("/"):
                # Check for HTTP errors
                if url_data.get("status_code", 0) >= 400:
                    failures.append(f"Homepage returned status {url_data['status_code']}")
                
                issues = url_data.get("issues", {})
                for cat in issues.values():
                    for issue in cat:
                        if issue.get("status") == "critical" and issue.get("check_name") in ["noindex", "robots_txt", "ssl_https"]:
                            # Special priority for noindex/robots
                            failures.append(f"CRITICAL: {issue['message']}")
                break
        return failures

    def _log_automation_run(self, site_name: str, status: str, **kwargs):
        """Log the automation run to automation_runs.json."""
        log_file = os.path.join(os.getcwd(), "automation_runs.json")
        runs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    runs = json.load(f)
            except:
                pass
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "site": site_name,
            "status": status,
            **kwargs
        }
        runs.insert(0, entry)
        runs = runs[:100] # Keep last 100 runs
        
        try:
            with open(log_file, 'w') as f:
                json.dump(runs, f, indent=2)
        except:
            pass

