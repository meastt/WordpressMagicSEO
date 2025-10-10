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
    Enhanced: Analyze GSC + GA4 data with AI-powered niche intelligence.
    Supports both multi-site (site_name) and legacy (individual params) modes.
    Returns comprehensive action plan for review.
    """
    
    # Validate GSC file upload
    if "gsc_file" not in request.files and "file" not in request.files:
        return jsonify({"error": "No GSC file uploaded (use 'gsc_file' or 'file')"}), 400
    
    gsc_file = request.files.get("gsc_file") or request.files.get("file")
    
    if gsc_file.filename == "" or not gsc_file.filename.endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({"error": "Please upload a CSV or Excel file for GSC data"}), 400
    
    gsc_filename = secure_filename(gsc_file.filename)
    gsc_path = os.path.join(UPLOAD_FOLDER, gsc_filename)
    gsc_file.save(gsc_path)
    
    # Optional GA4 file upload
    ga4_path = None
    if "ga4_file" in request.files:
        ga4_file = request.files["ga4_file"]
        if ga4_file.filename and ga4_file.filename.endswith(('.csv', '.xlsx', '.xls')):
            ga4_filename = secure_filename(ga4_file.filename)
            ga4_path = os.path.join(UPLOAD_FOLDER, ga4_filename)
            ga4_file.save(ga4_path)
    
    # Check for site_name (multi-site mode) or individual params (legacy mode)
    site_name = request.form.get("site_name")
    anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    
    try:
        # Initialize pipeline (multi-site or legacy mode)
        if site_name:
            # Multi-site mode
            pipeline = SEOAutomationPipeline(
                site_name=site_name,
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                anthropic_api_key=anthropic_key
            )
        else:
            # Legacy mode - need individual params
            site_url = request.form.get("site_url")
            username = request.form.get("username")
            application_password = request.form.get("application_password")
            
            if not all([site_url, username, application_password]):
                return jsonify({
                    "error": "Must provide either 'site_name' OR (site_url, username, application_password)"
                }), 400
            
            pipeline = SEOAutomationPipeline(
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                site_url=site_url,
                wp_username=username,
                wp_app_password=application_password,
                anthropic_api_key=anthropic_key
            )
        
        # Run analysis with AI planner
        use_ai = request.form.get("use_ai_planner", "true").lower() == "true"
        result = pipeline.run(
            execution_mode="view_plan",
            use_ai_planner=use_ai
        )
        
        # Format response
        return jsonify({
            "status": "analysis_complete",
            "mode": "ai_powered" if use_ai else "rule_based",
            "site": result['site'],
            "summary": result['summary'],
            "niche_insights": result.get('niche_insights'),
            "action_plan": result['action_plan'][:50],  # Limit to top 50
            "stats": result['stats'],
            "has_ga4": ga4_path is not None,
            "note": "This is analysis only. Use /execute endpoint to run actions."
        })
    
    except Exception as e:
        return jsonify({
            "error": "Analysis failed",
            "details": str(e)
        }), 500


@app.route("/execute", methods=["POST"])
def execute_full_pipeline():
    """
    Enhanced: Execute AI-powered SEO automation with flexible execution modes.
    Supports multi-site config and dual data input (GSC + GA4).
    """
    
    # Validate GSC file upload
    if "gsc_file" not in request.files and "file" not in request.files:
        return jsonify({"error": "No GSC file uploaded"}), 400
    
    gsc_file = request.files.get("gsc_file") or request.files.get("file")
    if gsc_file.filename == "" or not gsc_file.filename.endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({"error": "Please upload a CSV or Excel file"}), 400
    
    gsc_filename = secure_filename(gsc_file.filename)
    gsc_path = os.path.join(UPLOAD_FOLDER, gsc_filename)
    gsc_file.save(gsc_path)
    
    # Optional GA4 file
    ga4_path = None
    if "ga4_file" in request.files:
        ga4_file = request.files["ga4_file"]
        if ga4_file.filename and ga4_file.filename.endswith(('.csv', '.xlsx', '.xls')):
            ga4_filename = secure_filename(ga4_file.filename)
            ga4_path = os.path.join(UPLOAD_FOLDER, ga4_filename)
            ga4_file.save(ga4_path)
    
    # Get execution parameters
    site_name = request.form.get("site_name")
    execution_mode = request.form.get("execution_mode", "execute_all")
    schedule_mode = request.form.get("schedule_mode", "all_at_once")
    batch_size = int(request.form.get("batch_size", 3))
    delay_hours = float(request.form.get("delay_hours", 8))
    limit = request.form.get("limit")
    if limit:
        limit = int(limit)
    
    use_ai = request.form.get("use_ai_planner", "true").lower() == "true"
    anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    
    if not anthropic_key:
        return jsonify({
            "error": "ANTHROPIC_API_KEY required for AI-powered execution"
        }), 400
    
    try:
        # Initialize pipeline (multi-site or legacy mode)
        if site_name:
            pipeline = SEOAutomationPipeline(
                site_name=site_name,
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                anthropic_api_key=anthropic_key
            )
        else:
            # Legacy mode
            site_url = request.form.get("site_url")
            username = request.form.get("username")
            application_password = request.form.get("application_password")
            
            if not all([site_url, username, application_password]):
                return jsonify({
                    "error": "Must provide either 'site_name' OR (site_url, username, application_password)"
                }), 400
            
            pipeline = SEOAutomationPipeline(
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                site_url=site_url,
                wp_username=username,
                wp_app_password=application_password,
                anthropic_api_key=anthropic_key
            )
        
        # Generate output filename
        output_csv = os.path.join(
            UPLOAD_FOLDER,
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Run pipeline with specified execution mode
        result = pipeline.run(
            execution_mode=execution_mode,
            schedule_mode=schedule_mode,
            posts_per_batch=batch_size,
            delay_hours=delay_hours,
            limit=limit,
            output_csv=output_csv,
            use_ai_planner=use_ai
        )
        
        return jsonify({
            "status": "execution_complete",
            "mode": "ai_powered" if use_ai else "rule_based",
            "execution_mode": execution_mode,
            "site": result.get('site'),
            "summary": result.get('summary', {}),
            "stats": result.get('stats', {}),
            "actions_executed": limit if limit else "all",
            "note": "Check WordPress site for updated content"
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


@app.route("/niche/<site_name>", methods=["GET"])
def get_niche_research(site_name):
    """
    Get cached niche research for a site.
    Returns 404 if no cached research available.
    """
    try:
        from state_manager import StateManager
        
        state_mgr = StateManager(site_name)
        cached = state_mgr.get_niche_research()
        
        if not cached:
            return jsonify({
                "error": "No cached niche research available",
                "site": site_name
            }), 404
        
        import json
        report = json.loads(cached)
        
        return jsonify({
            "site": site_name,
            "niche_research": report,
            "cached": True
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve niche research",
            "details": str(e)
        }), 500


@app.route("/plan/<site_name>", methods=["GET"])
def get_action_plan(site_name):
    """
    Get current action plan for a site.
    Shows pending and completed actions.
    """
    try:
        from state_manager import StateManager
        
        state_mgr = StateManager(site_name)
        plan = state_mgr.state.get('current_plan', [])
        stats = state_mgr.get_stats()
        
        # Get pending actions
        pending = state_mgr.get_pending_actions()
        
        return jsonify({
            "site": site_name,
            "stats": stats,
            "total_actions": len(plan),
            "pending_actions": pending[:20],  # Top 20 pending
            "all_actions_count": len(plan)
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve action plan",
            "details": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Vercel."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0-ai"
    })


if __name__ == "__main__":
    # For local testing
    app.run(debug=True, port=5000)