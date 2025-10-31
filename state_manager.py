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
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from utils.state_storage import StateStorage

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to DEBUG for verbose output, INFO for production


class StateManager:
    """Per-site state tracking - prevents repeating work"""
    
    def __init__(self, site_name: str, state_dir: str = None):
        """
        Initialize state manager for a specific site.

        Args:
            site_name: Domain name of the site
            state_dir: Directory to store state files (deprecated, kept for compatibility)
        """
        self.site_name = site_name
        self.storage = StateStorage()
        # Keep state_file for backward compatibility with debug code
        self.state_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"{site_name}_state.json"
        )
        self.state = self._load()
        logger.info(f"StateManager initialized for {site_name}")
    
    def _load(self):
        """Load state using simplified storage."""
        try:
            state = self.storage.load(self.site_name)
            # Ensure state has required structure
            if 'stats' not in state:
                state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
            if 'current_plan' not in state:
                state['current_plan'] = []
            logger.info(f"Loaded state for {self.site_name}: {state.get('stats', {})}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            # Return empty state on error
            return self.storage._create_empty_state(self.site_name)
    
    def save(self):
        """
        Save state using simplified storage.
        
        Raises AppError if save fails critically.
        """
        try:
            # Update timestamp
            self.state['updated_at'] = datetime.now().isoformat()
            
            # Save using storage abstraction
            self.storage.save(self.site_name, self.state)
            logger.info(f"State saved for {self.site_name}: {self.state.get('stats', {})}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            # Don't raise - allow continued operation even if save fails
            # The next save attempt may succeed
    
    def update_plan(self, actions: List[Dict]):
        """
        Store new action plan.
        
        Args:
            actions: List of action dictionaries with keys like id, action_type, url, etc.
        """
        if 'current_plan' not in self.state:
            self.state['current_plan'] = []
        if 'stats' not in self.state:
            self.state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
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
        if 'current_plan' not in self.state:
            self.state['current_plan'] = []
        if 'stats' not in self.state:
            self.state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
            
        for action in self.state['current_plan']:
            if action['id'] == action_id:
                action['status'] = 'completed'
                action['completed_at'] = datetime.now().isoformat()
                if post_id:
                    action['post_id'] = post_id
                break

        # Recalculate stats from current plan to ensure accuracy
        self.state['stats']['total_actions'] = len(self.state['current_plan'])
        self.state['stats']['completed'] = len([a for a in self.state['current_plan'] if a.get('status') == 'completed'])
        self.state['stats']['pending'] = len([a for a in self.state['current_plan'] if a.get('status') != 'completed'])

        logger.debug(f"Marked {action_id} as completed")
        logger.debug(f"Updated stats: {self.state['stats']}")
        self.save()
    
    def get_pending_actions(self, limit: Optional[int] = None):
        """
        Get pending actions sorted by priority.
        
        Args:
            limit: Maximum number of actions to return
        
        Returns:
            list: Pending actions sorted by priority_score (highest first)
        """
        if 'current_plan' not in self.state:
            return []
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
        if 'stats' not in self.state:
            return {'total_actions': 0, 'completed': 0, 'pending': 0}
        return self.state['stats'].copy()

    def save_analysis_result(self, analysis: Dict):
        """
        Save full analysis result for later export/reference.

        Args:
            analysis: Full analysis dictionary with action_plan, summary, niche_insights, etc.
        """
        self.state['last_analysis'] = {
            'timestamp': datetime.now().isoformat(),
            'result': analysis
        }
        self.save()

    def get_analysis_result(self):
        """
        Get the last saved analysis result.

        Returns:
            dict or None: Last analysis result if available
        """
        return self.state.get('last_analysis', {}).get('result')

    def clear_state(self):
        """Clear all state (use with caution)"""
        self.state = self.storage._create_empty_state(self.site_name)
        self.save()
