"""
test_pipeline.py
===============
Test script to verify the SEO automation pipeline works.
Tests analysis only (no WordPress publishing).
"""

import os
import sys

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from multi_site_content_agent import GSCProcessor
        print("  ✓ GSCProcessor")
        
        from sitemap_analyzer import SitemapAnalyzer
        print("  ✓ SitemapAnalyzer")
        
        from strategic_planner import StrategicPlanner
        print("  ✓ StrategicPlanner")
        
        from claude_content_generator import ClaudeContentGenerator
        print("  ✓ ClaudeContentGenerator")
        
        from wordpress_publisher import WordPressPublisher
        print("  ✓ WordPressPublisher")
        
        from execution_scheduler import ExecutionScheduler
        print("  ✓ ExecutionScheduler")
        
        from seo_automation_main import SEOAutomationPipeline
        print("  ✓ SEOAutomationPipeline")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}\n")
        return False


def test_gsc_processing(csv_path):
    """Test GSC data processing."""
    print("🧪 Testing GSC data processing...")
    
    try:
        from multi_site_content_agent import GSCProcessor
        
        processor = GSCProcessor(csv_path)
        df = processor.load()
        
        print(f"  ✓ Loaded {len(df)} rows")
        print(f"  ✓ Columns: {list(df.columns)}")
        
        # Test summarization
        summary = processor.summarise_by_page()
        print(f"  ✓ Summarized to {len(summary)} unique pages")
        
        # Test refresh candidates
        candidates = processor.identify_refresh_candidates()
        print(f"  ✓ Found {len(candidates)} refresh candidates")
        
        # Test query extraction
        queries = processor.extract_query_opportunities(top_n=5)
        print(f"  ✓ Extracted {len(queries)} top queries")
        if queries:
            print(f"    Top query: {queries[0]}")
        
        print("\n✅ GSC processing works!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ GSC processing failed: {e}\n")
        return False


def test_sitemap_fetch(site_url):
    """Test sitemap fetching."""
    print("🧪 Testing sitemap fetching...")
    
    try:
        from sitemap_analyzer import SitemapAnalyzer
        
        analyzer = SitemapAnalyzer(site_url)
        urls = analyzer.fetch_sitemap()
        
        print(f"  ✓ Fetched {len(urls)} URLs from sitemap")
        if urls:
            print(f"    Sample URL: {urls[0].url}")
        
        print("\n✅ Sitemap fetching works!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Sitemap fetching failed: {e}\n")
        return False


def test_strategic_planning(csv_path, site_url):
    """Test the complete analysis and planning."""
    print("🧪 Testing strategic planning...")
    
    try:
        from multi_site_content_agent import GSCProcessor
        from sitemap_analyzer import SitemapAnalyzer
        from strategic_planner import StrategicPlanner
        
        # Load GSC data
        processor = GSCProcessor(csv_path)
        gsc_df = processor.load()
        
        # Fetch sitemap
        analyzer = SitemapAnalyzer(site_url)
        sitemap_urls = analyzer.fetch_sitemap()
        sitemap_data = analyzer.compare_with_gsc(sitemap_urls, gsc_df)
        
        print(f"  ✓ Dead content: {len(sitemap_data['dead_content'])}")
        print(f"  ✓ Performing: {len(sitemap_data['performing_content'])}")
        
        # Find duplicates
        duplicates = analyzer.find_duplicate_content_candidates(gsc_df)
        print(f"  ✓ Duplicate groups: {len(duplicates)}")
        
        # Create plan
        planner = StrategicPlanner(gsc_df, sitemap_data)
        action_plan = planner.create_master_plan(duplicates)
        summary = planner.get_plan_summary()
        
        print(f"  ✓ Total actions: {summary['total_actions']}")
        print(f"    - Delete: {summary['deletes']}")
        print(f"    - Redirect: {summary['redirects']}")
        print(f"    - Update: {summary['updates']}")
        print(f"    - Create: {summary['creates']}")
        
        if action_plan:
            print(f"\n  📋 Top 3 actions:")
            for i, action in enumerate(action_plan[:3], 1):
                print(f"    {i}. {action.action_type.value} - Priority: {action.priority_score:.1f}")
                print(f"       {action.reasoning[:60]}...")
        
        print("\n✅ Strategic planning works!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Strategic planning failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("🚀 SEO AUTOMATION PIPELINE - TEST SUITE")
    print("=" * 80)
    print()
    
    # Check for required arguments
    if len(sys.argv) < 3:
        print("Usage: python test_pipeline.py <gsc_csv_path> <site_url>")
        print("\nExample:")
        print("  python test_pipeline.py gsc_export.csv https://yoursite.com")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    site_url = sys.argv[2]
    
    # Verify file exists
    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"Testing with:")
    print(f"  CSV: {csv_path}")
    print(f"  Site: {site_url}")
    print()
    
    # Run tests
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("GSC Processing", test_gsc_processing(csv_path)))
    results.append(("Sitemap Fetching", test_sitemap_fetch(site_url)))
    results.append(("Strategic Planning", test_strategic_planning(csv_path, site_url)))
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Pipeline is ready to use.")
        print("\nNext steps:")
        print("1. Set ANTHROPIC_API_KEY environment variable")
        print("2. Test with --max-actions 1 flag first")
        print("3. Review generated content before publishing")
    else:
        print("\n⚠️  Some tests failed. Fix issues before running full pipeline.")
    
    print("=" * 80)


if __name__ == "__main__":
    main()