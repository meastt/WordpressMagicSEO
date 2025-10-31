"""
State management utilities with simplified storage.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from utils.error_handler import AppError, ErrorCategory

logger = logging.getLogger(__name__)


class StateStorage:
    """Simplified state storage - single source of truth."""
    
    def __init__(self, storage_type: str = "auto"):
        """
        Initialize state storage.
        
        Args:
            storage_type: "gist", "file", or "auto" (auto-detect)
        """
        self.storage_type = storage_type
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.use_gist = self._should_use_gist()
    
    def _should_use_gist(self) -> bool:
        """Determine if we should use Gist storage."""
        if self.storage_type == "file":
            return False
        if self.storage_type == "gist":
            return True
        # Auto-detect: use Gist if token is available
        return bool(self.github_token)
    
    def load(self, site_name: str) -> Dict:
        """
        Load state for a site.
        
        Args:
            site_name: Site identifier
        
        Returns:
            State dictionary
        
        Raises:
            AppError if loading fails
        """
        if self.use_gist:
            return self._load_from_gist(site_name)
        else:
            return self._load_from_file(site_name)
    
    def save(self, site_name: str, state: Dict) -> None:
        """
        Save state for a site.
        
        Args:
            site_name: Site identifier
            state: State dictionary to save
        
        Raises:
            AppError if saving fails
        """
        if self.use_gist:
            self._save_to_gist(site_name, state)
        else:
            self._save_to_file(site_name, state)
    
    def _load_from_file(self, site_name: str) -> Dict:
        """Load state from local file."""
        state_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            f"{site_name}_state.json"
        )
        state_file = os.path.abspath(state_file)
        
        if not os.path.exists(state_file):
            return self._create_empty_state(site_name)
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from file for {site_name}")
            return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load state file: {e}. Creating new state.")
            return self._create_empty_state(site_name)
    
    def _save_to_file(self, site_name: str, state: Dict) -> None:
        """Save state to local file."""
        state_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            f"{site_name}_state.json"
        )
        state_file = os.path.abspath(state_file)
        
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved state to file for {site_name}")
        except IOError as e:
            raise AppError(
                f"Failed to save state to file: {e}",
                category=ErrorCategory.SYSTEM_ERROR,
                suggestion="Please check file permissions.",
                status_code=500
            )
    
    def _load_from_gist(self, site_name: str) -> Dict:
        """Load state from GitHub Gist."""
        import requests
        
        env_key = f"GIST_ID_{site_name.replace('.', '_').replace('-', '_').upper()}"
        gist_id = os.getenv(env_key)
        
        if not gist_id or gist_id == "new":
            logger.info(f"No Gist ID for {site_name}, creating new state")
            return self._create_empty_state(site_name)
        
        try:
            response = requests.get(
                f"https://api.github.com/gists/{gist_id}",
                timeout=5,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            
            if response.status_code == 200:
                gist_data = response.json()
                file_key = f"{site_name}_state.json"
                
                if file_key in gist_data.get('files', {}):
                    state_content = gist_data['files'][file_key]['content']
                    state = json.loads(state_content)
                    logger.info(f"Loaded state from Gist for {site_name}")
                    return state
            
            logger.warning(f"Gist not found or empty for {site_name}")
            return self._create_empty_state(site_name)
            
        except Exception as e:
            logger.warning(f"Could not load from Gist: {e}. Using file fallback.")
            return self._load_from_file(site_name)
    
    def _save_to_gist(self, site_name: str, state: Dict) -> None:
        """Save state to GitHub Gist."""
        import requests
        
        env_key = f"GIST_ID_{site_name.replace('.', '_').replace('-', '_').upper()}"
        gist_id = os.getenv(env_key)
        
        if not self.github_token:
            logger.warning("No GitHub token, falling back to file storage")
            self._save_to_file(site_name, state)
            return
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        files = {
            f"{site_name}_state.json": {
                "content": json.dumps(state, indent=2)
            }
        }
        
        try:
            if gist_id == "new" or not gist_id:
                # Create new Gist
                data = {
                    "description": f"State for {site_name}",
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
                    logger.info(f"Created new Gist {new_gist_id} for {site_name}")
                    # Note: In production, you'd want to save this Gist ID back to env
                    return
                else:
                    raise Exception(f"Gist creation failed: {response.status_code}")
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
                    logger.info(f"Updated Gist {gist_id} for {site_name}")
                    return
                else:
                    raise Exception(f"Gist update failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to save to Gist: {e}. Falling back to file.")
            self._save_to_file(site_name, state)
    
    def _create_empty_state(self, site_name: str) -> Dict:
        """Create an empty state structure."""
        return {
            "site_name": site_name,
            "niche_research": None,
            "current_plan": [],
            "stats": {
                "total_actions": 0,
                "completed": 0,
                "pending": 0
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
