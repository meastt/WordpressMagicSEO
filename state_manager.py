"""
State Manager - Per-Site State Tracking
----------------------------------------
Prevents repeating work by tracking:
- Completed actions
- Cached niche research
- Current action plan
- Execution statistics
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class StateManager:
    """Per-site state tracking - prevents repeating work"""
    
    def __init__(self, site_name: str, state_dir: str = "/tmp"):
        """
        Initialize state manager for a specific site.
        
        Args:
            site_name: Domain name of the site
            state_dir: Directory to store state files (default: /tmp)
        """
        self.site_name = site_name
        self.state_file = os.path.join(state_dir, f"{site_name}_state.json")
        self.state = self._load()
    
    def _load(self):
        """Load state from disk or create new state structure"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load state file, creating new state: {e}")
        
        return {
            "site_name": self.site_name,
            "niche_research": None,
            "current_plan": [],
            "stats": {
                "total_actions": 0,
                "completed": 0,
                "pending": 0
            }
        }
    
    def save(self):
        """Save state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save state file: {e}")
    
    def update_plan(self, actions: List[Dict]):
        """
        Store new action plan.
        
        Args:
            actions: List of action dictionaries with keys like id, action_type, url, etc.
        """
        self.state['current_plan'] = actions
        self.state['stats']['total_actions'] = len(actions)
        self.state['stats']['pending'] = len([a for a in actions if a.get('status') != 'completed'])
        self.state['stats']['completed'] = len([a for a in actions if a.get('status') == 'completed'])
        self.save()
    
    def mark_completed(self, action_id: str, post_id: Optional[int] = None):
        """
        Mark an action as completed.
        
        Args:
            action_id: Unique identifier of the action
            post_id: WordPress post ID if applicable
        """
        for action in self.state['current_plan']:
            if action['id'] == action_id:
                action['status'] = 'completed'
                action['completed_at'] = datetime.now().isoformat()
                if post_id:
                    action['post_id'] = post_id
                break
        
        self.state['stats']['completed'] += 1
        self.state['stats']['pending'] = max(0, self.state['stats']['pending'] - 1)
        self.save()
    
    def get_pending_actions(self, limit: Optional[int] = None):
        """
        Get pending actions sorted by priority.
        
        Args:
            limit: Maximum number of actions to return
        
        Returns:
            list: Pending actions sorted by priority_score (highest first)
        """
        pending = [a for a in self.state['current_plan'] if a.get('status') != 'completed']
        pending.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        return pending[:limit] if limit else pending
    
    def cache_niche_research(self, report: str, cache_days: int = 30):
        """
        Cache niche research report to avoid repeated API calls.
        
        Args:
            report: JSON string of niche research report
            cache_days: Number of days to cache (default: 30)
        """
        self.state['niche_research'] = {
            'report': report,
            'cached_until': (datetime.now() + timedelta(days=cache_days)).isoformat()
        }
        self.save()
    
    def get_niche_research(self):
        """
        Get cached niche research if still valid.
        
        Returns:
            str or None: Cached report JSON string if valid, None if expired or not cached
        """
        if not self.state.get('niche_research'):
            return None
        
        cached_until = datetime.fromisoformat(self.state['niche_research']['cached_until'])
        if datetime.now() < cached_until:
            return self.state['niche_research']['report']
        
        return None
    
    def get_stats(self):
        """
        Get execution statistics.
        
        Returns:
            dict: Statistics with keys: total_actions, completed, pending
        """
        return self.state['stats'].copy()
    
    def clear_state(self):
        """Clear all state (use with caution)"""
        self.state = {
            "site_name": self.site_name,
            "niche_research": None,
            "current_plan": [],
            "stats": {
                "total_actions": 0,
                "completed": 0,
                "pending": 0
            }
        }
        self.save()
