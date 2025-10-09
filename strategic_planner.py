"""
strategic_planner.py
===================
AI-powered strategic planner that analyzes all data and creates a prioritized action plan.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import pandas as pd


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
    
    def __init__(self, gsc_df: pd.DataFrame, sitemap_data: Dict):
        self.gsc_df = gsc_df
        self.sitemap_data = sitemap_data
        self.action_plan: List[ActionItem] = []
    
    def analyze_dead_content(self, duplicate_analysis: List[Dict]) -> List[ActionItem]:
        """Decide what to do with dead content (no GSC data)."""
        actions = []
        
        dead_urls = self.sitemap_data.get('dead_content', [])
        
        # Check if dead URLs should redirect to better performing duplicates
        duplicate_map = {}
        for dup in duplicate_analysis:
            winner_url = dup['winner']['url']
            for loser in dup['redirect_candidates']:
                duplicate_map[loser['url']] = winner_url
        
        for url in dead_urls:
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
                # No duplicate - just delete
                action = ActionItem(
                    action_type=ActionType.DELETE,
                    url=url,
                    priority_score=1.0,  # Low priority
                    reasoning="No traffic and no duplicate content to redirect to",
                    estimated_impact="Low"
                )
            
            actions.append(action)
        
        return actions
    
    def analyze_update_opportunities(self) -> List[ActionItem]:
        """Find content that should be updated/refreshed."""
        actions = []
        
        # High impressions but low CTR = needs better title/meta
        high_imp_low_ctr = self.gsc_df.groupby('page').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # Filter: >1000 impressions, CTR < 2%, or position > 10
        candidates = high_imp_low_ctr[
            (high_imp_low_ctr['impressions'] > 1000) & 
            ((high_imp_low_ctr['ctr'] < 0.02) | (high_imp_low_ctr['position'] > 10))
        ]
        
        for _, row in candidates.iterrows():
            url = row['page']
            
            # Get top keywords for this URL
            url_queries = self.gsc_df[self.gsc_df['page'] == url].nlargest(5, 'impressions')
            keywords = url_queries['query'].tolist()
            
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
        
        # Get queries with high impressions where we rank poorly (position > 20)
        poor_ranking = self.gsc_df[self.gsc_df['position'] > 20].copy()
        
        # Group by query to find opportunities
        query_stats = poor_ranking.groupby('query').agg({
            'impressions': 'sum',
            'position': 'mean'
        }).reset_index()
        
        # Sort by impressions (highest opportunity first)
        opportunities = query_stats.nlargest(top_n, 'impressions')
        
        for _, row in opportunities.iterrows():
            query = row['query']
            
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
        
        all_actions = delete_actions + update_actions + create_actions
        
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