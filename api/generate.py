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
from affiliate_link_manager import AffiliateLinkManager
from affiliate_link_updater import AffiliateLinkUpdater

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
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


@app.route("/api/analyze", methods=["POST"])
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
    
    # Get all parameters
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
    site_name = request.form.get("site_name")
    anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")

    try:
        # Check if manual config is provided (takes priority)
        if site_url and username and application_password:
            # Manual/legacy mode - use individual params
            pipeline = SEOAutomationPipeline(
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                site_url=site_url,
                wp_username=username,
                wp_app_password=application_password,
                anthropic_api_key=anthropic_key
            )
        elif site_name:
            # Multi-site mode - load from config
            pipeline = SEOAutomationPipeline(
                site_name=site_name,
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                anthropic_api_key=anthropic_key
            )
        else:
            return jsonify({
                "error": "Must provide either (site_url, username, application_password) OR site_name"
            }), 400
        
        # Run analysis with AI planner
        use_ai = request.form.get("use_ai_planner", "true").lower() == "true"
        force_new = request.form.get("force_new_plan", "false").lower() == "true"
        result = pipeline.run(
            execution_mode="view_plan",
            use_ai_planner=use_ai,
            force_new_plan=force_new
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


@app.route("/api/execute", methods=["POST"])
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
    
    # Get all parameters
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
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
        # Check if manual config is provided (takes priority)
        if site_url and username and application_password:
            # Manual/legacy mode - use individual params
            pipeline = SEOAutomationPipeline(
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                site_url=site_url,
                wp_username=username,
                wp_app_password=application_password,
                anthropic_api_key=anthropic_key
            )
        elif site_name:
            # Multi-site mode - load from config
            pipeline = SEOAutomationPipeline(
                site_name=site_name,
                gsc_csv_path=gsc_path,
                ga4_csv_path=ga4_path,
                anthropic_api_key=anthropic_key
            )
        else:
            return jsonify({
                "error": "Must provide either (site_url, username, application_password) OR site_name"
            }), 400
        
        # Generate output filename
        output_csv = os.path.join(
            UPLOAD_FOLDER,
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Run pipeline with specified execution mode
        force_new = request.form.get("force_new_plan", "false").lower() == "true"
        result = pipeline.run(
            execution_mode=execution_mode,
            schedule_mode=schedule_mode,
            posts_per_batch=batch_size,
            delay_hours=delay_hours,
            limit=limit,
            output_csv=output_csv,
            use_ai_planner=use_ai,
            force_new_plan=force_new
        )

        # Get error details from result
        error_details = result.get('errors', [])

        response_data = {
            "status": "execution_complete",
            "mode": "ai_powered" if use_ai else "rule_based",
            "execution_mode": execution_mode,
            "site": result.get('site'),
            "summary": result.get('summary', {}),
            "stats": result.get('stats', {}),
            "completed_actions": result.get('completed_actions', []),
            "actions_executed": limit if limit else "all",
            "note": "Check WordPress site for updated content"
        }

        # Add errors if any
        if error_details:
            response_data['errors'] = error_details
            response_data['note'] = f"{len(error_details)} action(s) failed - check errors for details"

        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({
            "error": "Execution failed",
            "details": str(e)
        }), 500


@app.route("/api/sites", methods=["GET"])
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
                'pending_actions': stats.get('pending', 0),
                'completed_actions': stats.get('completed', 0),
                'total_actions': stats.get('total_actions', 0)
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


@app.route("/api/niche/<site_name>", methods=["GET"])
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


@app.route("/api/plan/<site_name>", methods=["GET"])
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


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Vercel."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0-ai"
    })


# ============================================================================
# AFFILIATE LINK MANAGEMENT ENDPOINTS
# ============================================================================

@app.route("/api/affiliate/links", methods=["GET"])
def get_affiliate_links():
    """
    Get all affiliate links for a site.
    Query params: site_name (required)
    """
    site_name = request.args.get('site_name')
    
    if not site_name:
        return jsonify({"error": "site_name parameter required"}), 400
    
    try:
        manager = AffiliateLinkManager(site_name)
        links = manager.get_all_links()
        stats = manager.get_stats()
        
        return jsonify({
            "site": site_name,
            "links": links,
            "stats": stats
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve affiliate links",
            "details": str(e)
        }), 500


@app.route("/api/affiliate/links/add", methods=["POST"])
def add_affiliate_link():
    """
    Add a single affiliate link manually.
    JSON body: {site_name, url, brand, product_name, product_type, keywords (optional)}
    """
    data = request.get_json()
    
    site_name = data.get('site_name')
    url = data.get('url')
    brand = data.get('brand')
    product_name = data.get('product_name')
    product_type = data.get('product_type')
    keywords = data.get('keywords', [])
    
    if not all([site_name, url, brand, product_name, product_type]):
        return jsonify({
            "error": "Missing required fields: site_name, url, brand, product_name, product_type"
        }), 400
    
    try:
        manager = AffiliateLinkManager(site_name)
        link = manager.add_link(url, brand, product_name, product_type, keywords)
        
        return jsonify({
            "success": True,
            "link": link,
            "message": "Affiliate link added successfully"
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to add affiliate link",
            "details": str(e)
        }), 500


@app.route("/api/affiliate/links/upload", methods=["POST"])
def upload_affiliate_links_csv():
    """
    Upload multiple affiliate links via CSV.
    Expects: multipart/form-data with 'csv_file' and 'site_name'
    """
    site_name = request.form.get('site_name')
    
    if not site_name:
        return jsonify({"error": "site_name parameter required"}), 400
    
    if 'csv_file' not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400
    
    csv_file = request.files['csv_file']
    
    if csv_file.filename == '' or not csv_file.filename.endswith('.csv'):
        return jsonify({"error": "Please upload a CSV file"}), 400
    
    try:
        # Read CSV content
        csv_content = csv_file.read().decode('utf-8')
        
        # Process the CSV
        manager = AffiliateLinkManager(site_name)
        results = manager.add_links_from_csv(csv_content)
        
        return jsonify({
            "success": True,
            "site": site_name,
            "results": results,
            "message": f"Processed CSV: {results['added']} added, {results['skipped']} skipped"
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to process CSV",
            "details": str(e)
        }), 500


@app.route("/api/affiliate/links/delete/<int:link_id>", methods=["DELETE"])
def delete_affiliate_link(link_id):
    """
    Delete an affiliate link by ID.
    Query params: site_name (required)
    """
    site_name = request.args.get('site_name')
    
    if not site_name:
        return jsonify({"error": "site_name parameter required"}), 400
    
    try:
        manager = AffiliateLinkManager(site_name)
        success = manager.delete_link(link_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Link {link_id} deleted successfully"
            })
        else:
            return jsonify({
                "error": f"Link {link_id} not found"
            }), 404
    
    except Exception as e:
        return jsonify({
            "error": "Failed to delete link",
            "details": str(e)
        }), 500


@app.route("/api/affiliate/update-content", methods=["POST"])
def update_content_with_affiliates():
    """
    Use AI to update content with affiliate links.
    
    JSON body:
    {
        "site_name": "domain.com",
        "post_id": 123,  // Optional - for updating specific post
        "content": "HTML content",  // Optional if post_id provided
        "title": "Post title",
        "keywords": ["keyword1", "keyword2"],  // Optional
        "auto_publish": false  // If true, updates the post in WordPress
    }
    """
    data = request.get_json()
    
    site_name = data.get('site_name')
    post_id = data.get('post_id')
    content = data.get('content')
    title = data.get('title')
    keywords = data.get('keywords', [])
    auto_publish = data.get('auto_publish', False)
    
    if not site_name:
        return jsonify({"error": "site_name required"}), 400
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400
    
    try:
        # Get affiliate links for this site
        link_manager = AffiliateLinkManager(site_name)
        available_links = link_manager.get_all_links()
        
        if not available_links:
            return jsonify({
                "error": "No affiliate links configured for this site",
                "message": "Please add affiliate links first"
            }), 400
        
        # If post_id provided but no content, fetch from WordPress
        if post_id and not content:
            from config import get_site
            from wordpress_publisher import WordPressPublisher
            
            site_config = get_site(site_name)
            wp = WordPressPublisher(
                site_config['url'],
                site_config['wp_username'],
                site_config['wp_app_password']
            )
            
            post_data = wp.get_post(post_id)
            content = post_data.get('content', {}).get('rendered', '')
            title = title or post_data.get('title', {}).get('rendered', '')
        
        if not content or not title:
            return jsonify({"error": "content and title required"}), 400
        
        # Update content with AI
        updater = AffiliateLinkUpdater(anthropic_key)
        result = updater.update_content_with_affiliate_links(
            content=content,
            title=title,
            available_links=available_links,
            keywords=keywords
        )
        
        # Update usage counts for added links
        for added_link in result.get('links_added', []):
            for link in available_links:
                if link['url'] == added_link.get('url'):
                    link_manager.increment_usage(link['id'])
                    break
        
        # Auto-publish if requested
        if auto_publish and post_id and result.get('success'):
            from config import get_site
            from wordpress_publisher import WordPressPublisher
            
            site_config = get_site(site_name)
            wp = WordPressPublisher(
                site_config['url'],
                site_config['wp_username'],
                site_config['wp_app_password']
            )
            
            wp.update_post(post_id, content=result['updated_content'])
            result['published'] = True
            result['post_id'] = post_id
        
        return jsonify({
            "success": result.get('success', False),
            **result
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to update content",
            "details": str(e)
        }), 500


@app.route("/api/affiliate/bulk-update", methods=["POST"])
def bulk_update_posts_with_affiliates():
    """
    Bulk update multiple posts with affiliate links.
    
    JSON body:
    {
        "site_name": "domain.com",
        "post_ids": [123, 456, 789],  // WordPress post IDs
        "auto_publish": false,  // If true, updates posts in WordPress
        "limit": 10  // Optional - max posts to update
    }
    """
    data = request.get_json()
    
    site_name = data.get('site_name')
    post_ids = data.get('post_ids', [])
    auto_publish = data.get('auto_publish', False)
    limit = data.get('limit')
    
    if not site_name:
        return jsonify({"error": "site_name required"}), 400
    
    if not post_ids:
        return jsonify({"error": "post_ids required"}), 400
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400
    
    try:
        from config import get_site
        from wordpress_publisher import WordPressPublisher
        
        # Get site config and WordPress connection
        site_config = get_site(site_name)
        wp = WordPressPublisher(
            site_config['url'],
            site_config['wp_username'],
            site_config['wp_app_password']
        )
        
        # Get affiliate links
        link_manager = AffiliateLinkManager(site_name)
        available_links = link_manager.get_all_links()
        
        if not available_links:
            return jsonify({
                "error": "No affiliate links configured for this site"
            }), 400
        
        # Limit posts if specified
        if limit:
            post_ids = post_ids[:limit]
        
        # Fetch posts from WordPress
        posts = []
        for post_id in post_ids:
            try:
                post_data = wp.get_post(post_id)
                posts.append({
                    'id': post_id,
                    'title': post_data.get('title', {}).get('rendered', ''),
                    'content': post_data.get('content', {}).get('rendered', ''),
                    'keywords': []  # Could extract from tags/categories if needed
                })
            except Exception as e:
                print(f"Error fetching post {post_id}: {e}")
                continue
        
        # Update posts with AI
        updater = AffiliateLinkUpdater(anthropic_key)
        results = updater.batch_update_posts(posts, available_links)
        
        # Publish if requested
        if auto_publish:
            for result in results:
                if result.get('success') and result.get('post_id'):
                    try:
                        wp.update_post(
                            result['post_id'],
                            content=result['updated_content']
                        )
                        result['published'] = True
                    except Exception as e:
                        result['publish_error'] = str(e)
        
        # Update usage counts
        for result in results:
            for added_link in result.get('links_added', []):
                for link in available_links:
                    if link['url'] == added_link.get('url'):
                        link_manager.increment_usage(link['id'])
                        break
        
        return jsonify({
            "success": True,
            "total_posts": len(results),
            "results": results
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to bulk update posts",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    # For local testing
    app.run(debug=True, port=5000)