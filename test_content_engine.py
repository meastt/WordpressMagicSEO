import logging
from content_engine.optimizer import ContentOptimizer
from content_engine.media import MediaEngine
from content_engine.taxonomy import TaxonomyManager

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_content_engine_scaffold():
    print("🚀 Testing AI Content Engine Scaffolding...")
    
    # 1. Test Optimizer
    optimizer = ContentOptimizer()
    print("\n✍️  Testing Content Optimizer:")
    title = optimizer.rewrite_title("My Review of Burger Press", "Burger Press")
    print(f"   Original: My Review of Burger Press")
    print(f"   Optimized: {title}")
    
    table = optimizer.generate_comparison_table("Burger Presses", ["Press A", "Press B"])
    print(f"   Table Preview: {table}")

    # 2. Test Media
    media = MediaEngine()
    print("\n🎨 Testing Media Engine:")
    img_path = media.generate_featured_image("Best Burger Presses 2025")
    print(f"   Image Generated at: {img_path}")
    alt_text = media.generate_alt_text("Burger Press", "Smash Burger")
    print(f"   Alt Text: {alt_text}")

    # 3. Test Taxonomy
    taxonomy = TaxonomyManager()
    print("\n📚 Testing Taxonomy Manager:")
    cats = taxonomy.suggest_categories("Review of a heavy duty burger press...", ["Reviews", "News"])
    print(f"   Categories: {cats}")
    tags = taxonomy.generate_tags("Review of Blackstone..")
    print(f"   Tags: {tags}")

    print("\n✅ Scaffolding Verified!")

if __name__ == "__main__":
    test_content_engine_scaffold()
