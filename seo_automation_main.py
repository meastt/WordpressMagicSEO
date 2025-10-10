"""
seo_automation_main.py
=====================
Main orchestrator for the complete SEO automation system.

Phase 5: Enhanced Pipeline with AI Intelligence
- Multi-site support via config.py
- Dual data input (GSC + GA4) via DataProcessor
- AI niche intelligence via NicheAnalyzer
- AI strategic planning via AIStrategicPlanner
- State tracking via StateManager
"""

import os
import sys
import json
from typing import Dict, Optional
import pandas as pd
from datetime import datetime

# Import all our modules
from multi_site_content_agent import DataProcessor  # Phase 2: GSC + GA4 support
from sitemap_analyzer import SitemapAnalyzer
from strategic_planner import StrategicPlanner  # Legacy planner (will be deprecated)
from claude_content_generator import ClaudeContentGenerator
from wordpress_publisher import WordPressPublisher
from execution_scheduler import ExecutionScheduler, ScheduleConfig

# Phase 1-4: New AI-powered modules
from config import get_site, list_sites
from state_manager import StateManager
from niche_analyzer import NicheAnalyzer
from ai_strategic_planner import AIStrategicPlanner


class SEOAutomationPipeline:
    """
    Complete SEO automation pipeline orchestrator.
    
    Enhanced in Phase 5 with:
    - Multi-site configuration support
    - GA4 + GSC dual data input
    - AI-powered niche research
    - AI-powered strategic planning
    - State tracking and caching
    """
    
    def __init__(
        self,
        site_name: str = None,
        gsc_csv_path: str = None,
        ga4_csv_path: str = None,
        site_url: str = None,
        wp_username: str = None,
        wp_app_password: str = None,
        anthropic_api_key: str = None
    ):
        """
        Initialize pipeline with either:
        - site_name (loads from config) OR
        - individual parameters (legacy mode)
        
        Args:
            site_name: Configured site name (e.g., "griddleking.com")
            gsc_csv_path: Path to GSC CSV export
            ga4_csv_path: Path to GA4 CSV export (optional)
            site_url: WordPress site URL
            wp_username: WordPress username
            wp_app_password: WordPress application password
            anthropic_api_key: Anthropic API key
        """
        
        # Mode 1: Multi-site mode (use config)
        if site_name:
            try:
                site_config = get_site(site_name)
                self.site_name = site_name
                self.site_url = site_config['url']
                self.wp_username = site_config['wp_username']
                self.wp_app_password = site_config['wp_app_password']
                self.niche = site_config['niche']
                self.gsc_csv_path = gsc_csv_path  # Still need to provide data files
                self.ga4_csv_path = ga4_csv_path
            except Exception as e:
                raise ValueError(f"Failed to load site config for '{site_name}': {e}")
        
        # Mode 2: Legacy mode (individual parameters)
        else:
            if not all([gsc_csv_path, site_url, wp_username, wp_app_password]):
                raise ValueError("Must provide either site_name OR all individual parameters")
            
            self.site_name = site_url  # Use URL as identifier
            self.gsc_csv_path = gsc_csv_path
            self.ga4_csv_path = ga4_csv_path
            self.site_url = site_url
            self.wp_username = wp_username
            self.wp_app_password = wp_app_password
            self.niche = None  # Will skip niche research if not set
        
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize state manager
        self.state_mgr = StateManager(self.site_name)
        
        # Initialize components
        self.data_processor = None
        self.sitemap_analyzer = None
        self.niche_analyzer = None
        self.ai_planner = None  # New AI planner
        self.legacy_planner = None  # Old rule-based planner
        self.content_generator = None
        self.wp_publisher = None
        self.scheduler = None
        
        # Data storage
        self.merged_df = None
        self.sitemap_data = None
        self.duplicate_analysis = None
        self.niche_report = None
        self.action_plan = None
    
    def run(
        self,
        execution_mode: str = "view_plan",
        schedule_mode: str = "all_at_once",
        posts_per_batch: int = 3,
        delay_hours: float = 8,
        limit: int = None,
        output_csv: str = "seo_automation_results.csv",
        use_ai_planner: bool = True
    ) -> Dict:
        """
        Run the complete enhanced pipeline.
        
        Args:
            execution_mode: "view_plan" (analyze only), "execute_all", "execute_top_n", "continue"
            schedule_mode: "all_at_once", "daily", "hourly", "custom"
            posts_per_batch: Number of posts to process per batch
            delay_hours: Hours to wait between batches
            limit: Maximum number of actions to execute (for execute_top_n mode)
            output_csv: Path to save results CSV
            use_ai_planner: Use AI planner (True) or legacy rule-based planner (False)
        
        Returns:
            Dictionary with execution summary and action plan
        """
        
        print("=" * 80)
        print(f"🎯 SEO AUTOMATION PIPELINE - {self.site_name}")
        print("=" * 80)
        print(f"Mode: {'AI-Powered' if use_ai_planner else 'Legacy Rule-Based'}")
        print(f"Execution: {execution_mode}")
        
        # STEP 1: Load and analyze GSC + GA4 data
        print("\n📊 STEP 1: Loading data (GSC + GA4)...")
        self.data_processor = DataProcessor(self.gsc_csv_path, self.ga4_csv_path)
        self.merged_df = self.data_processor.merge_data()
        
        # Check if GA4 data was loaded
        has_ga4 = 'engagement_rate' in self.merged_df.columns
        print(f"  ✓ Loaded {len(self.merged_df)} GSC rows")
        if has_ga4:
            ga4_count = self.merged_df['engagement_rate'].notna().sum()
            print(f"  ✓ Merged with GA4 data ({ga4_count} pages with engagement metrics)")
        else:
            print(f"  ℹ No GA4 data available (GSC only)")
        
        # STEP 2: Niche Intelligence (if AI mode and niche is set)
        if use_ai_planner and self.niche and self.anthropic_api_key:
            print("\n🔍 STEP 2: AI Niche Intelligence...")
            
            # Check for cached research
            cached_research = self.state_mgr.get_niche_research()
            if cached_research:
                print("  ✓ Using cached niche research (30-day cache)")
                self.niche_report = json.loads(cached_research)
            else:
                print(f"  🌐 Researching '{self.niche}' niche with AI...")
                self.niche_analyzer = NicheAnalyzer(self.anthropic_api_key)
                self.niche_report = self.niche_analyzer.research_niche(self.niche, self.site_url)
                
                # Cache the research
                self.state_mgr.cache_niche_research(json.dumps(self.niche_report), cache_days=30)
                print("  ✓ Niche research complete (cached for 30 days)")
            
            # Show key insights
            print(f"\n  📈 Key Trends:")
            for trend in self.niche_report.get('trends', [])[:3]:
                print(f"     • {trend}")
            print(f"\n  💡 Top Opportunities:")
            for opp in self.niche_report.get('opportunities', [])[:3]:
                print(f"     • {opp}")
        else:
            print("\n⏭️  STEP 2: Skipping niche intelligence (not in AI mode or no niche set)")
            self.niche_report = None
        
        # STEP 3: Fetch and analyze sitemap
        print("\n🗺️  STEP 3: Fetching and analyzing sitemap...")
        self.sitemap_analyzer = SitemapAnalyzer(self.site_url)
        sitemap_urls = self.sitemap_analyzer.fetch_sitemap()
        print(f"  ✓ Found {len(sitemap_urls)} URLs in sitemap")
        
        # Compare sitemap with GSC data
        self.sitemap_data = self.sitemap_analyzer.compare_with_gsc(
            sitemap_urls,
            self.merged_df
        )
        
        print(f"  ✓ Dead content: {len(self.sitemap_data['dead_content'])} URLs")
        print(f"  ✓ Performing content: {len(self.sitemap_data['performing_content'])} URLs")
        print(f"  ✓ Orphaned content: {len(self.sitemap_data['orphaned_content'])} URLs")
        
        # STEP 3: Find duplicate content
        print("\n🔍 STEP 3: Identifying duplicate content...")
        self.duplicate_analysis = self.sitemap_analyzer.find_duplicate_content_candidates(
            self.merged_df
        )
        print(f"  ✓ Found {len(self.duplicate_analysis)} potential duplicate groups")

        # STEP 4: Create strategic plan
        print("\n🎯 STEP 4: Creating strategic action plan...")
        self.strategic_planner = StrategicPlanner(self.merged_df, self.sitemap_data)
        self.action_plan = self.strategic_planner.create_master_plan(
            self.duplicate_analysis
        )
        
        plan_summary = self.strategic_planner.get_plan_summary()
        print(f"  ✓ Total actions planned: {plan_summary['total_actions']}")
        print(f"    - Delete: {plan_summary['deletes']}")
        print(f"    - Redirect (301): {plan_summary['redirects']}")
        print(f"    - Update: {plan_summary['updates']}")
        print(f"    - Create: {plan_summary['creates']}")
        print(f"  ✓ Priority breakdown:")
        print(f"    - High: {plan_summary['high_priority']}")
        print(f"    - Medium: {plan_summary['medium_priority']}")
        print(f"    - Low: {plan_summary['low_priority']}")
        
        # Show top 5 actions
        print("\n  📋 Top 5 Priority Actions:")
        for i, action in enumerate(self.action_plan[:5], 1):
            print(f"    {i}. [{action.action_type.value.upper()}] "
                  f"Priority: {action.priority_score:.1f} - {action.reasoning[:60]}...")
        
        # STEP 5: Initialize execution components
        print("\n⚙️  STEP 5: Initializing execution components...")
        
        self.content_generator = ClaudeContentGenerator(self.anthropic_api_key)
        print("  ✓ Claude content generator ready")
        
        self.wp_publisher = WordPressPublisher(
            self.site_url,
            self.wp_username,
            self.wp_app_password,
            rate_limit_delay=2.0
        )
        print("  ✓ WordPress publisher ready")
        
        # STEP 6: Execute the plan
        print("\n🚀 STEP 6: Executing action plan...")
        print(f"  Schedule: {schedule_mode}")
        
        if schedule_mode == "all_at_once":
            print(f"  ⚡ All actions processed continuously (no batching)")
        else:
            print(f"  Batch size: {posts_per_batch} posts")
            print(f"  Delay between batches: {delay_hours} hours")

        if limit:
            print(f"  ⚠️  Limited to first {limit} actions (for testing)")

        # Confirm before execution
        if limit is None and len(self.action_plan) > 50:
            print(f"\n  ⚠️  Warning: About to execute {len(self.action_plan)} actions!")
            print("  This will modify your WordPress site.")
            print("  Continuing automatically (set limit to restrict)...")
        
        schedule_config = ScheduleConfig(
            mode=schedule_mode,
            posts_per_batch=posts_per_batch,
            delay_between_batches=delay_hours * 3600,  # Convert to seconds
            max_api_calls_per_minute=10
        )
        
        self.scheduler = ExecutionScheduler(
            self.action_plan,
            self.wp_publisher,
            self.content_generator,
            schedule_config,
            planner=self.strategic_planner
        )
        
        # Execute!
        results = self.scheduler.execute_plan(max_actions=limit)
        
        # STEP 7: Save results and summary
        print("\n📊 STEP 7: Saving results...")
        self.scheduler.save_results_to_csv(output_csv)
        
        summary = self.scheduler.get_summary()
        
        print("\n" + "=" * 80)
        print("✅ EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Total actions: {summary['total_actions']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success rate: {summary['success_rate']}")
        print(f"\nResults saved to: {output_csv}")
        print("=" * 80)
        
        return summary


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SEO Automation Pipeline - Analyze, plan, and execute content strategy"
    )
    
    parser.add_argument("gsc_csv", help="Path to GSC CSV export (12 months)")
    parser.add_argument("site_url", help="WordPress site URL")
    parser.add_argument("wp_username", help="WordPress username")
    parser.add_argument("wp_app_password", help="WordPress application password")
    
    parser.add_argument(
        "--schedule",
        choices=["all_at_once", "daily", "hourly", "custom"],
        default="all_at_once",
        help="Execution schedule mode"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of posts per batch"
    )
    
    parser.add_argument(
        "--delay-hours",
        type=float,
        default=8,
        help="Hours between batches"
    )
    
    parser.add_argument(
        "--max-actions",
        type=int,
        default=None,
        help="Limit execution to first N actions (for testing)"
    )
    
    parser.add_argument(
        "--output",
        default=f"seo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        help="Output CSV file path"
    )
    
    parser.add_argument(
        "--anthropic-key",
        default=None,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = SEOAutomationPipeline(
        gsc_csv_path=args.gsc_csv,
        site_url=args.site_url,
        wp_username=args.wp_username,
        wp_app_password=args.wp_app_password,
        anthropic_api_key=args.anthropic_key
    )
    
    # Run it!
    pipeline.run(
        schedule_mode=args.schedule,
        posts_per_batch=args.batch_size,
        delay_hours=args.delay_hours,
        max_actions=args.max_actions,
        output_csv=args.output
    )


if __name__ == "__main__":
    main()