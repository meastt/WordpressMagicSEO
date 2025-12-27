import os
import logging
from content_engine.optimizer import ContentOptimizer
from dotenv import load_dotenv

# Load env vars from venv/.env
load_dotenv("venv/.env")

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_live_connection():
    print("🚀 Testing Live Anthropic Connection (Claude Sonnet 4.5)...")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment.")
        return

    optimizer = ContentOptimizer(api_key=api_key)
    
    # Test 1: Simple Title Rewrite
    print("\n✍️  Test 1: Title Rewrite")
    original = "How to cook a steak on a griddle"
    keyword = "ribeye steak"
    
    try:
        new_title = optimizer.rewrite_title(original, keyword)
        print(f"   Original: {original}")
        print(f"   Result:   {new_title}")
        
        if "MOCK_RESPONSE" in new_title or "ERROR" in new_title:
             print("   ⚠️  Warning: API call failed or used mock.")
        else:
             print("   ✅ API Call Successful!")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_live_connection()
