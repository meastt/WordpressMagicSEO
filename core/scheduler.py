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
        return self.settings.get(site_name, default)

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
                continue
                
            next_run = datetime.fromisoformat(next_run_str)
            if now >= next_run:
                pending.append({
                    "site_name": site_name,
                    "type": "audit_and_fix" if settings["auto_fix"] else "audit_only",
                    "settings": settings
                })
        
        return pending

    def process_automation(self, force_site: Optional[str] = None):
        """Run pending automation tasks across all sites."""
        tasks = self.get_pending_tasks()
        if force_site:
            # For testing/manual trigger
            tasks = [{
                "site_name": force_site,
                "type": "audit_and_fix",
                "settings": self.get_site_settings(force_site)
            }]

        results = []
        for task in tasks:
            site_name = task["site_name"]
            print(f"🤖 Processing automation for {site_name} ({task['type']})...")
            
            # This logic will be triggered by an API endpoint typically
            # But we can store the result and update the schedule
            settings = task["settings"]
            settings["last_run"] = datetime.now().isoformat()
            settings["next_run"] = self._calculate_next_run(settings["frequency"])
            self.settings[site_name] = settings
            self._save_settings()
            
            results.append({
                "site": site_name,
                "status": "triggered",
                "next_run": settings["next_run"]
            })
            
        return results
