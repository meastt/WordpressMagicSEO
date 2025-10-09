"""
seo_automation_main.py
=====================
Main orchestrator for the complete SEO automation system.
"""

import os
import sys
from typing import Dict
import pandas as pd
from datetime import datetime

# Import all our modules
from multi_site_content_agent import GSCProcessor
from sitemap_analyzer import SitemapAnalyzer
from strategic_planner import StrategicPlanner
from claude_content_generator import ClaudeContentGenerator
from wordpress_publisher import WordPressPublisher
from execution_scheduler import ExecutionScheduler, ScheduleConfig


class SEOAutomationPipeline:
    """Complete SEO automation pipeline orchestrator."""
    
    def __init__(
        self,
        gsc_csv_path: str,
        site_url: str,
        wp_username: str,
        wp_app_password: str,
        anthropic_api_key: str = None
    ):
        self.gsc_csv_path = gsc_csv_path
        self.site_url = site_url
        self.wp_username = wp_username
        self.wp_app_password = wp_app_password
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize components
        self.gsc_processor = None
        self.sitemap_analyzer = None
        self.strategic_planner = None
        self.content_generator = None
        self.wp_publisher = None
        self.scheduler = None
        
        # Data storage
        self.gsc_df = None
        self.sitemap_data = None
        self.duplicate_analysis = None
        self.action_plan = None
    
    def run(
        self, 
        schedule_mode: str = "all_at_once",
        posts_per_batch: int = 3,
        delay_hours: float = 8,
        max_actions: int = None,
        output_csv: str = "seo_automation_results.csv"
    ) -> Dict:
        """
        Run the complete pipeline.
        
        Args:
            schedule_mode: "all_at_once", "daily", "hourly", "custom"
            posts_per_batch: Number of posts to process per batch
            delay_hours: Hours to wait between batches
            max_actions: Maximum number of actions to execute (None = all)
            output_csv: Path to save results CSV
        
        Returns:
            Dictionary with execution summary
        """
        
        print("=" * 80)
        print("🎯 SEO AUTOMATION PIPELINE")
        print("=" * 80)
        
        # STEP 1: Load and analyze GSC data
        print("\n📊 STEP 1: Analyzing Google Search Console data...")
        self.gsc_processor = GSCProcessor(self.gsc_csv_path)
        self.gsc_df = self.gsc_processor.load()
        print(f"  ✓ Loaded {len(self.gsc_df)} GSC rows")
        
        # STEP 2: Fetch and analyze sitemap
        print("\n🗺️  STEP 2: Fetching and analyzing sitemap...")
        self.sitemap_analyzer = SitemapAnalyzer(self.site_url)
        sitemap_urls = self.sitemap_analyzer.fetch_sitemap()
        print(f"  ✓ Found {len(sitemap_urls)} URLs in sitemap")
        
        # Compare sitemap with GSC data
        self.sitemap_data = self.sitemap_analyzer.compare_with_gsc(
            sitemap_urls,
            self.gsc_df
        )
        
        print(f"  ✓ Dead content: {len(self.sitemap_data['dead_content'])} URLs")
        print(f"  ✓ Performing content: {len(self.sitemap_data['performing_content'])} URLs")
        print(f"  ✓ Orphaned content: {len(self.sitemap_data['orphaned_content'])} URLs")
        
        # STEP 3: Find duplicate content
        print("\n🔍 STEP 3: Identifying duplicate content...")
        self.duplicate_analysis = self.sitemap_analyzer.find_duplicate_content_candidates(
            self.gsc_df
        )
        print(f"  ✓ Found {len(self.duplicate_analysis)} potential duplicate groups")
        
        # STEP 4: Create strategic plan
        print("\n🎯 STEP 4: Creating strategic action plan...")
        self.strategic_planner = StrategicPlanner(self.gsc_df, self.sitemap_data)
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
        print(f"  Batch size: {posts_per_batch} posts")
        print(f"  Delay between batches: {delay_hours} hours")
        
        if max_actions:
            print(f"  ⚠️  Limited to first {max_actions} actions (for testing)")
        
        # Confirm before execution
        if max_actions is None and len(self.action_plan) > 50:
            print(f"\n  ⚠️  Warning: About to execute {len(self.action_plan)} actions!")
            print("  This will modify your WordPress site.")
            print("  Continuing automatically (set max_actions to limit)...")
        
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
            schedule_config
        )
        
        # Execute!
        results = self.scheduler.execute_plan(max_actions=max_actions)
        
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