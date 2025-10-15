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
        "version": "3.1",
        "description": "AI-powered SEO automation for multiple WordPress sites",
        "endpoints": {
            "/sites": "GET - List all configured sites with status",
            "/analyze": "POST - Analyze GSC data and create action plan (no execution)",
            "/execute": "POST - Full pipeline: analyze + execute content plan (may timeout on Vercel)",
            "/execute-next": "POST - Execute ONE action (serverless-safe, recommended)",
            "/export/pdf/<site_name>": "GET - Export analysis as PDF",
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
        "multi_site_support": "Configure sites via SITES_CONFIG environment variable",
        "recommended_workflow": "Use /analyze first, then call /execute-next repeatedly until all actions complete"
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

        # Enrich UPDATE actions with titles from WordPress
        # Create a temporary WordPress publisher to fetch titles
        from wordpress_publisher import WordPressPublisher
        temp_wp = WordPressPublisher(
            pipeline.site_url,
            pipeline.wp_username,
            pipeline.wp_app_password,
            rate_limit_delay=0.5  # Fast for fetching only
        )

        enriched_action_plan = []
        for action in result['action_plan'][:50]:  # Limit to top 50
            # If it's an UPDATE action with a URL but no title, fetch the title from WordPress
            if action['action_type'] == 'update' and action['url'] and not action.get('title'):
                try:
                    post = temp_wp.find_post_by_url(action['url'])
                    if post:
                        action['title'] = post.get('title', {}).get('rendered', '') if isinstance(post.get('title'), dict) else post.get('title', '')
                except Exception as e:
                    # If fetching fails, leave title empty
                    print(f"Warning: Could not fetch title for {action['url']}: {e}")
            enriched_action_plan.append(action)

        # Save the analysis result to state for later export/reference
        analysis_result = {
            "status": "analysis_complete",
            "mode": "ai_powered" if use_ai else "rule_based",
            "site": result['site'],
            "summary": result['summary'],
            "niche_insights": result.get('niche_insights'),
            "action_plan": enriched_action_plan,
            "stats": result['stats'],
            "has_ga4": ga4_path is not None
        }
        pipeline.state_mgr.save_analysis_result(analysis_result)

        # Format response
        return jsonify({
            **analysis_result,
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


@app.route("/api/execute-next", methods=["POST"])
def execute_next_action():
    """
    Execute the next pending action for a site (timeout-safe, processes 1 action only).
    Designed for Vercel serverless - stays within timeout limits.

    JSON body: {site_name}
    Returns: Action result + remaining count
    """
    data = request.get_json()
    site_name = data.get('site_name')

    if not site_name:
        return jsonify({"error": "site_name required"}), 400

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400

    try:
        from config import get_site
        from state_manager import StateManager
        from wordpress_publisher import WordPressPublisher
        from claude_content_generator import ClaudeContentGenerator
        from strategic_planner import ActionType
        from affiliate_link_manager import AffiliateLinkManager

        # Get site config
        site_config = get_site(site_name)
        state_mgr = StateManager(site_name)

        # Get next pending action
        pending = state_mgr.get_pending_actions(limit=1)
        stats = state_mgr.get_stats()
        
        print(f"DEBUG: Site {site_name}")
        print(f"DEBUG: Total actions in plan: {len(state_mgr.state.get('current_plan', []))}")
        print(f"DEBUG: Stats: {stats}")
        print(f"DEBUG: Pending actions: {len(pending)}")
        
        if not pending:
            return jsonify({
                "status": "complete",
                "message": "No pending actions",
                "stats": stats,
                "debug": {
                    "total_plan_actions": len(state_mgr.state.get('current_plan', [])),
                    "pending_count": len(pending)
                }
            })

        action_data = pending[0]

        # Initialize WordPress and content generator
        wp = WordPressPublisher(
            site_config['url'],
            site_config['wp_username'],
            site_config['wp_app_password'],
            rate_limit_delay=1.0
        )
        content_gen = ClaudeContentGenerator(anthropic_key)

        # Get affiliate manager if available
        affiliate_mgr = None
        try:
            affiliate_mgr = AffiliateLinkManager(site_name)
            if not affiliate_mgr.get_all_links():
                affiliate_mgr = None
        except:
            pass

        # Execute the action
        result = {
            "action_id": action_data['id'],
            "action_type": action_data['action_type'],
            "url": action_data.get('url'),
            "title": action_data.get('title'),
            "success": False,
            "error": None
        }

        try:
            if action_data['action_type'] == 'create':
                # Generate and publish new content
                title = action_data['title']
                keywords = action_data.get('keywords', [])

                # Do research first
                research = content_gen.research_topic(title, keywords)

                # Get internal link suggestions (FIX: was missing)
                internal_links = wp.get_internal_link_suggestions(keywords)

                # Get affiliate links if available
                affiliate_links = []
                if affiliate_mgr:
                    affiliate_links = affiliate_mgr.get_all_links()

                # Generate complete article
                article_data = content_gen.generate_article(
                    topic_title=title,
                    keywords=keywords,
                    research=research,
                    meta_description=f"Learn about {title}",
                    internal_links=internal_links,  # FIX: Add internal links
                    affiliate_links=affiliate_links
                )

                # Create the post
                publish_result = wp.create_post(
                    title=article_data.get('title', title),
                    content=article_data['content'],
                    meta_title=article_data.get('meta_title'),  # FIX: Add meta title
                    meta_description=article_data.get('meta_description'),  # FIX: Add meta description
                    categories=article_data.get('categories', []),
                    tags=article_data.get('tags', [])
                )

                # Update affiliate link usage if any were added
                if affiliate_mgr and affiliate_links:
                    for link in affiliate_links:
                        if link['url'] in article_data['content']:
                            affiliate_mgr.increment_usage(link['id'])

                # FIX: Extract post_id from PublishResult object
                if publish_result.success:
                    result['post_id'] = publish_result.post_id
                    result['success'] = True
                    state_mgr.mark_completed(action_data['id'], publish_result.post_id)
                else:
                    result['error'] = publish_result.error
                    result['success'] = False

            elif action_data['action_type'] == 'update':
                # Fetch and update existing content
                post = wp.find_post_by_url(action_data['url'])
                if not post:
                    raise Exception(f"Post not found: {action_data['url']}")

                post_id = post['id']
                existing_content = post.get('content', {}).get('rendered', '')
                title = action_data.get('title', '') or post.get('title', {}).get('rendered', '')
                keywords = action_data.get('keywords', [])

                # Generate improved content using generate_article with existing_content
                # First do research
                research = content_gen.research_topic(title, keywords)

                # Get internal link suggestions (FIX: was missing)
                internal_links = wp.get_internal_link_suggestions(keywords)

                # Get affiliate links for this update if available
                affiliate_links = []
                if affiliate_mgr:
                    affiliate_links = affiliate_mgr.get_all_links()

                # Generate updated article
                article_data = content_gen.generate_article(
                    topic_title=title,
                    keywords=keywords,
                    research=research,
                    meta_description=f"Updated: {title}",
                    existing_content=existing_content,
                    internal_links=internal_links,  # FIX: Add internal links
                    affiliate_links=affiliate_links
                )

                # Update the post with new content
                publish_result = wp.update_post(
                    post_id,
                    title=article_data.get('title', title),
                    content=article_data['content'],
                    meta_title=article_data.get('meta_title'),  # FIX: Add meta title
                    meta_description=article_data.get('meta_description'),  # FIX: Add meta description
                    categories=article_data.get('categories', []),
                    tags=article_data.get('tags', [])
                )

                # Update affiliate link usage if any were added
                if affiliate_mgr and affiliate_links:
                    # Count how many affiliate links appear in the new content
                    for link in affiliate_links:
                        if link['url'] in article_data['content']:
                            affiliate_mgr.increment_usage(link['id'])

                # FIX: Handle PublishResult properly
                if publish_result.success:
                    result['post_id'] = post_id
                    result['success'] = True
                    state_mgr.mark_completed(action_data['id'], post_id)
                else:
                    result['error'] = publish_result.error
                    result['success'] = False

            else:
                result['error'] = f"Unsupported action type: {action_data['action_type']}"

        except Exception as e:
            result['error'] = str(e)

        # Get updated stats
        stats = state_mgr.get_stats()

        return jsonify({
            "status": "action_executed",
            "result": result,
            "stats": stats,
            "has_more": stats['pending'] > 0
        })

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
            
            print(f"DEBUG SITES: {site_name}")
            print(f"DEBUG SITES: Plan length: {len(state_mgr.state.get('current_plan', []))}")
            print(f"DEBUG SITES: Stats: {stats}")
            
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


@app.route("/api/export/pdf/<site_name>", methods=["GET"])
def export_analysis_pdf(site_name):
    """
    Export the last analysis result as a styled PDF report.
    """
    try:
        from state_manager import StateManager
        from flask import make_response
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import io

        state_mgr = StateManager(site_name)
        analysis = state_mgr.get_analysis_result()

        if not analysis:
            return jsonify({
                "error": "No analysis available for this site",
                "message": "Please run an analysis first"
            }), 404

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a56db'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=20
        )

        # Title
        story.append(Paragraph(f"SEO Analysis Report", title_style))
        story.append(Paragraph(f"{analysis.get('site', site_name)}", styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Summary Stats
        story.append(Paragraph("Executive Summary", heading_style))
        summary = analysis.get('summary', {})
        summary_data = [
            ['Total Actions', str(summary.get('total_actions', 0))],
            ['Updates Recommended', str(summary.get('updates', 0))],
            ['New Posts Suggested', str(summary.get('creates', 0))],
            ['High Priority Items', str(summary.get('high_priority', 0))],
        ]
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))

        # Niche Insights
        niche = analysis.get('niche_insights')
        if niche:
            story.append(Paragraph("Niche Intelligence", heading_style))

            if niche.get('summary'):
                story.append(Paragraph(f"<b>Market Overview:</b> {niche['summary']}", styles['Normal']))
                story.append(Spacer(1, 0.15*inch))

            if niche.get('trends'):
                story.append(Paragraph("<b>Top Trends:</b>", styles['Normal']))
                for trend in niche['trends'][:5]:
                    story.append(Paragraph(f"• {trend}", styles['Normal']))
                story.append(Spacer(1, 0.15*inch))

            if niche.get('opportunities'):
                story.append(Paragraph("<b>Key Opportunities:</b>", styles['Normal']))
                for opp in niche['opportunities'][:5]:
                    story.append(Paragraph(f"• {opp}", styles['Normal']))
                story.append(Spacer(1, 0.2*inch))

        # Top Priority Actions
        story.append(PageBreak())
        story.append(Paragraph("Recommended Actions", heading_style))

        actions = analysis.get('action_plan', [])[:15]  # Top 15
        if actions:
            action_data = [['Priority', 'Type', 'Title/URL', 'Reasoning']]
            for action in actions:
                action_data.append([
                    f"{action.get('priority_score', 0):.1f}",
                    action.get('action_type', '').upper(),
                    action.get('title') or action.get('url', '')[:40] + '...' if len(action.get('url', '')) > 40 else action.get('url', ''),
                    action.get('reasoning', '')[:60] + '...' if len(action.get('reasoning', '')) > 60 else action.get('reasoning', '')
                ])

            actions_table = Table(action_data, colWidths=[0.7*inch, 0.8*inch, 2.5*inch, 2.5*inch])
            actions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(actions_table)

        # Build PDF
        doc.build(story)

        # Prepare response
        buffer.seek(0)
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{site_name}_seo_analysis_{datetime.now().strftime("%Y%m%d")}.pdf"'

        return response

    except ImportError:
        return jsonify({
            "error": "PDF export not available",
            "message": "reportlab library not installed. Install with: pip install reportlab"
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to generate PDF",
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