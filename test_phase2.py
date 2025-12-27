import json
from analytics.gsc_ingestor import GSCIngestor
from analytics.performance_analyzer import PerformanceAnalyzer, StrategyAction

def run_test():
    print("🚀 Starting Phase 2 Test: GSC Data Intelligence")
    
    # 1. Ingest
    ingestor = GSCIngestor()
    print("📥 Ingesting Mock Data...")
    pages = ingestor.ingest("mock_gsc_pages.csv")
    print(f"   ✓ Ingested {len(pages)} URLs")

    # 2. Analyze
    analyzer = PerformanceAnalyzer()
    print("🧠 Analyzing Performance...")
    actions = analyzer.analyze_batch(pages)

    # 3. Output
    print("\n📋 STRATEGIC ACTION PLAN:")
    print("="*60)
    
    for action in actions:
        if action.strategy.name == "IGNORE":
            continue
            
        icon = "❓"
        if action.strategy.name == "PROTECT": icon = "🏆"
        if action.strategy.name == "OPTIMIZE_CTR": icon = "🎯"
        if action.strategy.name == "REVIVE": icon = "📉"
        if action.strategy.name == "PRUNE": icon = "💀"

        print(f"{icon} {action.strategy.name}: {action.url}")
        print(f"   Reason: {action.reason}")
        print(f"   Fix:    {action.suggested_fix}")
        print("-" * 60)

if __name__ == "__main__":
    run_test()
