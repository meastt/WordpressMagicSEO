"""
Notification Utility
====================
Handles sending alerts for automated SEO tasks via webhooks (Slack/Discord).
"""

import requests
import json
import os
from typing import Dict, Optional

class SEONotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("NOTIFIER_WEBHOOK_URL")

    def send_notification(self, title: str, message: str, color: str = "#667eea"):
        """Send a formatted notification to the configured webhook."""
        if not self.webhook_url:
            print(f"⚠️ No webhook URL configured. Notification suppressed: {title}")
            return False

        # Support for Slack and Discord (both accept simple JSON usually)
        payload = {
            "text": f"*{title}*\n{message}",
            "attachments": [
                {
                    "title": title,
                    "text": message,
                    "color": color
                }
            ]
        }

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.ok
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")
            return False

    def send_audit_summary(self, site_name: str, score: int, critical: int, warnings: int):
        """Specifically formatted notification for audit completion."""
        emoji = "🟢" if score > 80 else "🟡" if score > 50 else "🔴"
        title = f"{emoji} SEO Audit Complete: {site_name}"
        message = (
            f"Health Score: *{score}/100*\n"
            f"🚨 Critical Issues: {critical}\n"
            f"⚠️ Warnings: {warnings}\n"
            f"View Details: {os.getenv('APP_URL', 'http://localhost:5001')}"
        )
        color = "#4caf50" if score > 80 else "#ff9800" if score > 50 else "#f44336"
        return self.send_notification(title, message, color)

    def send_fix_summary(self, site_name: str, total_fixed: int, failures: int = 0):
        """Specifically formatted notification for fix execution."""
        title = f"🔧 SEO Fixes Applied: {site_name}"
        message = (
            f"✅ Successfully fixed: *{total_fixed}* issues\n"
            f"❌ Failures: {failures}\n"
            f"The site should be healthier now!"
        )
        return self.send_notification(title, message, "#667eea" if failures == 0 else "#ff9800")

    def send_urgent_alert(self, site_name: str, issues: list):
        """High-priority alert for critical foundation failures."""
        title = f"🚨 URGENT: SEO Foundation Failure - {site_name}"
        issues_text = "\n".join([f"• {issue}" for issue in issues])
        message = (
            f"*Immediate action recommended!*\n"
            f"We detected critical issues that may block indexing:\n"
            f"{issues_text}\n"
            f"Please check your site settings immediately."
        )
        return self.send_notification(title, message, "#d32f2f")
