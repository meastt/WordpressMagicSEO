import os
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from content_engine.optimizer import ContentOptimizer
from content_engine.media import MediaEngine

# Load Environment Variables
load_dotenv("venv/.env")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_URL = "https://griddleking.com/difference-between-ribeye-steak-and-rib-steak/"
TARGET_KEYWORD = "ribeye vs rib steak"

def fetch_content(url):
    """
    Fetches the Title and Headers/Text from the URL.
    """
    logger.info(f"🌐 Fetching content from: {url}")
    try:
        response = requests.get(url, headers={"User-Agent": "MagicSEO/1.0"})
        if response.status_code != 200:
            logger.error(f"Failed to fetch content: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.content, "html.parser")
        
        title = soup.title.string if soup.title else "No Title Found"
        
        # Get headings for context
        headings = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])]
        
        # Get first few paragraphs for context
        paragraphs = [p.get_text() for p in soup.find_all('p')[:5]]
        
        content_summary = "\n".join(headings[:5]) + "\n" + "\n".join(paragraphs)
        
        return {
            "title": title,
            "content_summary": content_summary
        }
    except Exception as e:
        logger.error(f"Error fetching content: {e}")
        return None

def run_optimization():
    print("🚀 Starting Live Optimization Test (Production-Ready Workflow)...")
    
    # 1. Fetch Content
    page_data = fetch_content(TARGET_URL)
    if not page_data:
        print("❌ Could not fetch page content.")
        return

    current_title = page_data['title']
    print(f"\n📄 Current Title: {current_title}")
    
    # 2. Setup Output Directory (Production Isolation)
    # Use slug + timestamp or just slug for this demo
    slug = TARGET_URL.strip("/").split("/")[-1]
    output_dir = os.path.join("outputs", slug)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📂 Output Directory Created: {output_dir}")

    # 3. Optimize Text (Claude Sonnet 4.5)
    print("\n🧠 Initializing Content Optimizer (Claude Sonnet 4.5)...")
    optimizer = ContentOptimizer() 
    
    # Rewrite Title
    new_title = optimizer.rewrite_title(current_title, TARGET_KEYWORD)
    print(f"   ✨ Optimized Title: {new_title}")
    
    # Generate Comparison Table
    print(f"   📊 Generating Comparison Table...")
    comparison_table = optimizer.generate_comparison_table(
        "Steak Cuts", 
        ["Ribeye Steak", "Rib Steak", "Tomahawk Steak"]
    )
    
    # 4. Generate Visuals (Gemini Imagen 4 + Claude Prompting)
    print("\n🎨 Initializing Media Engine (Gemini Imagen 4)...")
    media = MediaEngine()
    
    print(f"   📸 Generating Featured Image for: '{new_title}'")
    # Save image DIRECTLY into the output folder
    image_path = media.generate_featured_image(
        new_title, 
        style_guide="close up macro food photography, delicious, smoke, juicy",
        output_dir=output_dir
    )
    
    # 5. Save Report
    report_file = os.path.join(output_dir, "optimization_report.md")
    with open(report_file, "w") as f:
        f.write(f"# Optimization Report: {TARGET_URL}\n\n")
        f.write(f"**Target Keyword:** {TARGET_KEYWORD}\n\n")
        
        f.write("## 1. Title Optimization\n")
        f.write(f"**Original:** {current_title}\n\n")
        f.write(f"**Optimized (Claude 4.5):** {new_title}\n\n")
        
        f.write("## 2. Visual Asset (Gemini Imagen 4)\n")
        if image_path and "error" not in image_path:
            # Use relative path for portability in the folder
            rel_image_path = os.path.basename(image_path)
            f.write(f"![New Featured Image]({rel_image_path})\n")
            f.write(f"*File: {rel_image_path}*\n\n")
        else:
             f.write("*Image Generation Failed*\n\n")
        
        f.write("## 3. Comparison Table (Claude 4.5)\n")
        f.write(comparison_table)
        f.write("\n\n")

    print(f"\n✅ Optimization Complete! All assets saved to: {output_dir}/")

if __name__ == "__main__":
    run_optimization()
