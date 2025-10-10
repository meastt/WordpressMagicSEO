"""
Serverless Flask API for Vercel – COMPLETE SEO Automation System
----------------------------------------------------------------
Enhanced version with full sitemap analysis, strategic planning, and Claude-powered content.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask_cors import CORS
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from seo_automation_main import SEOAutomationPipeline

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["GET"])
def home():
    """API information endpoint."""
    return jsonify({
        "name": "WordPress Magic SEO - Multi-Site Portfolio Manager",
        "version": "3.0",
        "description": "AI-powered SEO automation for multiple WordPress sites",
        "endpoints": {
            "/sites": "GET - List all configured sites with status",
            "/analyze": "POST - Analyze GSC data and create action plan (no execution)",
            "/execute": "POST - Full pipeline: analyze + execute content plan",
            "/health": "GET - Health check"
        },
        "required_fields": {
            "file": "GSC CSV export (12 months)",
            "site_url": "WordPress site URL (or use site_name with SITES_CONFIG)",
            "username": "WordPress username",
            "application_password": "WordPress application password"
        },
        "optional_fields": {
            "site_name": "Pre-configured site name (e.g., griddleking.com)",
            "schedule_mode": "all_at_once (default), daily, hourly",
            "batch_size": "Posts per batch (default: 3)",
            "delay_hours": "Hours between batches (default: 8)",
            "max_actions": "Limit actions for testing (default: None)",
            "anthropic_api_key": "Claude API key (or set ANTHROPIC_API_KEY env)"
        },
        "multi_site_support": "Configure sites via SITES_CONFIG environment variable"
    })


@app.route("/analyze", methods=["POST"])
def analyze_only():
    """
    Analyze GSC data and create action plan WITHOUT executing.
    Returns the complete plan for review.
    """
    
    # Validate file upload
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]  # <-- ADD THIS LINE
    
    if file.filename == "" or not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({"error": "Please upload a CSV or Excel file"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # Get required parameters
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
    
    if not all([site_url, username, application_password]):
        return jsonify({
            "error": "Missing required fields: site_url, username, application_password"
        }), 400
    
    anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    
    try:
        # Initialize pipeline
        pipeline = SEOAutomationPipeline(
            gsc_csv_path=file_path,
            site_url=site_url,
            wp_username=username,
            wp_app_password=application_password,
            anthropic_api_key=anthropic_key
        )
        
        # Run analysis only (steps 1-4)
        from multi_site_content_agent import GSCProcessor
        from sitemap_analyzer import SitemapAnalyzer
        from strategic_planner import StrategicPlanner
        
        # Step 1: Load GSC data
        gsc_processor = GSCProcessor(file_path)
        gsc_df = gsc_processor.load()
        
        # Step 2: Fetch sitemap
        sitemap_analyzer = SitemapAnalyzer(site_url)
        sitemap_urls = sitemap_analyzer.fetch_sitemap()
        sitemap_data = sitemap_analyzer.compare_with_gsc(sitemap_urls, gsc_df)
        
        # Step 3: Find duplicates
        duplicate_analysis = sitemap_analyzer.find_duplicate_content_candidates(gsc_df)
        
        # Step 4: Create plan
        planner = StrategicPlanner(gsc_df, sitemap_data)
        action_plan = planner.create_master_plan(duplicate_analysis)
        plan_summary = planner.get_plan_summary()
        
        # Format response
        plan_items = []
        for action in action_plan[:50]:  # Limit to top 50 for response size
            plan_items.append({
                "action_type": action.action_type.value,
                "url": action.url,
                "title": action.title,
                "keywords": action.keywords,
                "priority_score": round(action.priority_score, 2),
                "reasoning": action.reasoning,
                "redirect_target": action.redirect_target,
                "estimated_impact": action.estimated_impact
            })
        
        return jsonify({
            "status": "analysis_complete",
            "summary": {
                "total_actions": plan_summary['total_actions'],
                "deletes": plan_summary['deletes'],
                "redirects": plan_summary['redirects'],
                "updates": plan_summary['updates'],
                "creates": plan_summary['creates'],
                "high_priority": plan_summary['high_priority'],
                "medium_priority": plan_summary['medium_priority'],
                "low_priority": plan_summary['low_priority']
            },
            "sitemap_analysis": {
                "dead_content_count": len(sitemap_data['dead_content']),
                "performing_content_count": len(sitemap_data['performing_content']),
                "orphaned_content_count": len(sitemap_data['orphaned_content'])
            },
            "duplicate_groups": len(duplicate_analysis),
            "action_plan": plan_items,
            "note": "This is analysis only. Use /execute endpoint to run the plan."
        })
    
    except Exception as e:
        return jsonify({
            "error": "Analysis failed",
            "details": str(e)
        }), 500


@app.route("/execute", methods=["POST"])
def execute_full_pipeline():
    """
    Full pipeline: Analyze GSC data, create plan, and execute content actions.
    This will actually publish/update/delete content on WordPress.
    """
    
    # Validate file upload
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "" or not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({"error": "Please upload a CSV or Excel file"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # Get required parameters
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
    
    if not all([site_url, username, application_password]):
        return jsonify({
            "error": "Missing required fields: site_url, username, application_password"
        }), 400
    
    # Get optional parameters
    schedule_mode = request.form.get("schedule_mode", "all_at_once")
    batch_size = int(request.form.get("batch_size", 3))
    delay_hours = float(request.form.get("delay_hours", 8))
    max_actions = request.form.get("max_actions")
    if max_actions:
        max_actions = int(max_actions)
    
    anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    
    if not anthropic_key:
        return jsonify({
            "error": "ANTHROPIC_API_KEY required for content generation"
        }), 400
    
    try:
        # Initialize and run complete pipeline
        pipeline = SEOAutomationPipeline(
            gsc_csv_path=file_path,
            site_url=site_url,
            wp_username=username,
            wp_app_password=application_password,
            anthropic_api_key=anthropic_key
        )
        
        # Generate output filename
        from datetime import datetime
        output_csv = os.path.join(
            UPLOAD_FOLDER, 
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Run the complete pipeline
        summary = pipeline.run(
            schedule_mode=schedule_mode,
            posts_per_batch=batch_size,
            delay_hours=delay_hours,
            max_actions=max_actions,
            output_csv=output_csv
        )
        
        # Read results CSV to return
        results_data = []
        if os.path.exists(output_csv):
            import csv
            with open(output_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                results_data = list(reader)
        
        return jsonify({
            "status": "execution_complete",
            "summary": summary,
            "results": results_data[:100],  # Limit to first 100 for response size
            "results_file": output_csv,
            "note": "Results saved to CSV. Review AI-generated content on your site."
        })
    
    except Exception as e:
        return jsonify({
            "error": "Execution failed",
            "details": str(e)
        }), 500


@app.route("/sites", methods=["GET"])
def list_sites_endpoint():
    """
    List all configured sites with their current status.
    Returns site names and pending action counts.
    """
    try:
        from config import list_sites
        from state_manager import StateManager
        
        sites = list_sites()
        site_status = []
        
        for site_name in sites:
            state_mgr = StateManager(site_name)
            stats = state_mgr.get_stats()
            site_status.append({
                'name': site_name,
                'pending_actions': stats['pending'],
                'completed_actions': stats['completed'],
                'total_actions': stats['total_actions']
            })
        
        return jsonify({
            "sites": site_status,
            "total_sites": len(sites)
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to load sites",
            "details": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Vercel."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    # For local testing
    app.run(debug=True, port=5000)