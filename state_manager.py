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
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class StateManager:
    """Per-site state tracking - prevents repeating work"""
    
    def __init__(self, site_name: str, state_dir: str = None):
        """
        Initialize state manager for a specific site.

        Args:
            site_name: Domain name of the site
            state_dir: Directory to store state files (default: persistent location)
        """
        print(f"DEBUG INIT: StateManager.__init__ called for {site_name}")
        self.site_name = site_name
        print(f"DEBUG INIT: Site name set")

        # Use persistent directory for Vercel serverless
        if state_dir is None:
            print(f"DEBUG INIT: state_dir is None, determining default")
            # For Vercel, we need to use a location that persists between deployments
            # Use the project root directory which is persistent in Vercel
            state_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"DEBUG INIT: state_dir set to {state_dir}")

            # Ensure the directory exists
            print(f"DEBUG INIT: Creating directory if needed")
            os.makedirs(state_dir, exist_ok=True)
            print(f"DEBUG INIT: Directory created/verified")

        self.state_file = os.path.join(state_dir, f"{site_name}_state.json")
        print(f"DEBUG INIT: state_file set to {self.state_file}")
        print(f"DEBUG INIT: About to call self._load()")
        self.state = self._load()
        print(f"DEBUG INIT: StateManager.__init__ completed successfully")
    
    def _load(self):
        """Load state from persistent storage or file, create new state structure if needed"""
        print(f"DEBUG LOAD: _load() called for {self.site_name}")

        # Try to load from persistent storage first (for Vercel)
        print(f"DEBUG LOAD: Calling _load_from_persistent_storage()")
        try:
            state = self._load_from_persistent_storage()
            print(f"DEBUG LOAD: _load_from_persistent_storage() returned, state is {'None' if state is None else 'loaded'}")
            if state:
                print(f"Loaded state from persistent storage for {self.site_name}: {state.get('stats', {})}")
                return state
        except Exception as e:
            print(f"DEBUG LOAD: Exception in _load_from_persistent_storage(): {e}")
            import traceback
            print(f"DEBUG LOAD: Traceback: {traceback.format_exc()}")

        # Fallback to file-based storage (for local development)
        print(f"DEBUG LOAD: Checking for file at {self.state_file}")
        if os.path.exists(self.state_file):
            print(f"DEBUG LOAD: File exists, attempting to load")
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    print(f"Loaded state from file for {self.site_name}: {state.get('stats', {})}")
                    return state
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load state file, creating new state: {e}")
        else:
            print(f"DEBUG LOAD: File does not exist")

        print(f"Creating new state for {self.site_name}")
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
    
    def _load_from_persistent_storage(self):
        """Load state from GitHub Gist (persistent storage for Vercel)"""
        print(f"DEBUG PERSISTENT: _load_from_persistent_storage() entered for {self.site_name}")
        try:
            print(f"DEBUG PERSISTENT: Inside try block")
            # Use GitHub Gist as persistent storage
            print(f"DEBUG PERSISTENT: Building env_key")
            env_key = f"GIST_ID_{self.site_name.replace('.', '_').replace('-', '_').upper()}"
            print(f"DEBUG PERSISTENT: Getting gist_id from env")
            gist_id = os.getenv(env_key)
            print(f"DEBUG PERSISTENT: Getting github_token from env")
            github_token = os.getenv("GITHUB_TOKEN")

            print(f"DEBUG STATE: Loading for {self.site_name}")
            print(f"DEBUG STATE: Env key: {env_key}")
            print(f"DEBUG STATE: Gist ID: {gist_id}")
            print(f"DEBUG STATE: GitHub token: {'SET' if github_token else 'NOT SET'}")
            
            if not gist_id:
                print(f"DEBUG STATE: No Gist ID found for {self.site_name}")
                return None
            
            if gist_id == "new":
                print(f"DEBUG STATE: Gist ID is 'new', no existing state")
                return None
            
            # Load from Gist with short timeout for Vercel
            print(f"DEBUG STATE: About to fetch from Gist API...")
            print(f"DEBUG STATE: URL: https://api.github.com/gists/{gist_id}")
            print(f"DEBUG STATE: Timeout: 5 seconds")
            try:
                print(f"DEBUG STATE: Calling requests.get()...")
                response = requests.get(
                    f"https://api.github.com/gists/{gist_id}",
                    timeout=5,  # Shorter timeout for serverless
                    headers={'Accept': 'application/vnd.github.v3+json'}
                )
                print(f"DEBUG STATE: requests.get() returned")
                print(f"DEBUG STATE: Gist response status: {response.status_code}")
            except requests.exceptions.Timeout:
                print(f"DEBUG STATE: Gist API request timed out after 5 seconds")
                return None
            except requests.exceptions.RequestException as req_err:
                print(f"DEBUG STATE: Gist API request failed: {req_err}")
                return None
            
            if response.status_code == 200:
                gist_data = response.json()
                file_key = f"{self.site_name}_state.json"
                print(f"DEBUG STATE: Looking for file key: {file_key}")
                print(f"DEBUG STATE: Available files in Gist: {list(gist_data.get('files', {}).keys())}")

                if file_key not in gist_data.get('files', {}):
                    print(f"DEBUG STATE: File {file_key} not found in Gist")
                    return None

                state_content = gist_data['files'][file_key]['content']
                state = json.loads(state_content)
                print(f"DEBUG STATE: Loaded state from Gist: {state.get('stats', {})}")
                return state
            else:
                print(f"DEBUG STATE: Gist load failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"Could not load from persistent storage: {e}")
            return None
    
    def save(self):
        """Save state to persistent storage and file"""
        print(f"DEBUG STATE SAVE: Starting save for {self.site_name}")
        print(f"DEBUG STATE SAVE: State file: {self.state_file}")
        print(f"DEBUG STATE SAVE: State content: {self.state}")
        
        # Save to persistent storage first (for Vercel)
        self._save_to_persistent_storage()
        
        # Also save to file (for local development)
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            print(f"State saved for {self.site_name}: {self.state.get('stats', {})}")
        except IOError as e:
            print(f"Warning: Could not save state file: {e}")
    
    def _save_to_persistent_storage(self):
        """Save state to GitHub Gist (persistent storage for Vercel)"""
        try:
            # Use GitHub Gist as persistent storage
            env_key = f"GIST_ID_{self.site_name.replace('.', '_').replace('-', '_').upper()}"
            gist_id = os.getenv(env_key)
            github_token = os.getenv("GITHUB_TOKEN")
            
            print(f"DEBUG GIST SAVE: Env key: {env_key}")
            print(f"DEBUG GIST SAVE: Gist ID: {gist_id}")
            print(f"DEBUG GIST SAVE: GitHub token: {'SET' if github_token else 'NOT SET'}")
            
            if not gist_id or not github_token:
                print(f"No Gist ID or GitHub token configured for {self.site_name}")
                return
            
            # Save to Gist
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            files = {
                f"{self.site_name}_state.json": {
                    "content": json.dumps(self.state, indent=2)
                }
            }
            
            if gist_id == "new":
                # Create new Gist
                data = {
                    "description": f"State for {self.site_name}",
                    "public": False,
                    "files": files
                }
                response = requests.post("https://api.github.com/gists", 
                                       headers=headers, json=data, timeout=10)
                if response.status_code == 201:
                    new_gist_id = response.json()['id']
                    print(f"Created new Gist {new_gist_id} for {self.site_name}")
            else:
                # Update existing Gist
                data = {"files": files}
                response = requests.patch(f"https://api.github.com/gists/{gist_id}", 
                                        headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    print(f"Updated Gist {gist_id} for {self.site_name}")
                    
        except Exception as e:
            print(f"Could not save to persistent storage: {e}")
    
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
        
        # Recalculate stats from current plan to ensure accuracy
        self.state['stats']['total_actions'] = len(self.state['current_plan'])
        self.state['stats']['completed'] = len([a for a in self.state['current_plan'] if a.get('status') == 'completed'])
        self.state['stats']['pending'] = len([a for a in self.state['current_plan'] if a.get('status') != 'completed'])
        
        print(f"DEBUG MARK_COMPLETED: Marked {action_id} as completed")
        print(f"DEBUG MARK_COMPLETED: Updated stats: {self.state['stats']}")
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
