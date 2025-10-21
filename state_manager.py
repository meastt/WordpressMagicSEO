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
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
            state_dir: Directory to store state files (default: persistent location)
        """
        logger.debug(f"StateManager.__init__ called for {site_name}")
        self.site_name = site_name
        logger.debug("Site name set")

        # Use persistent directory for Vercel serverless
        if state_dir is None:
            logger.debug("state_dir is None, determining default")
            # For Vercel, we need to use a location that persists between deployments
            # Use the project root directory which is persistent in Vercel
            state_dir = os.path.dirname(os.path.abspath(__file__))
            logger.debug(f"state_dir set to {state_dir}")

            # Ensure the directory exists
            logger.debug("Creating directory if needed")
            os.makedirs(state_dir, exist_ok=True)
            logger.debug("Directory created/verified")

        self.state_file = os.path.join(state_dir, f"{site_name}_state.json")
        logger.debug(f"state_file set to {self.state_file}")
        logger.debug("About to call self._load()")
        self.state = self._load()
        logger.debug("StateManager.__init__ completed successfully")
    
    def _load(self):
        """Load state from persistent storage or file, create new state structure if needed"""
        logger.debug(f"_load() called for {self.site_name}")

        # Try to load from persistent storage first (for Vercel)
        logger.debug("Calling _load_from_persistent_storage()")
        try:
            state = self._load_from_persistent_storage()
            logger.debug(f"_load_from_persistent_storage() returned, state is {'None' if state is None else 'loaded'}")
            if state:
                logger.info(f"Loaded state from persistent storage for {self.site_name}: {state.get('stats', {})}")
                return state
        except Exception as e:
            logger.debug(f"Exception in _load_from_persistent_storage(): {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")

        # Fallback to file-based storage (for local development)
        logger.debug(f"Checking for file at {self.state_file}")
        if os.path.exists(self.state_file):
            logger.debug("File exists, attempting to load")
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded state from file for {self.site_name}: {state.get('stats', {})}")
                    return state
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load state file, creating new state: {e}")
        else:
            logger.debug("File does not exist")

        logger.info(f"Creating new state for {self.site_name}")
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
        logger.debug(f"_load_from_persistent_storage() entered for {self.site_name}")
        try:
            logger.debug("Inside try block")
            # Use GitHub Gist as persistent storage
            logger.debug("Building env_key")
            env_key = f"GIST_ID_{self.site_name.replace('.', '_').replace('-', '_').upper()}"
            logger.debug("Getting gist_id from env")
            gist_id = os.getenv(env_key)
            logger.debug("Getting github_token from env")
            github_token = os.getenv("GITHUB_TOKEN")

            logger.debug(f"Loading for {self.site_name}")
            logger.debug(f"Env key: {env_key}")
            logger.debug(f"Gist ID: {gist_id}")
            logger.debug(f"GitHub token: {'SET' if github_token else 'NOT SET'}")

            if not gist_id:
                logger.debug(f"No Gist ID found for {self.site_name}")
                return None

            if gist_id == "new":
                logger.debug("Gist ID is 'new', no existing state")
                return None

            # Load from Gist with short timeout for Vercel
            logger.debug("About to fetch from Gist API...")
            logger.debug(f"URL: https://api.github.com/gists/{gist_id}")
            logger.debug("Timeout: 5 seconds")
            try:
                logger.debug("Calling requests.get()...")
                response = requests.get(
                    f"https://api.github.com/gists/{gist_id}",
                    timeout=5,  # Shorter timeout for serverless
                    headers={'Accept': 'application/vnd.github.v3+json'}
                )
                logger.debug("requests.get() returned")
                logger.debug(f"Gist response status: {response.status_code}")
            except requests.exceptions.Timeout:
                logger.debug("Gist API request timed out after 5 seconds")
                return None
            except requests.exceptions.RequestException as req_err:
                logger.debug(f"Gist API request failed: {req_err}")
                return None

            if response.status_code == 200:
                gist_data = response.json()
                file_key = f"{self.site_name}_state.json"
                logger.debug(f"Looking for file key: {file_key}")
                logger.debug(f"Available files in Gist: {list(gist_data.get('files', {}).keys())}")

                if file_key not in gist_data.get('files', {}):
                    logger.debug(f"File {file_key} not found in Gist")
                    return None

                state_content = gist_data['files'][file_key]['content']
                state = json.loads(state_content)
                logger.debug(f"Loaded state from Gist: {state.get('stats', {})}")
                return state
            else:
                logger.debug(f"Gist load failed: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Could not load from persistent storage: {e}")
            return None
    
    def save(self):
        """
        Save state to persistent storage and file.

        Attempts to save to both GitHub Gist (persistent) and local file.
        Raises exception if CRITICAL persistent storage fails.
        """
        logger.debug(f"Starting save for {self.site_name}")
        logger.debug(f"State file: {self.state_file}")
        logger.debug(f"State content: {self.state}")

        # Save to persistent storage first (for Vercel) - CRITICAL
        try:
            self._save_to_persistent_storage()
        except Exception as e:
            # Log the error but also try local save before re-raising
            print(f"❌ Persistent storage save failed: {e}")
            # Try local save as backup
            try:
                with open(self.state_file, 'w') as f:
                    json.dump(self.state, f, indent=2)
                print(f"✅ State saved to local file as backup: {self.state_file}")
            except IOError as file_error:
                print(f"❌ Local file save also failed: {file_error}")

            # Re-raise the original persistent storage error
            # User needs to know state persistence failed
            raise e

        # Also save to file (for local development and redundancy)
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            print(f"✅ State saved locally for {self.site_name}: {self.state.get('stats', {})}")
        except IOError as e:
            # Local save failure is less critical if persistent storage succeeded
            print(f"⚠️  Warning: Could not save state to local file: {e}")
            print(f"   (Persistent storage succeeded, so state is safe)")
    
    def _save_to_persistent_storage(self, max_retries: int = 3):
        """
        Save state to GitHub Gist (persistent storage for Vercel) with retry logic.

        Args:
            max_retries: Number of retry attempts for transient failures

        Raises:
            Exception: If save fails after all retries (CRITICAL - state not persisted)
        """
        import time

        # Use GitHub Gist as persistent storage
        env_key = f"GIST_ID_{self.site_name.replace('.', '_').replace('-', '_').upper()}"
        gist_id = os.getenv(env_key)
        github_token = os.getenv("GITHUB_TOKEN")

        logger.debug(f"Env key: {env_key}")
        logger.debug(f"Gist ID: {gist_id}")
        logger.debug(f"GitHub token: {'SET' if github_token else 'NOT SET'}")

        if not gist_id or not github_token:
            # This is OK for local development - just skip persistent storage
            logger.info(f"No Gist ID or GitHub token configured for {self.site_name} - using local storage only")
            return

        # Prepare request data
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        files = {
            f"{self.site_name}_state.json": {
                "content": json.dumps(self.state, indent=2)
            }
        }

        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                if gist_id == "new":
                    # Create new Gist
                    data = {
                        "description": f"State for {self.site_name}",
                        "public": False,
                        "files": files
                    }
                    response = requests.post(
                        "https://api.github.com/gists",
                        headers=headers,
                        json=data,
                        timeout=10
                    )

                    if response.status_code == 201:
                        new_gist_id = response.json()['id']
                        print(f"✅ Created new Gist {new_gist_id} for {self.site_name}")
                        return  # Success
                    else:
                        raise Exception(f"Gist creation failed: {response.status_code} - {response.text}")
                else:
                    # Update existing Gist
                    data = {"files": files}
                    response = requests.patch(
                        f"https://api.github.com/gists/{gist_id}",
                        headers=headers,
                        json=data,
                        timeout=10
                    )

                    if response.status_code == 200:
                        print(f"✅ Updated Gist {gist_id} for {self.site_name}")
                        return  # Success
                    else:
                        raise Exception(f"Gist update failed: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"⚠️  Gist save timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # CRITICAL: Raise exception on final failure
                    raise Exception(f"❌ CRITICAL: Failed to save state to Gist after {max_retries} attempts (timeout): {e}")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Gist save error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # CRITICAL: Raise exception on final failure
                    raise Exception(f"❌ CRITICAL: Failed to save state to Gist after {max_retries} attempts: {e}")

            except Exception as e:
                # Non-network errors (parsing, etc.)
                raise Exception(f"❌ CRITICAL: Failed to save state to Gist: {e}")
    
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
