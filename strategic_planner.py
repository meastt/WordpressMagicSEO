"""
strategic_planner.py
===================
AI-powered strategic planner that analyzes all data and creates a prioritized action plan.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import json
import os


class ActionType(Enum):
    """Types of actions the system can take."""
    DELETE = "delete"
    REDIRECT_301 = "redirect_301"
    UPDATE = "update"
    CREATE = "create"


@dataclass
class ActionItem:
    """Represents a single action in the content plan."""
    action_type: ActionType
    url: str = ""
    title: str = ""
    keywords: List[str] = None
    priority_score: float = 0.0
    reasoning: str = ""
    redirect_target: str = ""  # For 301 redirects
    estimated_impact: str = ""  # High, Medium, Low
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class StrategicPlanner:
    """Create prioritized action plans based on comprehensive data analysis."""
    
    def __init__(
        self, 
        gsc_df: pd.DataFrame, 
        sitemap_data: Dict,
        state_file: str = "seo_automation_state.json",
        skip_recent_days: int = 7
    ):
        self.gsc_df = gsc_df
        self.sitemap_data = sitemap_data
        self.action_plan: List[ActionItem] = []
        self.state_file = state_file
        self.skip_recent_days = skip_recent_days
        self.completed_actions = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load previously completed actions from state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️  Could not load state file: {e}")
                return {'completed': []}
        return {'completed': []}
    
    def _is_recently_processed(self, url: str) -> bool:
        """Check if URL was processed within skip_recent_days."""
        for action in self.completed_actions.get('completed', []):
            if action['url'] == url:
                action_date = datetime.fromisoformat(action['timestamp'])
                days_ago = (datetime.now() - action_date).days
                if days_ago < self.skip_recent_days:
                    return True
        return False
    
    def mark_completed(self, url: str, action_type: str, post_id: Optional[int] = None):
        """Mark an action as completed in the state file."""
        if 'completed' not in self.completed_actions:
            self.completed_actions['completed'] = []
        
        self.completed_actions['completed'].append({
            'url': url,
            'action': action_type,
            'post_id': post_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save to file
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.completed_actions, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Could not save state file: {e}")
    
    def analyze_dead_content(self, duplicate_analysis: List[Dict]) -> List[ActionItem]:
        """Decide what to do with dead content (no GSC data) - UPDATE with fresh content."""
        actions = []
        
        dead_urls = self.sitemap_data.get('dead_content', [])
        print(f"DEBUG STRATEGIC: Dead content URLs: {len(dead_urls)}")
        print(f"DEBUG STRATEGIC: Sitemap data keys: {list(self.sitemap_data.keys())}")
        
        # Check if dead URLs should redirect to better performing duplicates
        duplicate_map = {}
        for dup in duplicate_analysis:
            winner_url = dup['winner']['url']
            for loser in dup['redirect_candidates']:
                duplicate_map[loser['url']] = winner_url
        
        for url in dead_urls:
            # Skip taxonomy pages (categories, tags, archives)
            if any(x in url for x in ['/category/', '/tag/', '/page/', '/author/', '/date/']):
                continue
            
            # Skip if recently processed
            if self._is_recently_processed(url):
                continue
            
            if url in duplicate_map:
                # This dead URL has a better performing duplicate - redirect it
                action = ActionItem(
                    action_type=ActionType.REDIRECT_301,
                    url=url,
                    redirect_target=duplicate_map[url],
                    priority_score=3.0,  # Medium priority
                    reasoning="Dead content with better performing duplicate exists",
                    estimated_impact="Medium"
                )
            else:
                # No duplicate - UPDATE with fresh content to try to get it ranking
                # Extract keywords from URL slug
                url_slug = url.rstrip('/').split('/')[-1]
                keywords = [url_slug.replace('-', ' ')]
                
                action = ActionItem(
                    action_type=ActionType.UPDATE,
                    url=url,
                    keywords=keywords,
                    priority_score=2.0,  # Low-medium priority
                    reasoning="Zero impressions - refresh content to improve ranking potential",
                    estimated_impact="Medium"
                )
            
            actions.append(action)
        
        return actions
    
    def analyze_update_opportunities(self) -> List[ActionItem]:
        """Find content that should be updated/refreshed."""
        actions = []
        
        print(f"DEBUG STRATEGIC: Total GSC rows: {len(self.gsc_df)}")
        print(f"DEBUG STRATEGIC: GSC columns: {list(self.gsc_df.columns)}")
        
        # High impressions but low CTR = needs better title/meta
        high_imp_low_ctr = self.gsc_df.groupby('page').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        print(f"DEBUG STRATEGIC: Grouped pages: {len(high_imp_low_ctr)}")
        
        # Filter: >1000 impressions, CTR < 2%, or position > 10
        candidates = high_imp_low_ctr[
            (high_imp_low_ctr['impressions'] > 1000) & 
            ((high_imp_low_ctr['ctr'] < 0.02) | (high_imp_low_ctr['position'] > 10))
        ]
        
        print(f"DEBUG STRATEGIC: High-impression candidates: {len(candidates)}")
        
        # Also check for low-impression content that could be improved
        low_imp_candidates = high_imp_low_ctr[
            (high_imp_low_ctr['impressions'] > 0) & 
            (high_imp_low_ctr['impressions'] <= 1000) &
            (high_imp_low_ctr['position'] > 20)
        ]
        
        print(f"DEBUG STRATEGIC: Low-impression candidates: {len(low_imp_candidates)}")
        
        # Combine both sets
        all_candidates = pd.concat([candidates, low_imp_candidates], ignore_index=True)
        print(f"DEBUG STRATEGIC: Total update candidates: {len(all_candidates)}")
        
        for _, row in all_candidates.iterrows():
            url = row['page']
            
            # Skip if no URL
            if not url or url.strip() == '':
                continue
            
            # Skip taxonomy pages (categories, tags, archives)
            if any(x in url for x in ['/category/', '/tag/', '/page/', '/author/', '/date/']):
                continue
            
            # Skip if recently processed
            if self._is_recently_processed(url):
                continue
            
            # Get keywords for this URL from GSC data
            # Note: With Excel exports, we may only have URL-derived keywords
            url_queries = self.gsc_df[self.gsc_df['page'] == url]
            keywords = url_queries['query'].unique().tolist()
            
            # If no keywords found, derive from URL
            if not keywords or keywords == ['']:
                url_slug = url.rstrip('/').split('/')[-1]
                keywords = [url_slug.replace('-', ' ')]
            
            # Calculate priority score based on potential impact
            # High impressions = high potential impact
            priority = (row['impressions'] / 1000) * (1 - row['ctr']) * 10
            priority = min(priority, 10.0)  # Cap at 10
            
            impact = "High" if row['impressions'] > 5000 else "Medium"
            
            action = ActionItem(
                action_type=ActionType.UPDATE,
                url=url,
                keywords=keywords,
                priority_score=priority,
                reasoning=f"High visibility ({int(row['impressions'])} impr) but low engagement (CTR: {row['ctr']:.2%}, pos: {row['position']:.1f})",
                estimated_impact=impact
            )
            actions.append(action)
        
        return actions
    
    def identify_content_gaps(self, top_n: int = 20) -> List[ActionItem]:
        """Find high-opportunity keywords we're not ranking for."""
        actions = []
        
        # Get all existing pages from GSC data (pages that have any traffic)
        existing_pages = set(self.gsc_df['page'].unique())
        
        # Also get all performing pages from sitemap data
        performing_urls = set(self.sitemap_data.get('performing_content', []))
        all_existing_pages = existing_pages | performing_urls
        
        # Get queries with high impressions where we rank poorly (position > 20)
        poor_ranking = self.gsc_df[self.gsc_df['position'] > 20].copy()
        
        # Group by query to find opportunities
        query_stats = poor_ranking.groupby('query').agg({
            'impressions': 'sum',
            'position': 'mean',
            'page': 'first'  # Get one example page for this query
        }).reset_index()
        
        # Sort by impressions (highest opportunity first)
        opportunities = query_stats.nlargest(top_n, 'impressions')
        
        for _, row in opportunities.iterrows():
            query = row['query']
            example_page = row['page']
            
            # Skip if this query already has a page (even if ranking poorly)
            # Those should be handled by UPDATE actions, not CREATE
            if example_page and example_page in all_existing_pages:
                continue
            
            # Calculate priority based on search volume
            priority = (row['impressions'] / 100) * (row['position'] / 10)
            priority = min(priority, 10.0)
            
            impact = "High" if row['impressions'] > 2000 else "Medium"
            
            action = ActionItem(
                action_type=ActionType.CREATE,
                title=self._query_to_title(query),
                keywords=[query],
                priority_score=priority,
                reasoning=f"High search volume ({int(row['impressions'])} impr) with poor ranking (pos {row['position']:.1f})",
                estimated_impact=impact
            )
            actions.append(action)
        
        return actions
    
    def create_master_plan(self, duplicate_analysis: List[Dict]) -> List[ActionItem]:
        """Create the complete prioritized action plan."""
        
        # Collect all actions
        delete_actions = self.analyze_dead_content(duplicate_analysis)
        update_actions = self.analyze_update_opportunities()
        create_actions = self.identify_content_gaps()
        
        # Remove CREATE actions that duplicate existing content
        # Get ALL performing content URLs (not just ones being updated)
        performing_urls = self.sitemap_data.get('performing_content', [])
        existing_slugs = set()
        for url in performing_urls:
            if url:
                slug = url.rstrip('/').split('/')[-1]
                slug_norm = slug.lower().replace('-', ' ')
                existing_slugs.add(slug_norm)
        
        filtered_creates = []
        for action in create_actions:
            # Normalize the create title
            title_norm = action.title.lower()
            # Remove common suffixes
            for suffix in [': what you need to know', ': complete guide', ' guide', ' review']:
                title_norm = title_norm.replace(suffix, '')
            title_norm = title_norm.strip().replace('-', ' ')
            
            # Check if this title matches any existing content slug
            is_duplicate = False
            for existing_slug in existing_slugs:
                # Check if either contains the other (allows for variations)
                # Only match if substantial overlap (>4 chars to avoid false positives)
                if len(title_norm) > 4 and len(existing_slug) > 4:
                    if title_norm in existing_slug or existing_slug in title_norm:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered_creates.append(action)
        
        all_actions = delete_actions + update_actions + filtered_creates
        
        # Sort by priority score (highest first)
        all_actions.sort(key=lambda x: x.priority_score, reverse=True)
        
        self.action_plan = all_actions
        return all_actions
    
    def _query_to_title(self, query: str) -> str:
        """Convert search query to article title."""
        # Capitalize each word and clean up
        words = query.split()
        title = ' '.join(word.capitalize() for word in words)
        
        # Add context if it's a question
        if any(q in query.lower() for q in ['how', 'what', 'why', 'when', 'where', 'who']):
            return title
        else:
            # Add "Guide" or "Review" suffix based on query type
            if any(word in query.lower() for word in ['best', 'top', 'review']):
                return f"{title}: Complete Guide"
            else:
                return f"{title}: What You Need to Know"
    
    def get_plan_summary(self) -> Dict:
        """Get summary statistics of the action plan."""
        if not self.action_plan:
            return {}
        
        summary = {
            'total_actions': len(self.action_plan),
            'deletes': len([a for a in self.action_plan if a.action_type == ActionType.DELETE]),
            'redirects': len([a for a in self.action_plan if a.action_type == ActionType.REDIRECT_301]),
            'updates': len([a for a in self.action_plan if a.action_type == ActionType.UPDATE]),
            'creates': len([a for a in self.action_plan if a.action_type == ActionType.CREATE]),
            'high_priority': len([a for a in self.action_plan if a.priority_score >= 7]),
            'medium_priority': len([a for a in self.action_plan if 3 <= a.priority_score < 7]),
            'low_priority': len([a for a in self.action_plan if a.priority_score < 3]),
        }
        
        return summary