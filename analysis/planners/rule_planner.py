"""
strategic_planner.py
===================
AI-powered strategic planner that analyzes all data and creates a prioritized action plan.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import re


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
        
        # SEO enhancement data
        self.keyword_data = self._extract_keywords_from_gsc()
        self.intent_scores = self._calculate_intent_scores()
    
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
    
    def _extract_keywords_from_gsc(self) -> Dict[str, Dict]:
        """Extract and analyze keywords from GSC data for better SEO scoring."""
        keyword_data = {}
        
        # Group by page and analyze queries
        for page, group in self.gsc_df.groupby('page'):
            if not page or page.strip() == '':
                continue
                
            # Extract main keyword from page URL
            main_keyword = self._extract_main_keyword_from_url(page)
            
            # Analyze query performance
            queries = group['query'].dropna().unique()
            total_impressions = group['impressions'].sum()
            total_clicks = group['clicks'].sum()
            avg_position = group['position'].mean()
            avg_ctr = group['ctr'].mean()
            
            # Calculate keyword characteristics
            keyword_data[page] = {
                'main_keyword': main_keyword,
                'queries': list(queries),
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'avg_position': avg_position,
                'avg_ctr': avg_ctr,
                'query_count': len(queries),
                'search_volume_estimate': self._estimate_search_volume(total_impressions, avg_position),
                'competition_score': self._estimate_competition(avg_position, avg_ctr),
                'intent_score': self._calculate_commercial_intent(main_keyword, queries)
            }
        
        return keyword_data
    
    def _extract_main_keyword_from_url(self, url: str) -> str:
        """Extract the main keyword from a URL."""
        if not url:
            return ""
        
        # Extract slug from URL
        slug = url.rstrip('/').split('/')[-1]
        
        # Convert to readable keyword
        keyword = slug.replace('-', ' ').replace('_', ' ')
        
        # Remove common suffixes
        suffixes = [' review', ' guide', ' tips', ' vs ', ' vs', ' comparison', ' differences']
        for suffix in suffixes:
            if keyword.endswith(suffix):
                keyword = keyword[:-len(suffix)]
                break
        
        return keyword.strip()
    
    def _estimate_search_volume(self, impressions: int, position: float) -> int:
        """Estimate search volume based on impressions and position."""
        if position <= 0:
            return 0
        
        # Rough estimation: impressions = search_volume * CTR * position_factor
        # Higher positions get more impressions per search volume
        position_factor = max(0.1, 1 / (position ** 0.5))
        estimated_volume = int(impressions / (position_factor * 0.05))  # Assume 5% CTR
        
        return max(0, estimated_volume)
    
    def _estimate_competition(self, position: float, ctr: float) -> float:
        """Estimate keyword competition based on position and CTR."""
        # Lower position = higher competition
        # Lower CTR = higher competition
        position_score = max(0, 1 - (position / 100))
        ctr_score = min(1, ctr / 0.05)  # 5% CTR is good
        
        competition = (1 - position_score) + (1 - ctr_score)
        return min(1, max(0, competition / 2))
    
    def _calculate_commercial_intent(self, main_keyword: str, queries: List[str]) -> float:
        """Calculate commercial intent score for keywords."""
        commercial_indicators = [
            'buy', 'purchase', 'price', 'cost', 'cheap', 'expensive', 'best', 'top', 'review',
            'vs', 'comparison', 'alternative', 'recommend', 'guide', 'how to', 'where to',
            'shop', 'store', 'deal', 'discount', 'sale', 'offer'
        ]
        
        informational_indicators = [
            'what is', 'how does', 'why do', 'when do', 'where do', 'facts', 'information',
            'learn', 'understand', 'explain', 'meaning', 'definition', 'types', 'species'
        ]
        
        # Check main keyword
        main_score = 0
        for indicator in commercial_indicators:
            if indicator in main_keyword.lower():
                main_score += 0.3
        for indicator in informational_indicators:
            if indicator in main_keyword.lower():
                main_score -= 0.2
        
        # Check queries
        query_score = 0
        for query in queries[:10]:  # Check top 10 queries
            query_lower = query.lower()
            for indicator in commercial_indicators:
                if indicator in query_lower:
                    query_score += 0.1
            for indicator in informational_indicators:
                if indicator in query_lower:
                    query_score -= 0.05
        
        total_score = main_score + query_score
        return max(0, min(1, total_score))  # Clamp between 0 and 1
    
    def _calculate_intent_scores(self) -> Dict[str, float]:
        """Calculate intent scores for all pages."""
        intent_scores = {}
        for page, data in self.keyword_data.items():
            intent_scores[page] = data['intent_score']
        return intent_scores
    
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
        print(f"DEBUG STRATEGIC: Keyword data entries: {len(self.keyword_data)}")
        
        # Process each page with advanced SEO scoring
        for url, data in self.keyword_data.items():
            
            # Skip if no URL
            if not url or url.strip() == '':
                continue
            
            # Skip taxonomy pages (categories, tags, archives)
            if any(x in url for x in ['/category/', '/tag/', '/page/', '/author/', '/date/']):
                continue
            
            # Skip if recently processed
            if self._is_recently_processed(url):
                continue
            
            # Calculate advanced SEO opportunity score
            seo_score = self._calculate_seo_opportunity_score(data)
            
            # Only include pages with meaningful SEO potential
            if seo_score < 3.0:
                continue
            
            # Determine action type and reasoning
            action_type, reasoning, impact = self._determine_update_strategy(data)
            
            # Get keywords for this URL
            keywords = data.get('queries', [])
            if not keywords:
                url_slug = url.rstrip('/').split('/')[-1]
                keywords = [url_slug.replace('-', ' ')]
            
            action = ActionItem(
                action_type=ActionType.UPDATE,
                url=url,
                keywords=keywords,
                priority_score=seo_score,
                reasoning=reasoning,
                estimated_impact=impact
            )
            
            actions.append(action)
        
        print(f"DEBUG STRATEGIC: Total update candidates: {len(actions)}")
        return actions
    
    def _calculate_seo_opportunity_score(self, data: Dict) -> float:
        """Calculate comprehensive SEO opportunity score."""
        impressions = data['total_impressions']
        position = data['avg_position']
        ctr = data['avg_ctr']
        search_volume = data['search_volume_estimate']
        competition = data['competition_score']
        intent = data['intent_score']
        
        # Base score from impressions and position
        if impressions > 1000:
            base_score = 8.0 + min(2.0, impressions / 1000)
        elif impressions > 500:
            base_score = 6.0 + min(2.0, impressions / 500)
        elif impressions > 100:
            base_score = 4.0 + min(2.0, impressions / 100)
        else:
            base_score = 2.0
        
        # Position penalty/bonus
        if position > 50:
            position_modifier = -1.0
        elif position > 20:
            position_modifier = -0.5
        elif position > 10:
            position_modifier = 0.0
        else:
            position_modifier = 0.5
        
        # CTR penalty
        if ctr < 0.01:
            ctr_modifier = -0.5
        elif ctr < 0.03:
            ctr_modifier = 0.0
        else:
            ctr_modifier = 0.3
        
        # Search volume bonus
        if search_volume > 5000:
            volume_modifier = 1.0
        elif search_volume > 1000:
            volume_modifier = 0.5
        else:
            volume_modifier = 0.0
        
        # Competition modifier (lower competition = higher opportunity)
        competition_modifier = (1 - competition) * 0.5
        
        # Intent modifier (commercial intent = higher value)
        intent_modifier = intent * 0.3
        
        total_score = base_score + position_modifier + ctr_modifier + volume_modifier + competition_modifier + intent_modifier
        
        return max(0, min(10, total_score))  # Clamp between 0 and 10
    
    def _determine_update_strategy(self, data: Dict) -> Tuple[str, str, str]:
        """Determine the best update strategy based on SEO data."""
        impressions = data['total_impressions']
        position = data['avg_position']
        ctr = data['avg_ctr']
        search_volume = data['search_volume_estimate']
        intent = data['intent_score']
        
        if impressions > 1000 and ctr < 0.02:
            strategy = "High visibility but low CTR - optimize title and meta description for better click-through rates"
            impact = "High"
        elif position > 30 and search_volume > 1000:
            strategy = f"High search volume ({search_volume:.0f} est.) but poor ranking (pos: {position:.1f}) - comprehensive content optimization needed"
            impact = "High"
        elif intent > 0.6 and position > 15:
            strategy = f"Commercial intent detected but suboptimal ranking (pos: {position:.1f}) - optimize for conversion and ranking"
            impact = "High"
        elif impressions > 500 and position > 20:
            strategy = f"Moderate visibility ({impressions:.0f} impr) but poor ranking (pos: {position:.1f}) - content refresh and optimization"
            impact = "Medium"
        elif ctr < 0.01 and impressions > 100:
            strategy = f"Very low CTR ({ctr:.2%}) despite visibility ({impressions:.0f} impr) - title and meta optimization critical"
            impact = "Medium"
        else:
            strategy = f"Content refresh opportunity - improve engagement and ranking potential"
            impact = "Low"
        
        return "update", strategy, impact
    
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

        # CRITICAL: Filter out homepage URLs from all actions
        # Homepage URLs can break the site if treated as posts
        import re
        homepage_pattern = re.compile(r'^https?://[^/]+/?$')

        filtered_deletes = [a for a in delete_actions if not (a.url and homepage_pattern.match(a.url))]
        filtered_updates = [a for a in update_actions if not (a.url and homepage_pattern.match(a.url))]
        # Creates don't have URLs yet, so no filter needed

        # Log if any homepages were filtered out
        filtered_count = (len(delete_actions) - len(filtered_deletes)) + (len(update_actions) - len(filtered_updates))
        if filtered_count > 0:
            print(f"  ℹ  Filtered out {filtered_count} homepage URL(s) from action plan (homepages are not posts)")

        # Update the lists with filtered versions
        delete_actions = filtered_deletes
        update_actions = filtered_updates

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