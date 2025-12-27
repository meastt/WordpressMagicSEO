import logging
from analytics.gsc_ingestor import GSCIngestor
from analytics.performance_analyzer import PerformanceAnalyzer

# Setup simple logging
logging.basicConfig(level=logging.INFO)

def test_real_file():
    gsc_file = "/Users/michaeleast/WordpressMagicSEO/data/reports/https___griddleking.com_-Performance-on-Search-2025-12-27.xlsx"
    print(f"🚀 Testing Real GSC File: {gsc_file}")

    try:
        # 1. Ingest
        ingestor = GSCIngestor()
        pages = ingestor.ingest(gsc_file)
        print(f"✅ Successfully ingested {len(pages)} URLs from Excel!")
        
        # 2. Analyze a sample
        analyzer = PerformanceAnalyzer()
        actions = analyzer.analyze_batch(pages)
        
        # 3. Print Summary Stats
        protect = len([a for a in actions if a.strategy.name == "PROTECT"])
        optimize = len([a for a in actions if a.strategy.name == "OPTIMIZE_CTR"])
        revive = len([a for a in actions if a.strategy.name == "REVIVE"])
        prune = len([a for a in actions if a.strategy.name == "PRUNE"])
        
        print("\n📊 Strategy Breakdown:")
        print(f"   🏆 Winners (Protect):    {protect}")
        print(f"   🎯 Quick Wins (Optimize): {optimize}")
        print(f"   📉 Revive Opportunities:  {revive}")
        print(f"   💀 Dead Weight (Prune):   {prune}")
        
        print("\n🔍 Top 5 Quick Wins:")
        quick_wins = [a for a in actions if a.strategy.name == "OPTIMIZE_CTR"]
        # Sort by impressions desc
        quick_wins.sort(key=lambda x: x.metrics.impressions, reverse=True)
        
        for win in quick_wins[:5]:
             print(f"   • {win.url}")
             print(f"     Metrics: Pos {win.metrics.position:.1f} | Impr {win.metrics.impressions}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_real_file()
