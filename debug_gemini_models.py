import os
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv("venv/.env")

def list_gemini_models():
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ No API Key found.")
        return

    client = genai.Client(api_key=api_key)
    
    print("🔍 Listing Available Models...")
    try:
        # Listing models (pager iterator)
        for model in client.models.list(config={"page_size": 100}):
             print(f" - {model.name}")

    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
