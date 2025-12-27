import os
import logging
import requests
import argparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from content_engine.optimizer import ContentOptimizer
from content_engine.media import MediaEngine
from content_engine.taxonomy import TaxonomyManager
from live_bridge import LiveBridge

# Load Environment Variables
load_dotenv("venv/.env")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_URL = "https://griddleking.com/griddle-boil-water-pots-pans/"
TARGET_KEYWORD = "boil water on griddle"

def fetch_content(url):
    """
    Fetches the Title and Headers/Text from the URL.
    """
    logger.info(f"🌐 Fetching content from: {url}")
    try:
        response = requests.get(url, headers={"User-Agent": "MagicSEO/1.0"})
        if response.status_code != 200:
            logger.warning(f"Public URL returned {response.status_code}. Trying WordPress API fallback...")
            return fetch_content_from_api(url)
            
        soup = BeautifulSoup(response.content, "html.parser")
        
        title = soup.title.string if soup.title else "No Title Found"
        
        # Get headings for context
        headings = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])]
        paragraphs = [p.get_text() for p in soup.find_all('p')[:5]]
        content_summary = "\n".join(headings[:5]) + "\n" + "\n".join(paragraphs)

        # Get full content (Surgical selection)
        # We want ONLY the post body, excluding sidebars, headers, footers
        content_obj = soup.find('div', class_='entry-content') or soup.find('article') or soup.find('main')
        
        if content_obj:
            # Strip scripts, styles, and ads if possible
            for tag in content_obj.find_all(['script', 'style', 'ins', 'iframe']):
                tag.decompose()
            full_html = str(content_obj.decode_contents()) # Get internal HTML only
        else:
            full_html = ""
        
        return {
            "title": title,
            "content": full_html,
            "content_summary": content_summary
        }
    except Exception as e:
        logger.error(f"Error fetching content: {e}")
        return None

def fetch_content_from_api(url):
    """
    Fallback: Fetch content directly from WordPress REST API.
    Useful when public URL returns 404 (scheduled/draft posts, CDN caching).
    """
    from urllib.parse import urlparse
    from wordpress.publisher import WordPressPublisher
    
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_").upper()
    
    site_url = os.getenv(f"WP_{domain}_URL")
    username = os.getenv(f"WP_{domain}_USERNAME")
    password = os.getenv(f"WP_{domain}_PASSWORD")
    
    if not all([site_url, username, password]):
        logger.error("WordPress API credentials not found for fallback.")
        return None
    
    try:
        pub = WordPressPublisher(site_url=site_url, username=username, application_password=password)
        post = pub.find_post_or_page_by_url(url)
        
        if not post:
            logger.error(f"Post not found via API: {url}")
            return None
        
        title = post.get('title', {}).get('rendered', 'No Title')
        content_html = post.get('content', {}).get('rendered', '')
        
        # Parse for summary
        soup = BeautifulSoup(content_html, "html.parser")
        headings = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])]
        paragraphs = [p.get_text() for p in soup.find_all('p')[:5]]
        content_summary = "\n".join(headings[:5]) + "\n" + "\n".join(paragraphs)
        
        logger.info(f"✅ Fetched content via WordPress API (Post ID: {post.get('id')})")
        
        return {
            "title": title,
            "content": content_html,
            "content_summary": content_summary
        }
    except Exception as e:
        logger.error(f"API fallback failed: {e}")
        return None

def run_optimization(push_live=False):
    print(f"🚀 Starting {'LIVE ' if push_live else '' }Optimization Test (Full Strategic Pipeline)...")
    
    # 1. Fetch Content
    page_data = fetch_content(TARGET_URL)
    if not page_data:
        print("❌ Could not fetch page content.")
        return

    current_title = page_data['title']
    content_summary = page_data['content_summary']
    print(f"\n📄 Current Title: {current_title}")
    
    # 2. Setup Output Directory
    slug = TARGET_URL.strip("/").split("/")[-1]
    output_dir = os.path.join("outputs", slug)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📂 Output Directory: {output_dir}")

    # 3. Initialize Engines
    optimizer = ContentOptimizer()
    media = MediaEngine()
    taxonomy = TaxonomyManager(llm_client=optimizer)
    
    # 4. STEP 1: Competitive Analysis (The Cheat Code)
    print(f"\n🕵️‍♂️ Running Competitive Analysis for: '{TARGET_KEYWORD}'...")
    # Using mock metrics for analysis since we don't have GSC live for this specific post right now
    analysis = optimizer.analyzer.analyze_competitive_gap(
        target_keyword=TARGET_KEYWORD,
        your_current_content=content_summary,
        your_current_position=12,
        impressions=1200,
        clicks=25
    )
    
    brief = optimizer.analyzer.generate_improvement_brief(analysis)
    print(f"   ✅ Competitive Brief Generated.")
    
    # 5. STEP 2: Content Optimization (Claude 4.5 Sonnet)
    print("\n🧠 Optimizing Content based on Competitive Intelligence...")
    
    # Rewrite Title with Brief context
    new_title = optimizer.rewrite_title(current_title, TARGET_KEYWORD, competitive_brief=brief)
    print(f"   ✨ Optimized Title: {new_title}")
    
    # Generate Comparison Table (Requested in Brief if multimedia_needed)
    print(f"   📊 Generating Strategic Comparison Table...")
    comparison_table = optimizer.generate_comparison_table(
        "Premium Steak Cuts", 
        ["Ribeye Steak", "Rib Steak", "Porterhouse", "T-Bone"]
    )
    
    # 6. STEP 3: Media Generation (Imagen 4 with Watermark)
    print("\n🎨 Generating Branded Visual Assets...")
    print(f"   📸 Creating Featured Image with 'Griddle King' Watermark...")
    image_path = media.generate_featured_image(
        new_title, 
        style_guide="macro food photography, grilling, charcoal smoke, authentic backyard setting, sizzling meat",
        output_dir=output_dir,
        target_keyword=TARGET_KEYWORD
    )
    
    # NEW: Generate Alt-Text using Vision
    alt_text = "N/A"
    if image_path and os.path.exists(image_path):
        print(f"   👁️ Analyzing Image for Alt-Text...")
        alt_text = media.generate_alt_text(image_path, TARGET_KEYWORD)
        print(f"   ✨ AI Alt-Text: {alt_text}")

    # NEW: STEP 3.5: Smart Content Fusion (The Secret Sauce)
    print("\n🔥 Fusing Content with Strategic Insights (Full Body Rewrite)...")
    optimized_html = optimizer.smart_fusion(
        original_html=page_data['content'],
        competitive_brief=brief,
        table_md=comparison_table
    )

    # NEW: Taxonomy Suggestions
    print("\n🏷️ Generating Taxonomy Suggestions...")
    post_categories = taxonomy.suggest_categories(content_summary, ["Outdoor Cooking", "Gear", "Recipes", "Steak Guide"])
    post_tags = taxonomy.generate_tags(content_summary)
    print(f"   📂 Categories: {', '.join(post_categories)}")
    print(f"   🏷️ Tags: {', '.join(post_tags)}")
    
    # 7. Save Final Strategic Report
    report_file = os.path.join(output_dir, "strategic_optimization_report.md")
    with open(report_file, "w") as f:
        f.write(f"# Strategic Optimization Report: {TARGET_URL}\n\n")
        f.write(f"**Target Keyword:** `{TARGET_KEYWORD}`\n")
        f.write(f"**Estimated Ranking Lift:** {analysis.get('estimated_ranking_improvement', 'N/A')}\n\n")
        
        f.write("## 1. Competitive Intelligence Summary\n")
        f.write("Based on analysis of Top 10 results:\n\n")
        f.write(f"**Search Intent:** {analysis.get('search_intent', 'N/A')}\n")
        f.write("**Critical Gaps Identified:**\n")
        for topic in analysis.get('missing_topics', [])[:5]:
            f.write(f"- {topic}\n")
        f.write("\n")
        
        f.write("## 2. Optimized Metadata\n")
        f.write(f"**Original Title:** {current_title}\n\n")
        f.write(f"**AI-Optimized Title (Claude 4.5):** {new_title}\n\n")
        
        if image_path and "error" not in image_path:
            rel_image_path = os.path.basename(image_path)
            f.write(f"![{alt_text}]({rel_image_path})\n")
            f.write(f"**Alt Text:** {alt_text}\n")
            f.write(f"**Filename:** `{rel_image_path}`\n")
            f.write(f"*Status: Generated with 'Griddle King' watermark*\n\n")
        else:
             f.write("*Image Generation Failed*\n\n")
        
        f.write("## 4. Taxonomy & Categories\n")
        f.write(f"**Suggested Categories:** {', '.join(post_categories)}\n")
        f.write(f"**Suggested Tags:** {', '.join(post_tags)}\n\n")

        f.write("## 5. Enhanced Content Elements\n")
        f.write("### Strategic Comparison Table\n")
        f.write(comparison_table)
        f.write("\n\n")
        
        f.write("--- \n")
        f.write("*Report generated by Magic SEO Intelligence Engine*")

    # 8. STEP 4: The Bridge (Optional Push to Live WP)
    if push_live:
        print("\n🌐 BRIDGE: Pushing updates live to WordPress...")
        bridge = LiveBridge(target_url=TARGET_URL)
        
        # Consolidate data for the bridge
        push_data = {
            "title": new_title,
            "categories": post_categories,
            "tags": post_tags,
            "image_path": image_path,
            "alt_text": alt_text,
            "optimized_content": optimized_html,
            "comparison_table": comparison_table,
            # Note: We intentionally do NOT send update_date to avoid scheduling issues
            "status": "publish" # Force publish status
        }
        
        success = bridge.push_optimization(TARGET_URL, push_data)
        if success:
            print(f"✅ LIVE UPDATE COMPLETE: {TARGET_URL}")
        else:
            print("❌ Live Update Failed. Check logs.")

    print(f"\n✅ FULL STRATEGIC OPTIMIZATION COMPLETE!")
    print(f"📂 Assets & Strategy saved to: {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize a blog post using AI Content Engine.")
    parser.add_argument("--push", action="store_true", help="Push the optimized content live to WordPress.")
    args = parser.parse_args()
    
    run_optimization(push_live=args.push)
