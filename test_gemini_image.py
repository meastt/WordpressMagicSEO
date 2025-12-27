import os
import logging
from content_engine.media import MediaEngine
from dotenv import load_dotenv

load_dotenv("venv/.env")
logging.basicConfig(level=logging.INFO)

def test_gemini_image():
    print("🚀 Testing Gemini 3 Image Generation...")
    
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_GEMINI_API_KEY not found.")
        return

    media = MediaEngine(api_key=api_key)
    
    # Test Generation
    title = "Perfect Ribeye Steak on Griddle"
    print(f"\n🎨 Generating image for: '{title}'")
    
    try:
        image_path = media.generate_featured_image(title)
        print(f"   Result Path: {image_path}")
        
        if os.path.exists(image_path) and image_path.endswith(".png"):
             print(f"   ✅ Image Successfully Saved! Size: {os.path.getsize(image_path)} bytes")
        else:
             print("   ❌ Image generation failed.")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_gemini_image()
