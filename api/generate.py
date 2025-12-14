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
import requests
import json

# Lazy imports to avoid loading heavy modules at function startup
try:
    from core.pipeline import SEOAutomationPipeline
    from affiliate.manager import AffiliateLinkManager
    from affiliate.updater import AffiliateLinkUpdater
except ImportError as e:
    print(f"⚠️  Warning: Some modules failed to import: {e}")
    # These will be imported inside functions that need them


def sanitize_for_json(value):
    """
    Sanitize a value to ensure it can be safely serialized to JSON.
    Handles strings with unescaped quotes, special characters, etc.
    """
    if value is None:
        return None
    if isinstance(value, str):
        # Try to encode/decode to ensure valid UTF-8
        try:
            # Replace any problematic characters
            value = value.encode('utf-8', errors='replace').decode('utf-8')
            # Truncate very long strings that might cause JSON issues
            if len(value) > 10000:
                value = value[:10000] + "... [truncated]"
        except Exception:
            value = str(value)[:1000]  # Fallback truncation
    return value

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
    try:
        from utils.error_handler import (
            validate_file_upload,
            validate_site_config,
            handle_api_error,
            AppError,
            ErrorCategory
        )
        
        # Validate GSC file upload
        gsc_file = request.files.get("gsc_file") or request.files.get("file")
        if not gsc_file:
            raise AppError(
                "No GSC file uploaded",
                category=ErrorCategory.USER_ERROR,
                suggestion="Please upload a GSC data file (CSV or Excel format).",
                status_code=400
            )
        
        validate_file_upload(gsc_file)
        
        gsc_filename = secure_filename(gsc_file.filename)
        gsc_path = os.path.join(UPLOAD_FOLDER, gsc_filename)
        gsc_file.save(gsc_path)
        
        # Optional GA4 file upload
        ga4_path = None
        if "ga4_file" in request.files:
            ga4_file = request.files["ga4_file"]
            if ga4_file.filename:
                try:
                    validate_file_upload(ga4_file)
                    ga4_filename = secure_filename(ga4_file.filename)
                    ga4_path = os.path.join(UPLOAD_FOLDER, ga4_filename)
                    ga4_file.save(ga4_path)
                except AppError:
                    # GA4 is optional, so we'll just skip it if invalid
                    pass
        
        # Get all parameters
        site_url = request.form.get("site_url")
        username = request.form.get("username")
        application_password = request.form.get("application_password")
        site_name = request.form.get("site_name")
        anthropic_key = request.form.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
        
        # Validate site configuration
        validate_site_config(site_name, site_url, username, application_password)
        
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
        from wordpress.publisher import WordPressPublisher
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

        # Save the full action plan to StateManager so it can be executed later
        # This makes the actions available to /api/execute-next
        full_action_plan = result.get('action_plan', [])
        if full_action_plan:
            # Ensure each action has an ID
            import hashlib
            for i, action in enumerate(full_action_plan):
                if 'id' not in action:
                    # Generate a unique ID based on action content
                    id_string = f"{action.get('action_type', '')}_{action.get('url', '')}_{action.get('title', '')}_{i}"
                    action_id = hashlib.md5(id_string.encode()).hexdigest()[:12]
                    action['id'] = action_id

            pipeline.state_mgr.update_plan(full_action_plan)
            print(f"Saved {len(full_action_plan)} actions to StateManager for {site_name or site_url}")

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
        from utils.error_handler import handle_api_error
        return handle_api_error(e, include_traceback=True)


@app.route('/api/save-state', methods=['POST'])
def save_state():
    """
    Manually save state for a site.
    """
    try:
        from core.state_manager import StateManager
        
        data = request.get_json()
        site_name = data.get('site_name')
        action = data.get('action')
        
        if not site_name:
            return jsonify({'success': False, 'error': 'Site name required'})
        
        state_mgr = StateManager(site_name)
        
        if action == 'save':
            # Force save current state
            state_mgr.save()
            
            return jsonify({
                'success': True,
                'message': f'State saved for {site_name}',
                'stats': state_mgr.get_stats()
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid action'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/refresh-sites', methods=['POST'])
def refresh_sites():
    """
    Force refresh sites status after state changes.
    """
    try:
        from config import list_sites
        from core.state_manager import StateManager
        
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
            'success': True,
            'sites': site_status,
            'total_sites': len(sites)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/create-test-plan', methods=['POST'])
def create_test_plan():
    """
    Create a test action plan to verify state persistence.
    """
    try:
        from core.state_manager import StateManager

        data = request.get_json()
        site_name = data.get('site_name')

        if not site_name:
            return jsonify({'success': False, 'error': 'Site name required'})

        state_mgr = StateManager(site_name)

        # Create a test plan with 5 actions
        test_plan = []
        for i in range(5):
            test_plan.append({
                'id': f'test_action_{i+1}',
                'action_type': 'update',
                'url': f'https://{site_name}/test-page-{i+1}/',
                'title': f'Test Page {i+1}',
                'keywords': [f'test keyword {i+1}'],
                'priority_score': 8.0 - i * 0.5,
                'reasoning': f'Test action {i+1} for state persistence verification',
                'estimated_impact': 'High',
                'status': 'pending'
            })

        # Update the plan
        state_mgr.update_plan(test_plan)

        return jsonify({
            'success': True,
            'message': f'Test plan created for {site_name}',
            'stats': state_mgr.get_stats()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-action', methods=['POST'])
def delete_action():
    """
    Delete a specific action from the plan (cannot be undone).
    """
    try:
        from core.state_manager import StateManager

        data = request.get_json()
        site_name = data.get('site_name')
        action_id = data.get('action_id')

        if not site_name or not action_id:
            return jsonify({'success': False, 'error': 'Site name and action_id required'})

        state_mgr = StateManager(site_name)

        # Find and remove the action
        current_plan = state_mgr.state.get('current_plan', [])
        original_count = len(current_plan)

        # Filter out the action with the given ID
        updated_plan = [a for a in current_plan if a.get('id') != action_id]

        if len(updated_plan) == original_count:
            return jsonify({'success': False, 'error': 'Action not found'})

        # Update the plan
        state_mgr.state['current_plan'] = updated_plan
        if 'stats' not in state_mgr.state:
            state_mgr.state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
        state_mgr.state['stats']['total_actions'] = len(updated_plan)
        state_mgr.state['stats']['pending'] = len([a for a in updated_plan if a.get('status') != 'completed'])
        state_mgr.state['stats']['completed'] = len([a for a in updated_plan if a.get('status') == 'completed'])
        state_mgr.save()
        
        print(f"DEBUG DELETE: Updated stats after deletion: {state_mgr.get_stats()}")

        print(f"DEBUG DELETE: Deleted action {action_id} from {site_name}")

        return jsonify({
            'success': True,
            'message': f'Action deleted from {site_name}',
            'stats': state_mgr.get_stats()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/delete-actions-batch', methods=['POST'])
def delete_actions_batch():
    """
    Delete multiple actions from the plan in a single operation (prevents race conditions).
    Expects: { site_name: str, action_ids: list[str] }
    """
    try:
        from core.state_manager import StateManager

        data = request.get_json()
        site_name = data.get('site_name')
        action_ids = data.get('action_ids', [])

        if not site_name:
            return jsonify({'success': False, 'error': 'Site name required'})

        if not action_ids or not isinstance(action_ids, list):
            return jsonify({'success': False, 'error': 'action_ids must be a non-empty list'})

        state_mgr = StateManager(site_name)

        # Find and remove all specified actions in one operation
        current_plan = state_mgr.state.get('current_plan', [])
        original_count = len(current_plan)

        # Convert action_ids to a set for faster lookup
        ids_to_delete = set(action_ids)

        # Filter out all actions with IDs in the deletion list
        updated_plan = [a for a in current_plan if a.get('id') not in ids_to_delete]

        deleted_count = original_count - len(updated_plan)

        if deleted_count == 0:
            return jsonify({'success': False, 'error': 'No matching actions found'})

        # Update the plan and stats
        state_mgr.state['current_plan'] = updated_plan
        if 'stats' not in state_mgr.state:
            state_mgr.state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
        state_mgr.state['stats']['total_actions'] = len(updated_plan)
        state_mgr.state['stats']['pending'] = len([a for a in updated_plan if a.get('status') != 'completed'])
        state_mgr.state['stats']['completed'] = len([a for a in updated_plan if a.get('status') == 'completed'])
        state_mgr.save()

        print(f"Batch deleted {deleted_count} actions from {site_name}")

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} action{"s" if deleted_count != 1 else ""} from {site_name}',
            'deleted_count': deleted_count,
            'stats': state_mgr.get_stats()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/clear-plan', methods=['POST'])
def clear_plan():
    """
    Clear the action plan for a site (wipes all state).
    """
    try:
        from core.state_manager import StateManager

        data = request.get_json()
        site_name = data.get('site_name')

        if not site_name:
            return jsonify({'success': False, 'error': 'Site name required'})

        state_mgr = StateManager(site_name)

        # Clear all state
        state_mgr.clear_state()

        return jsonify({
            'success': True,
            'message': f'State cleared for {site_name}',
            'stats': state_mgr.get_stats()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/load-state', methods=['POST'])
def load_state():
    """
    Manually load state for a site.
    """
    try:
        from core.state_manager import StateManager
        
        data = request.get_json()
        site_name = data.get('site_name')
        action = data.get('action')
        
        if not site_name:
            return jsonify({'success': False, 'error': 'Site name required'})
        
        state_mgr = StateManager(site_name)
        
        if action == 'load':
            # Force reload state
            state_mgr.state = state_mgr._load()
            return jsonify({
                'success': True,
                'message': f'State loaded for {site_name}',
                'stats': state_mgr.get_stats()
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid action'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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


@app.route("/api/execute-selected", methods=["POST"])
def execute_selected_actions():
    """
    Execute specific actions by their IDs (supports multiple).

    JSON body: {
        site_name: string,
        action_ids: string[]  // Array of action IDs to execute
    }

    Returns: Results for each action executed
    """
    print("=== /api/execute-selected called ===")

    try:
        data = request.get_json()
        site_name = data.get('site_name')
        action_ids = data.get('action_ids', [])
        # Optional: frontend can send full action data as fallback
        action_data_override = data.get('actions', {})  # Dict mapping action_id -> action_data
        generate_images = data.get('generate_images', False)  # Image generation flag
        print(f"🖼️  Image generation flag received: {generate_images}")

        if not site_name:
            return jsonify({"error": "site_name required"}), 400

        if not action_ids or not isinstance(action_ids, list):
            return jsonify({"error": "action_ids must be a non-empty array"}), 400

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400

        from config import get_site
        from core.state_manager import StateManager
        from wordpress.publisher import WordPressPublisher
        from content.generators.claude_generator import ClaudeContentGenerator
        from affiliate.manager import AffiliateLinkManager

        site_config = get_site(site_name)
        state_mgr = StateManager(site_name)

        # Get the requested actions by ID
        all_actions = state_mgr.state.get('current_plan', [])
        actions_to_execute = [a.copy() for a in all_actions if a.get('id') in action_ids]

        if not actions_to_execute:
            return jsonify({
                "error": "No matching actions found",
                "requested_ids": action_ids
            }), 404

        # Merge in any action data from frontend (if provided) to override missing fields
        for action in actions_to_execute:
            action_id = action.get('id')
            action_type = action.get('action_type')
            
            # Debug logging for redirect actions
            if action_type in ['redirect_301', 'redirect']:
                print(f"  🔍 Processing redirect action {action_id}:")
                print(f"     State redirect_target: {repr(action.get('redirect_target'))}")
            
            if action_id in action_data_override:
                frontend_data = action_data_override[action_id]
                
                if action_type in ['redirect_301', 'redirect']:
                    print(f"     Frontend redirect_target: {repr(frontend_data.get('redirect_target'))}")
                
                # Merge frontend data, prioritizing it for missing fields
                # For redirect_target, use frontend value if it's valid, otherwise preserve state value
                for key, value in frontend_data.items():
                    if key == 'redirect_target':
                        # Use frontend redirect_target only if it's a valid non-empty value
                        if value is not None and value != '' and str(value).strip() != '':
                            action[key] = value
                            if action_type in ['redirect_301', 'redirect']:
                                print(f"     ✅ Using frontend redirect_target: {value}")
                        # If frontend value is empty/None, preserve state value (don't override)
                        # The state value (if it exists) will remain in action[key]
                        elif action_type in ['redirect_301', 'redirect']:
                            print(f"     📌 Preserving state redirect_target: {repr(action.get('redirect_target'))}")
                    else:
                        # For other fields, only override if current value is missing/empty
                        if value and not action.get(key):
                            action[key] = value
            
            # If redirect_target is missing AND not in frontend override, check state
            if action_type in ['redirect_301', 'redirect']:
                if not action.get('redirect_target'):
                    print(f"     ⚠️  redirect_target missing after merge, will try AI selection")

        # Validate redirect_301 actions have redirect_target before execution
        # Use AI-based selection if targets are missing
        import pandas as pd
        
        # Get merged data for AI-based redirect target selection
        merged_data_df = None
        try:
            merged_data = state_mgr.state.get('merged_data')
            if merged_data:
                if isinstance(merged_data, pd.DataFrame):
                    merged_data_df = merged_data
                elif isinstance(merged_data, list):
                    # Convert list of dicts to DataFrame
                    merged_data_df = pd.DataFrame(merged_data)
                elif isinstance(merged_data, dict) and 'page' in merged_data:
                    # Single row dict
                    merged_data_df = pd.DataFrame([merged_data])
        except Exception as e:
            print(f"  ⚠️  Could not load merged data for AI selection: {e}")
        
        # Process redirect actions missing targets
        redirect_actions_needing_targets = [
            action for action in actions_to_execute
            if action.get('action_type') in ['redirect_301', 'redirect']
            and (not action.get('redirect_target') or action.get('redirect_target', '').strip() == '')
        ]

        print(f"\n{'='*80}")
        print(f"🔍 REDIRECT TARGET SELECTION DIAGNOSTIC")
        print(f"{'='*80}")
        print(f"Total actions to execute: {len(actions_to_execute)}")
        print(f"Redirect actions needing targets: {len(redirect_actions_needing_targets)}")
        if redirect_actions_needing_targets:
            for act in redirect_actions_needing_targets:
                print(f"  - {act.get('url', 'NO URL')} (ID: {act.get('id', 'NO ID')})")
                print(f"    Current redirect_target: {repr(act.get('redirect_target'))}")
        print(f"Merged data available: {merged_data_df is not None}")
        if merged_data_df is not None:
            print(f"Merged data shape: {merged_data_df.shape}")
            print(f"Merged data columns: {list(merged_data_df.columns)}")
        print(f"{'='*80}\n")

        if redirect_actions_needing_targets and merged_data_df is not None and 'page' in merged_data_df.columns:
            # Use AI-based selection for missing redirect targets
            print(f"  🤖 Using AI to select redirect targets (with GSC data) for {len(redirect_actions_needing_targets)} actions...")
            from analysis.planners.ai_planner import AIStrategicPlanner
            
            try:
                ai_planner = AIStrategicPlanner(anthropic_key)
                
                for action in redirect_actions_needing_targets:
                    source_url = action.get('url', '')
                    reasoning = action.get('reasoning', '')
                    
                    if not source_url:
                        continue
                    
                    # Get URLs with performance metrics
                    by_page = merged_data_df.groupby('page').agg({
                        'impressions': 'sum',
                        'clicks': 'sum',
                        'ctr': 'mean',
                        'position': 'mean'
                    }).reset_index()
                    by_page = by_page.sort_values('impressions', ascending=False)
                    
                    urls_with_metrics = []
                    for _, row in by_page.iterrows():
                        urls_with_metrics.append({
                            'url': row['page'],
                            'impressions': int(row['impressions']),
                            'clicks': int(row['clicks']),
                            'ctr': row['ctr'],
                            'position': row['position']
                        })
                    
                    # Use AI to select best target
                    selected_target = ai_planner._ai_select_redirect_target(
                        source_url=source_url,
                        reasoning=reasoning,
                        available_urls=urls_with_metrics
                    )
                    
                    if selected_target:
                        action['redirect_target'] = selected_target
                        print(f"     ✅ AI selected redirect target for {source_url}")
                        print(f"        Target: {selected_target}")
                        print(f"        Action ID: {action.get('id')}")
                        print(f"        Verification: action['redirect_target'] = {repr(action.get('redirect_target'))}")
                    else:
                        print(f"     ❌ AI could not select target for {source_url}")
                        print(f"        Reasoning: {reasoning[:200] if reasoning else 'No reasoning provided'}")
                        
            except Exception as e:
                print(f"  ⚠️  AI-based redirect target selection failed: {e}")
                import traceback
                traceback.print_exc()
        elif redirect_actions_needing_targets:
            # merged_data not available - try to get URLs from WordPress
            print(f"  ⚠️  Merged data not available (or missing 'page' column), trying to load URLs from WordPress for AI selection...")
            print(f"     Redirect actions needing targets: {len(redirect_actions_needing_targets)}")
            try:
                wp_temp = WordPressPublisher(
                    site_config['url'],
                    site_config['wp_username'],
                    site_config['wp_app_password'],
                    rate_limit_delay=0.5
                )
                posts = wp_temp.get_all_posts()
                available_urls = [post.get('link', '') for post in posts if post.get('link')]
                
                if available_urls:
                    print(f"  ✓ Loaded {len(available_urls)} URLs from WordPress")
                    from analysis.planners.ai_planner import AIStrategicPlanner
                    ai_planner = AIStrategicPlanner(anthropic_key)
                    
                    # Create simple URL list with default metrics
                    urls_with_metrics = [
                        {'url': url, 'impressions': 100, 'clicks': 10, 'ctr': 0.1, 'position': 20.0}
                        for url in available_urls[:100]  # Limit to top 100
                    ]
                    
                    for action in redirect_actions_needing_targets:
                        source_url = action.get('url', '')
                        reasoning = action.get('reasoning', '')
                        
                        if not source_url:
                            continue
                        
                        selected_target = ai_planner._ai_select_redirect_target(
                            source_url=source_url,
                            reasoning=reasoning,
                            available_urls=urls_with_metrics
                        )
                        
                        if selected_target:
                            action['redirect_target'] = selected_target
                            print(f"     ✅ AI selected redirect target (from WordPress URLs) for {source_url}")
                            print(f"        Target: {selected_target}")
                            print(f"        Action ID: {action.get('id')}")
                            print(f"        Verification: action['redirect_target'] = {repr(action.get('redirect_target'))}")
            except Exception as e:
                print(f"  ⚠️  Could not load URLs from WordPress for AI selection: {e}")
                import traceback
                traceback.print_exc()
        
        # Final validation - check if any redirect actions still lack targets
        print(f"\n{'='*80}")
        print(f"🔍 REDIRECT TARGET FINAL VALIDATION")
        print(f"{'='*80}")

        redirect_actions_final = [a for a in actions_to_execute if a.get('action_type') in ['redirect_301', 'redirect']]
        print(f"Total redirect actions: {len(redirect_actions_final)}")

        for action in redirect_actions_final:
            source_url = action.get('url', '')
            redirect_target = action.get('redirect_target')
            action_id = action.get('id', '')

            print(f"\nAction ID: {action_id}")
            print(f"  Source: {source_url}")
            print(f"  Target: {repr(redirect_target)}")

            if not redirect_target or redirect_target.strip() == '':
                reasoning = action.get('reasoning', '')
                print(f"  ❌ ERROR: Missing redirect_target!")
                print(f"     Action data keys: {list(action.keys())}")
                print(f"     Frontend override keys: {list(action_data_override.get(action_id, {}).keys())}")
                print(f"     Reasoning: {reasoning[:200] if reasoning else 'No reasoning'}")
                # Fail fast - don't proceed if redirect_target is missing
                # The execution handler will return proper error message
            else:
                print(f"  ✅ Has valid redirect_target")

        print(f"{'='*80}\n")

        # Initialize services
        wp = WordPressPublisher(
            site_config['url'],
            site_config['wp_username'],
            site_config['wp_app_password'],
            rate_limit_delay=1.0
        )
        content_gen = ClaudeContentGenerator(anthropic_key)

        try:
            affiliate_mgr = AffiliateLinkManager(site_name)
            if not affiliate_mgr.get_all_links():
                affiliate_mgr = None
        except Exception as e:
            print(f"   ⚠ Could not initialize affiliate link manager: {e}")
            affiliate_mgr = None

        # Execute each selected action
        results = []
        for action_data in actions_to_execute:
            result = {
                "action_id": sanitize_for_json(action_data.get('id')),
                "action_type": sanitize_for_json(action_data.get('action_type')),
                "url": sanitize_for_json(action_data.get('url')),
                "title": sanitize_for_json(action_data.get('title')),
                "success": False,
                "error": None
            }

            # Skip if already completed
            if action_data.get('status') == 'completed':
                result['success'] = True
                result['skipped'] = True
                result['reason'] = 'Already completed'
                results.append(result)
                continue

            # Execute the action (reuse execute logic from execute-next)
            try:
                if action_data['action_type'] == 'create':
                    title = action_data['title']
                    keywords = action_data.get('keywords', [])

                    # Duplicate detection
                    existing_posts = wp.get_all_posts()
                    duplicate_found = False
                    for post in existing_posts:
                        post_title = post.get('title', {}).get('rendered', '') if isinstance(post.get('title'), dict) else post.get('title', '')
                        if post_title.strip().lower() == title.strip().lower():
                            result['success'] = True
                            result['post_id'] = post.get('id')
                            result['skipped'] = True
                            result['reason'] = 'Duplicate post already exists'
                            state_mgr.mark_completed(action_data['id'], post.get('id'))
                            duplicate_found = True
                            break

                    if duplicate_found:
                        results.append(result)
                        continue

                    # Create new post
                    research = content_gen.research_topic(title, keywords)
                    internal_links = wp.get_internal_link_suggestions(keywords)
                    affiliate_links = affiliate_mgr.get_all_links() if affiliate_mgr else []

                    article_data = content_gen.generate_article(
                        topic_title=title,
                        keywords=keywords,
                        research=research,
                        meta_description=f"Learn about {title}",
                        internal_links=internal_links,
                        affiliate_links=affiliate_links
                    )

                    # TEMPORARY: Skip image generation to avoid Vercel timeout
                    # TODO: Implement background job processing for images
                    if generate_images:
                        print(f"  ⚠️  Image generation temporarily disabled to avoid timeout")
                        print(f"  ℹ️  Article will be created with [Image:...] placeholders")
                        print(f"  ℹ️  TODO: Implement background processing for image generation")
                        # Skip image generation for now
                        # try:
                        #     from gemini_image_generator import GeminiImageGenerator
                        #     gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                        #     if gemini_key:
                        #         print(f"  🖼️  Image generation enabled - processing image placeholders...")
                        #         image_gen = GeminiImageGenerator(gemini_key)
                        #         updated_content, image_info = image_gen.replace_placeholders_with_images(
                        #             content=article_data['content'],
                        #             article_title=article_data.get('title', title),
                        #             keywords=keywords,
                        #             wp_publisher=wp,
                        #             upload_to_wordpress=True
                        #         )
                        #         article_data['content'] = updated_content
                        #         if image_info:
                        #             print(f"  ✅ Generated and uploaded {len(image_info)} images")
                        #     else:
                        #         print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                        # except Exception as e:
                        #     print(f"  ⚠️  Image generation failed: {e}")
                        #     import traceback
                        #     traceback.print_exc()
                        #     # Continue without images if generation fails

                    # SIMPLIFIED QA/SEO Validation to avoid timeout
                    # Only log summary, skip detailed reports
                    try:
                        from content.validators.qa_validator import ContentQAValidator
                        from content.validators.seo_validator import SEOChecklistValidator

                        # Quick content QA
                        validator = ContentQAValidator()
                        is_valid, qa_report = validator.validate_article(
                            article_data,
                            title,
                            {'min_word_count': 2000}
                        )
                        print(f"  📋 Content QA: {qa_report['summary']}")
                        result['qa_validation'] = {'summary': qa_report['summary']}

                        # Quick SEO validation
                        seo_validator = SEOChecklistValidator()
                        article_data['keywords'] = keywords
                        is_seo_valid, seo_report = seo_validator.validate_seo(
                            article_data,
                            primary_keyword=keywords[0] if keywords else None,
                            site_url=site_config['url']
                        )
                        print(f"  🔍 SEO Score: {seo_report['seo_score']}/100")
                        result['seo_validation'] = {
                            'seo_score': seo_report['seo_score'],
                            'summary': seo_report['summary']
                        }

                    except Exception as e:
                        print(f"  ⚠️  Validation skipped (timeout prevention): {e}")
                        # Continue with publishing

                    publish_result = wp.create_post(
                        title=article_data.get('title', title),
                        content=article_data['content'],
                        meta_title=article_data.get('meta_title'),
                        meta_description=article_data.get('meta_description'),
                        categories=article_data.get('categories', []),
                        tags=article_data.get('tags', [])
                    )

                    if publish_result.success:
                        result['post_id'] = publish_result.post_id
                        result['success'] = True
                        state_mgr.mark_completed(action_data['id'], publish_result.post_id)

                        # Update affiliate usage
                        if affiliate_mgr and affiliate_links:
                            for link in affiliate_links:
                                if link['url'] in article_data['content']:
                                    affiliate_mgr.increment_usage(link['id'])
                    else:
                        result['error'] = sanitize_for_json(publish_result.error)

                elif action_data['action_type'] == 'update':
                    # SMART UPDATE: Detect page type and route appropriately
                    from page_type_detector import PageTypeDetector, PageType, UpdateStrategy

                    url = action_data['url']
                    page_info = PageTypeDetector.get_update_info(url)

                    print(f"  📄 Page Type Detection:")
                    print(f"     URL: {url}")
                    print(f"     Type: {page_info['page_type']}")
                    print(f"     Strategy: {page_info['strategy']}")
                    print(f"     {page_info['explanation']}")

                    if page_info['should_skip']:
                        # Skip this page type (date archives, search, etc.)
                        result['success'] = True
                        result['skipped'] = True
                        result['reason'] = page_info['explanation']
                        state_mgr.mark_completed(action_data['id'], None)
                        print(f"  ⏭️  Skipping: {page_info['explanation']}")

                    elif page_info['strategy'] == UpdateStrategy.META_ONLY.value:
                        # META_ONLY update - Categories, Tags, Homepage, Author
                        print(f"  🏷️  Meta-only update for {page_info['page_type']}")

                        if page_info['page_type'] == PageType.HOMEPAGE.value:
                            # Homepage handling (same as execute-next)
                            result['success'] = True
                            result['skipped'] = True
                            result['reason'] = 'Homepage meta updates handled in execute-next endpoint'
                            print(f"  ⚠️  Homepage updates should use execute-next endpoint")

                        elif page_info['page_type'] == PageType.CATEGORY.value:
                            category = wp.find_category_by_url(url)
                            if not category:
                                result['error'] = sanitize_for_json(f"Category not found: {url}")
                            else:
                                category_id = category['id']
                                current_name = category.get('name', '')
                                keywords = action_data.get('keywords', [])

                                meta_title = f"{current_name} | {site_name}" if keywords else current_name
                                meta_description = f"Explore our comprehensive {current_name.lower()} content. {' '.join(keywords[:3])}"

                                publish_result = wp.update_category_meta(
                                    category_id,
                                    meta_title=meta_title,
                                    meta_description=meta_description
                                )

                                if publish_result.success:
                                    result['success'] = True
                                    result['meta_only'] = True
                                    state_mgr.mark_completed(action_data['id'], category_id)
                                else:
                                    result['error'] = sanitize_for_json(publish_result.error)

                        elif page_info['page_type'] == PageType.TAG.value:
                            tag = wp.find_tag_by_url(url)
                            if not tag:
                                result['error'] = sanitize_for_json(f"Tag not found: {url}")
                            else:
                                tag_id = tag['id']
                                current_name = tag.get('name', '')
                                keywords = action_data.get('keywords', [])

                                meta_title = f"{current_name} Articles | {site_name}"
                                meta_description = f"Browse all articles tagged with {current_name.lower()}. {' '.join(keywords[:3])}"

                                publish_result = wp.update_tag_meta(
                                    tag_id,
                                    meta_title=meta_title,
                                    meta_description=meta_description
                                )

                                if publish_result.success:
                                    result['success'] = True
                                    result['meta_only'] = True
                                    state_mgr.mark_completed(action_data['id'], tag_id)
                                else:
                                    result['error'] = sanitize_for_json(publish_result.error)

                        elif page_info['page_type'] == PageType.AUTHOR.value:
                            result['success'] = True
                            result['skipped'] = True
                            result['reason'] = 'Author archives require custom WordPress setup for SEO meta updates'
                            state_mgr.mark_completed(action_data['id'], None)

                    else:
                        # FULL CONTENT UPDATE - For posts only (not WordPress pages)
                        print(f"  📝 Full content update for post/page")
                        
                        # Find post or page - check both endpoints
                        found_item = wp.find_post_or_page_by_url(url)
                        if not found_item:
                            result['error'] = sanitize_for_json(f"Post or page not found: {url}")
                        else:
                            item_type = found_item.get('_wp_type', 'post')
                            item_id = found_item['id']
                            
                            # CRITICAL SAFETY CHECK: If it's a WordPress PAGE (not POST), 
                            # only update SEO meta, NOT content (to avoid breaking static pages)
                            if item_type == 'page':
                                print(f"  ⚠️  WordPress PAGE detected - switching to meta-only update for safety")
                                print(f"     WordPress pages (like /about/, /contact/) should only have SEO meta updated, not content")
                                
                                keywords = action_data.get('keywords', [])
                                title = action_data.get('title', '') or found_item.get('title', {}).get('rendered', '')
                                
                                meta_title = title if title else found_item.get('title', {}).get('rendered', '')
                                meta_description = action_data.get('reasoning', '')
                                if keywords:
                                    meta_description = f"{', '.join(keywords[:3])}. {meta_description[:100]}" if meta_description else f"Learn about {', '.join(keywords[:3])}"
                                else:
                                    meta_description = meta_description[:155] if meta_description else "Learn more about our content."
                                
                                # Update ONLY meta fields, NOT content or title
                                publish_result = wp.update_post(
                                    item_id,
                                    title=None,
                                    content=None,  # NEVER update page content
                                    meta_title=meta_title,
                                    meta_description=meta_description,
                                    item_type='page'  # Use pages endpoint for WordPress pages
                                )
                                
                                if publish_result.success:
                                    result['post_id'] = item_id
                                    result['success'] = True
                                    result['meta_only'] = True
                                    result['wp_page'] = True
                                    state_mgr.mark_completed(action_data['id'], item_id)
                                    print(f"  ✅ WordPress page SEO meta updated successfully (content preserved)")
                                else:
                                    result['error'] = sanitize_for_json(publish_result.error)
                            
                            else:
                                # It's a POST - safe to do full content update
                                post_id = item_id
                                existing_content = found_item.get('content', {}).get('rendered', '')
                                title = action_data.get('title', '') or found_item.get('title', {}).get('rendered', '')
                                keywords = action_data.get('keywords', [])

                                research = content_gen.research_topic(title, keywords)
                                internal_links = wp.get_internal_link_suggestions(keywords)
                                affiliate_links = affiliate_mgr.get_all_links() if affiliate_mgr else []

                                article_data = content_gen.generate_article(
                                    topic_title=title,
                                    keywords=keywords,
                                    research=research,
                                    meta_description=f"Updated: {title}",
                                    existing_content=existing_content,
                                    internal_links=internal_links,
                                    affiliate_links=affiliate_links
                                )

                                # Generate images if requested
                                if generate_images:
                                    try:
                                        from content.generators.gemini_images import GeminiImageGenerator
                                        gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                                        if gemini_key:
                                            print(f"  🖼️  Image generation enabled - processing image placeholders...")
                                            image_gen = GeminiImageGenerator(gemini_key)
                                            updated_content, image_info = image_gen.replace_placeholders_with_images(
                                                content=article_data['content'],
                                                article_title=article_data.get('title', title),
                                                keywords=keywords,
                                                wp_publisher=wp,
                                                upload_to_wordpress=True
                                            )
                                            article_data['content'] = updated_content
                                            if image_info:
                                                print(f"  ✅ Generated and uploaded {len(image_info)} images")
                                        else:
                                            print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                                    except Exception as e:
                                        print(f"  ⚠️  Image generation failed: {e}")
                                        import traceback
                                        traceback.print_exc()
                                        # Continue without images if generation fails

                                publish_result = wp.update_post(
                                    post_id,
                                    title=article_data.get('title', title),
                                    content=article_data['content'],
                                    meta_title=article_data.get('meta_title'),
                                    meta_description=article_data.get('meta_description'),
                                    categories=article_data.get('categories', []),
                                    tags=article_data.get('tags', [])
                                )

                                if publish_result.success:
                                    result['post_id'] = post_id
                                    result['success'] = True
                                    state_mgr.mark_completed(action_data['id'], post_id)

                                    # Update affiliate usage
                                    if affiliate_mgr and affiliate_links:
                                        for link in affiliate_links:
                                            if link['url'] in article_data['content']:
                                                affiliate_mgr.increment_usage(link['id'])
                                else:
                                    result['error'] = sanitize_for_json(publish_result.error)

                elif action_data['action_type'] == 'redirect_301':
                    # Create 301 redirect
                    source_url = action_data['url']
                    target_url = action_data.get('redirect_target')

                    if not target_url or target_url.strip() == '':
                        result['error'] = sanitize_for_json(f'redirect_target is required for redirect_301 actions. Source URL: {source_url}. Please check the action plan and ensure redirect_target is set.')
                        print(f"  ❌ Redirect failed - missing redirect_target for {source_url}")
                        print(f"     Action data keys: {list(action_data.keys())}")
                        print(f"     redirect_target value: {repr(target_url)}")
                    else:
                        # Normalize target URL
                        target_url = target_url.strip()
                        
                        # Validate target URL format
                        if not target_url.startswith('http') and not target_url.startswith('/'):
                            # It might be a slug without leading slash, add it
                            target_url = '/' + target_url.lstrip('/')
                        
                        print(f"Creating 301 redirect: {source_url} -> {target_url}")
                        print(f"  Action ID: {action_data.get('id')}")
                        print(f"  Source URL: {source_url}")
                        print(f"  Target URL: {target_url}")

                        redirect_result = wp.create_301_redirect(source_url, target_url)

                        if redirect_result.success:
                            result['success'] = True
                            result['source_url'] = source_url
                            result['target_url'] = target_url
                            result['redirect_path'] = redirect_result.url  # Shows the actual paths used
                            state_mgr.mark_completed(action_data['id'], None)
                            print(f"✓ Redirect created successfully: {redirect_result.url}")
                        else:
                            result['error'] = sanitize_for_json(redirect_result.error)
                            print(f"✗ Redirect failed: {redirect_result.error}")
                            print(f"     Source: {source_url}")
                            print(f"     Target: {target_url}")

                elif action_data['action_type'] == 'delete':
                    # Delete post
                    post = wp.find_post_by_url(action_data['url'])
                    if not post:
                        result['error'] = sanitize_for_json(f"Post not found: {action_data['url']}")
                    else:
                        post_id = post['id']
                        print(f"Deleting post ID {post_id}: {action_data['url']}")

                        delete_result = wp.delete_post(post_id, force=True)

                        if delete_result.success:
                            result['success'] = True
                            result['post_id'] = post_id
                            state_mgr.mark_completed(action_data['id'], post_id)
                            print(f"✓ Post deleted successfully")
                        else:
                            result['error'] = sanitize_for_json(delete_result.error)
                            print(f"✗ Delete failed: {delete_result.error}")

                else:
                    result['error'] = sanitize_for_json(f"Unsupported action type: {action_data['action_type']}")

            except Exception as e:
                result['error'] = sanitize_for_json(str(e))

            results.append(result)

        # Get updated stats
        stats = state_mgr.get_stats()

        return jsonify({
            "status": "batch_complete",
            "total_requested": len(action_ids),
            "total_executed": len(results),
            "results": results,
            "stats": stats
        })

    except Exception as e:
        import traceback
        return jsonify({
            "error": "Execution failed",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/api/quick-create", methods=["POST"])
def quick_create_post():
    """
    Quick create a single post without action plan (ad-hoc content creation).

    JSON body: {
        site_name: string,
        title: string,
        keywords: string[] (comma-separated or array)
    }

    Returns: Creation result with post_id or error
    """
    print("=== /api/quick-create called ===")

    try:
        data = request.get_json()
        site_name = data.get('site_name')
        title = data.get('title')
        keywords = data.get('keywords', [])

        # Parse keywords if string
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]

        if not site_name or not title:
            return jsonify({"error": "site_name and title required"}), 400

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400

        from config import get_site
        from wordpress.publisher import WordPressPublisher
        from content.generators.claude_generator import ClaudeContentGenerator
        from affiliate.manager import AffiliateLinkManager

        # Get site config (includes niche context)
        site_config = get_site(site_name)

        # Initialize services
        wp = WordPressPublisher(
            site_config['url'],
            site_config['wp_username'],
            site_config['wp_app_password'],
            rate_limit_delay=1.0
        )
        content_gen = ClaudeContentGenerator(anthropic_key)

        # Get affiliate manager if available
        try:
            affiliate_mgr = AffiliateLinkManager(site_name)
            if not affiliate_mgr.get_all_links():
                affiliate_mgr = None
        except Exception as e:
            print(f"   ⚠ Could not initialize affiliate link manager: {e}")
            affiliate_mgr = None

        result = {
            "title": title,
            "success": False,
            "error": None
        }

        try:
            # DUPLICATE DETECTION: Check if post with this title already exists
            print(f"Checking for duplicate post with title: {title}")
            existing_posts = wp.get_all_posts()
            for post in existing_posts:
                post_title = post.get('title', {}).get('rendered', '') if isinstance(post.get('title'), dict) else post.get('title', '')
                if post_title.strip().lower() == title.strip().lower():
                    print(f"DUPLICATE DETECTED: Post with title '{title}' already exists (ID: {post.get('id')})")
                    result['success'] = True
                    result['post_id'] = post.get('id')
                    result['skipped'] = True
                    result['reason'] = 'Duplicate post already exists'
                    return jsonify(result)

            # Create new post
            print(f"Creating post: {title}")
            research = content_gen.research_topic(title, keywords)
            internal_links = wp.get_internal_link_suggestions(keywords)
            affiliate_links = affiliate_mgr.get_all_links() if affiliate_mgr else []

            article_data = content_gen.generate_article(
                topic_title=title,
                keywords=keywords,
                research=research,
                meta_description=f"Learn about {title}",
                internal_links=internal_links,
                affiliate_links=affiliate_links
            )

            # Generate images if requested
            generate_images = data.get('generate_images', False)
            if generate_images:
                try:
                    from content.generators.gemini_images import GeminiImageGenerator
                    gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                    if gemini_key:
                        print(f"  🖼️  Image generation enabled - processing image placeholders...")
                        image_gen = GeminiImageGenerator(gemini_key)
                        updated_content, image_info = image_gen.replace_placeholders_with_images(
                            content=article_data['content'],
                            article_title=article_data.get('title', title),
                            keywords=keywords,
                            wp_publisher=wp,
                            upload_to_wordpress=True
                        )
                        article_data['content'] = updated_content
                        if image_info:
                            print(f"  ✅ Generated and uploaded {len(image_info)} images")
                    else:
                        print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                except Exception as e:
                    print(f"  ⚠️  Image generation failed: {e}")
                    import traceback
                    traceback.print_exc()

            publish_result = wp.create_post(
                title=article_data.get('title', title),
                content=article_data['content'],
                meta_title=article_data.get('meta_title'),
                meta_description=article_data.get('meta_description'),
                categories=article_data.get('categories', []),
                tags=article_data.get('tags', [])
            )

            if publish_result.success:
                result['post_id'] = publish_result.post_id
                result['success'] = True
                result['url'] = f"{site_config['url']}/?p={publish_result.post_id}"

                # Update affiliate link usage
                if affiliate_mgr and affiliate_links:
                    for link in affiliate_links:
                        if link['url'] in article_data['content']:
                            affiliate_mgr.increment_usage(link['id'])

                print(f"Post created successfully: {result['post_id']}")
            else:
                result['error'] = sanitize_for_json(publish_result.error)
                print(f"Post creation failed: {publish_result.error}")

        except Exception as e:
            result['error'] = str(e)
            print(f"Error creating post: {e}")

        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({
            "error": "Quick create failed",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/api/quick-update", methods=["POST"])
def quick_update_post():
    """
    Quick update an existing post/page by URL without action plan (ad-hoc content update).
    
    JSON body: {
        site_name: string,
        url: string (full URL of post/page to update),
        keywords: string[] (optional, comma-separated or array),
        generate_images: bool (optional, default False)
    }
    
    Returns: Update result with post_id or error
    """
    print("=== /api/quick-update called ===")
    
    try:
        data = request.get_json()
        site_name = data.get('site_name')
        url = data.get('url')
        keywords = data.get('keywords', [])
        generate_images = data.get('generate_images', False)
        
        # Parse keywords if string
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        
        if not site_name or not url:
            return jsonify({"error": "site_name and url required"}), 400
        
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400
        
        from config import get_site
        from wordpress.publisher import WordPressPublisher
        from content.generators.claude_generator import ClaudeContentGenerator
        from affiliate.manager import AffiliateLinkManager
        from page_type_detector import PageTypeDetector
        
        # Get site config
        site_config = get_site(site_name)
        
        # Initialize services
        wp = WordPressPublisher(
            site_config['url'],
            site_config['wp_username'],
            site_config['wp_app_password'],
            rate_limit_delay=1.0
        )
        content_gen = ClaudeContentGenerator(anthropic_key)
        
        # Detect page type
        page_type = PageTypeDetector.detect_page_type(url)
        update_strategy = PageTypeDetector.get_update_strategy(page_type)
        
        result = {
            "success": False,
            "url": url,
            "page_type": page_type.value,
            "update_strategy": update_strategy.value
        }
        
        # Find the post/page
        found_item = wp.find_post_or_page_by_url(url)
        if not found_item:
            result['error'] = sanitize_for_json(f"Post or page not found: {url}")
            return jsonify(result), 404
        
        item_id = found_item['id']
        item_type = found_item.get('_wp_type', 'post')
        existing_title = found_item.get('title', {}).get('rendered', '') if isinstance(found_item.get('title'), dict) else found_item.get('title', '')
        existing_content = found_item.get('content', {}).get('rendered', '') if isinstance(found_item.get('content'), dict) else found_item.get('content', '')
        
        # Handle different page types
        if page_type.value == 'homepage' or (item_type == 'page' and update_strategy.value == 'meta_only'):
            # Homepage or WordPress page - only update meta, not content
            result['error'] = sanitize_for_json(f"This URL is a {page_type.value}. Only SEO meta data can be updated, not content. Use the action plan for meta-only updates.")
            return jsonify(result), 400
        
        elif update_strategy.value == 'skip':
            result['error'] = sanitize_for_json(f"This URL type ({page_type.value}) cannot be updated.")
            return jsonify(result), 400
        
        else:
            # Regular post/page - full content update
            title = existing_title  # Use existing title unless provided
            if not keywords:
                # Try to extract keywords from existing content or use default
                keywords = [title.split()[0]] if title else []
            
            # Research and generate updated content
            research = content_gen.research_topic(title, keywords)
            
            # Get affiliate manager if available
            affiliate_mgr = None
            try:
                affiliate_mgr = AffiliateLinkManager(site_name)
            except Exception as e:
                print(f"  ⚠️  Affiliate manager not available: {e}")
            
            internal_links = wp.get_internal_link_suggestions(keywords)
            affiliate_links = affiliate_mgr.get_all_links() if affiliate_mgr else []
            
            article_data = content_gen.generate_article(
                topic_title=title,
                keywords=keywords,
                research=research,
                meta_description=f"Updated: {title}",
                existing_content=existing_content,
                internal_links=internal_links,
                affiliate_links=affiliate_links
            )
            
            # Generate images if requested
            if generate_images:
                try:
                    from content.generators.gemini_images import GeminiImageGenerator
                    gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                    if gemini_key:
                        print(f"  🖼️  Image generation enabled - processing image placeholders...")
                        image_gen = GeminiImageGenerator(gemini_key)
                        updated_content, image_info = image_gen.replace_placeholders_with_images(
                            content=article_data['content'],
                            article_title=article_data.get('title', title),
                            keywords=keywords,
                            wp_publisher=wp,
                            upload_to_wordpress=True
                        )
                        article_data['content'] = updated_content
                        if image_info:
                            print(f"  ✅ Generated and uploaded {len(image_info)} images")
                    else:
                        print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                except Exception as e:
                    print(f"  ⚠️  Image generation failed: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue without images if generation fails
            
            # Update the post/page
            publish_result = wp.update_post(
                item_id,
                title=article_data.get('title', title),
                content=article_data['content'],
                meta_title=article_data.get('meta_title'),
                meta_description=article_data.get('meta_description'),
                categories=article_data.get('categories', []),
                tags=article_data.get('tags', []),
                item_type=item_type  # Use correct endpoint based on item type
            )
            
            if publish_result.success:
                result['post_id'] = item_id
                result['success'] = True
                result['url'] = url
                
                # Update affiliate link usage
                if affiliate_mgr and affiliate_links:
                    for link in affiliate_links:
                        if link['url'] in article_data['content']:
                            affiliate_mgr.increment_usage(link['id'])
                
                print(f"Post updated successfully: {item_id}")
            else:
                result['error'] = sanitize_for_json(publish_result.error)
                print(f"Post update failed: {publish_result.error}")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": "Quick update failed",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/api/execute-next", methods=["POST"])
def execute_next_action():
    """
    Execute the next pending action for a site (timeout-safe, processes 1 action only).
    Designed for Vercel serverless - stays within timeout limits.

    JSON body: {site_name}
    Returns: Action result + remaining count
    """
    print("=== /api/execute-next called ===")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")

    try:
        data = request.get_json()
        print(f"Request JSON data: {data}")
    except Exception as json_error:
        print(f"Error parsing JSON: {json_error}")
        return jsonify({"error": "Invalid JSON", "details": str(json_error)}), 400

    site_name = data.get('site_name') if data else None
    print(f"Site name: {site_name}")
    generate_images = data.get('generate_images', False) if data else False  # Image generation flag

    if not site_name:
        return jsonify({"error": "site_name required"}), 400

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400

    try:
        from config import get_site
        from core.state_manager import StateManager
        from wordpress.publisher import WordPressPublisher
        from content.generators.claude_generator import ClaudeContentGenerator
        from affiliate.manager import AffiliateLinkManager

        # Get site config
        print(f"Getting config for site: {site_name}")
        site_config = get_site(site_name)
        print(f"Site config: {site_config}")

        print(f"Initializing StateManager for: {site_name}")
        try:
            state_mgr = StateManager(site_name)
            print(f"StateManager initialized successfully")
        except Exception as sm_error:
            print(f"ERROR initializing StateManager: {sm_error}")
            import traceback
            print(f"StateManager traceback: {traceback.format_exc()}")
            raise

        # Get next pending action
        print(f"Getting pending actions...")
        try:
            pending = state_mgr.get_pending_actions(limit=1)
            print(f"Found {len(pending)} pending action(s)")
        except Exception as pend_error:
            print(f"ERROR getting pending actions: {pend_error}")
            raise

        print(f"Getting stats...")
        try:
            stats = state_mgr.get_stats()
            print(f"Stats: {stats}")
        except Exception as stats_error:
            print(f"ERROR getting stats: {stats_error}")
            raise
        
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

        # Ensure action has an ID (generate one if missing)
        if 'id' not in action_data:
            import hashlib
            # Generate a unique ID based on action content
            id_string = f"{action_data.get('action_type', '')}_{action_data.get('url', '')}_{action_data.get('title', '')}"
            action_id = hashlib.md5(id_string.encode()).hexdigest()[:12]
            action_data['id'] = action_id
            print(f"Generated ID for action: {action_id}")

            # CRITICAL: Update the action in state to persist the ID
            if 'current_plan' in state_mgr.state:
                for idx, act in enumerate(state_mgr.state['current_plan']):
                    if (act.get('action_type') == action_data.get('action_type') and
                        act.get('url') == action_data.get('url') and
                        act.get('title') == action_data.get('title')):
                        state_mgr.state['current_plan'][idx]['id'] = action_id
                        break
                state_mgr.save()
            print(f"Persisted ID to state for action: {action_id}")

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
        except Exception as e:
            print(f"   ⚠ Could not initialize affiliate link manager: {e}")

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

                # DUPLICATE DETECTION: Check if post with this title already exists
                print(f"Checking for duplicate post with title: {title}")
                try:
                    existing_posts = wp.get_all_posts()
                    for post in existing_posts:
                        post_title = post.get('title', {}).get('rendered', '') if isinstance(post.get('title'), dict) else post.get('title', '')
                        if post_title.strip().lower() == title.strip().lower():
                            print(f"DUPLICATE DETECTED: Post with title '{title}' already exists (ID: {post.get('id')})")
                            result['success'] = True
                            result['post_id'] = post.get('id')
                            result['skipped'] = True
                            result['reason'] = 'Duplicate post already exists'
                            state_mgr.mark_completed(action_data['id'], post.get('id'))
                            # Skip creation and move to next action
                            raise Exception("SKIP_DUPLICATE")
                except Exception as e:
                    if str(e) == "SKIP_DUPLICATE":
                        raise  # Re-raise to skip creation
                    print(f"Warning: Could not check for duplicates: {e}")
                    # Continue with creation if duplicate check fails

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
                    internal_links=internal_links,
                    affiliate_links=affiliate_links
                )

                # Generate images if requested
                if generate_images:
                    try:
                        from content.generators.gemini_images import GeminiImageGenerator
                        gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                        if gemini_key:
                            print(f"  🖼️  Image generation enabled - processing image placeholders...")
                            image_gen = GeminiImageGenerator(gemini_key)
                            updated_content, image_info = image_gen.replace_placeholders_with_images(
                                content=article_data['content'],
                                article_title=article_data.get('title', title),
                                keywords=keywords,
                                wp_publisher=wp,
                                upload_to_wordpress=True
                            )
                            article_data['content'] = updated_content
                            if image_info:
                                print(f"  ✅ Generated and uploaded {len(image_info)} images")
                        else:
                            print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                    except Exception as e:
                        print(f"  ⚠️  Image generation failed: {e}")
                        import traceback
                        traceback.print_exc()

                # Create the post
                publish_result = wp.create_post(
                    title=article_data.get('title', title),
                    content=article_data['content'],
                    meta_title=article_data.get('meta_title'),
                    meta_description=article_data.get('meta_description'),
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
                    result['error'] = sanitize_for_json(publish_result.error)
                    result['success'] = False

            elif action_data['action_type'] == 'update':
                # SMART UPDATE: Detect page type and route appropriately
                from page_type_detector import PageTypeDetector, PageType, UpdateStrategy

                url = action_data['url']
                page_info = PageTypeDetector.get_update_info(url)

                print(f"  📄 Page Type Detection:")
                print(f"     URL: {url}")
                print(f"     Type: {page_info['page_type']}")
                print(f"     Strategy: {page_info['strategy']}")
                print(f"     {page_info['explanation']}")

                if page_info['should_skip']:
                    # Skip this page type (date archives, search, etc.)
                    result['success'] = True
                    result['skipped'] = True
                    result['reason'] = page_info['explanation']
                    state_mgr.mark_completed(action_data['id'], None)
                    print(f"  ⏭️  Skipping: {page_info['explanation']}")

                elif page_info['strategy'] == UpdateStrategy.META_ONLY.value:
                    # META_ONLY update - Categories, Tags, or HOMEPAGE
                    print(f"  🏷️  Meta-only update for {page_info['page_type']}")

                    if page_info['page_type'] == PageType.HOMEPAGE.value:
                        # HOMEPAGE: Only update SEO meta, NEVER content
                        print(f"  🏠 Homepage detected - updating SEO meta only (content will NOT be modified)")
                        
                        # Find homepage (could be a page or post set as homepage)
                        homepage_post = None
                        
                        # Try to find by checking if it's a page with slug matching homepage
                        # WordPress homepage could be:
                        # 1. A static page set as homepage
                        # 2. The blog index (posts page)
                        # 3. A custom page template
                        
                        # First, try to find any page/post that matches the homepage URL
                        try:
                            # Check pages endpoint
                            pages_response = requests.get(
                                f"{wp.api_base}/pages",
                                auth=wp.auth,
                                params={'per_page': 100},
                                timeout=30
                            )
                            if pages_response.status_code == 200:
                                pages = pages_response.json()
                                # Look for page that might be homepage
                                # Homepage is often the first page or has a specific slug
                                for page in pages:
                                    page_link = page.get('link', '').rstrip('/')
                                    site_url = site_config['url'].rstrip('/')
                                    if page_link == site_url or page_link == f"{site_url}/":
                                        homepage_post = page
                                        break
                        except Exception as e:
                            print(f"  ⚠️  Could not fetch pages: {e}")
                        
                        # If not found in pages, try finding the front page
                        if not homepage_post:
                            try:
                                # WordPress might have a setting for homepage
                                # Try to get the front page option via REST API
                                # Or search posts if blog is homepage
                                posts = wp.get_all_posts()
                                # Blog homepage doesn't have a specific post, but we can update site meta
                                # For now, if we can't find a specific page, we'll skip
                                print(f"  ⚠️  Could not find specific homepage page/post")
                            except Exception as e:
                                print(f"  ⚠️  Error finding homepage: {e}")
                        
                        if homepage_post:
                            homepage_id = homepage_post['id']
                            keywords = action_data.get('keywords', [])
                            title = action_data.get('title', '') or homepage_post.get('title', {}).get('rendered', '')
                            
                            # Generate SEO meta based on reasoning/keywords
                            # Don't generate article content - just meta
                            meta_title = title if title else f"{site_name} | Wild Cat Conservation & Species Guide 2025"
                            meta_description = action_data.get('reasoning', '')
                            if keywords:
                                meta_description = f"Explore {', '.join(keywords[:3])} and more wild cat conservation content. {meta_description[:100]}"
                            else:
                                meta_description = meta_description[:155] if meta_description else f"Learn about wild cat conservation, species identification guides, and 2025 conservation trends."
                            
                            # Update ONLY meta fields, NOT content
                            publish_result = wp.update_post(
                                homepage_id,
                                title=None,  # Don't update title
                                content=None,  # NEVER update homepage content
                                meta_title=meta_title,
                                meta_description=meta_description,
                                item_type='page'  # Homepage is typically a page
                            )
                            
                            if publish_result.success:
                                result['post_id'] = homepage_id
                                result['success'] = True
                                result['meta_only'] = True
                                result['homepage'] = True
                                state_mgr.mark_completed(action_data['id'], homepage_id)
                                print(f"  ✅ Homepage SEO meta updated successfully (content preserved)")
                            else:
                                result['error'] = sanitize_for_json(publish_result.error)
                                result['success'] = False
                        else:
                            # Couldn't find homepage page/post - skip with warning
                            result['success'] = True
                            result['skipped'] = True
                            result['reason'] = 'Homepage not found as editable page/post - skipping for safety'
                            state_mgr.mark_completed(action_data['id'], None)
                            print(f"  ⚠️  Skipping homepage update - could not find editable homepage page/post")

                    elif page_info['page_type'] == PageType.AUTHOR.value:
                        # AUTHOR archive - Update SEO meta only
                        print(f"  👤 Author archive detected - updating SEO meta only")
                        
                        # Extract author slug from URL
                        import re
                        match = re.search(r'/author/([^/]+)', url)
                        if not match:
                            raise Exception(f"Invalid author URL: {url}")
                        
                        author_slug = match.group(1)
                        
                        # WordPress doesn't have a direct REST API for author meta
                        # This would require a custom endpoint or plugin
                        # For now, skip with explanation
                        result['success'] = True
                        result['skipped'] = True
                        result['reason'] = 'Author archives require custom WordPress setup for SEO meta updates'
                        state_mgr.mark_completed(action_data['id'], None)
                        print(f"  ⚠️  Author archive SEO updates require custom WordPress configuration")

                    elif page_info['page_type'] == PageType.CATEGORY.value:
                        category = wp.find_category_by_url(url)
                        if not category:
                            raise Exception(f"Category not found: {url}")

                        category_id = category['id']
                        current_name = category.get('name', '')
                        keywords = action_data.get('keywords', [])

                        # Generate optimized SEO meta (not full content)
                        meta_title = f"{current_name} | {site_name}" if keywords else current_name
                        meta_description = f"Explore our comprehensive {current_name.lower()} content. {' '.join(keywords[:3])}"

                        publish_result = wp.update_category_meta(
                            category_id,
                            meta_title=meta_title,
                            meta_description=meta_description
                        )

                    elif page_info['page_type'] == PageType.TAG.value:
                        tag = wp.find_tag_by_url(url)
                        if not tag:
                            raise Exception(f"Tag not found: {url}")

                        tag_id = tag['id']
                        current_name = tag.get('name', '')
                        keywords = action_data.get('keywords', [])

                        # Generate optimized SEO meta (not full content)
                        meta_title = f"{current_name} Articles | {site_name}"
                        meta_description = f"Browse all articles tagged with {current_name.lower()}. {' '.join(keywords[:3])}"

                        publish_result = wp.update_tag_meta(
                            tag_id,
                            meta_title=meta_title,
                            meta_description=meta_description
                        )

                    # Handle result
                    if publish_result.success:
                        result['post_id'] = publish_result.post_id
                        result['success'] = True
                        result['meta_only'] = True
                        state_mgr.mark_completed(action_data['id'], publish_result.post_id)
                        print(f"  ✅ Meta updated successfully")
                    else:
                        result['error'] = sanitize_for_json(publish_result.error)
                        result['success'] = False

                else:
                    # FULL CONTENT UPDATE - For posts and pages
                    print(f"  📝 Full content update for post/page")
                    
                    # Find post or page - check both endpoints
                    found_item = wp.find_post_or_page_by_url(url)
                    if not found_item:
                        raise Exception(f"Post or page not found: {url}")
                    
                    item_type = found_item.get('_wp_type', 'post')
                    item_id = found_item['id']
                    
                    # CRITICAL SAFETY CHECK: If it's a WordPress PAGE (not POST), 
                    # only update SEO meta, NOT content (to avoid breaking static pages)
                    if item_type == 'page':
                        print(f"  ⚠️  WordPress PAGE detected - switching to meta-only update for safety")
                        print(f"     WordPress pages (like /about/, /contact/) should only have SEO meta updated, not content")
                        
                        keywords = action_data.get('keywords', [])
                        title = action_data.get('title', '') or found_item.get('title', {}).get('rendered', '')
                        
                        # Generate SEO meta only
                        meta_title = title if title else found_item.get('title', {}).get('rendered', '')
                        meta_description = action_data.get('reasoning', '')
                        if keywords:
                            meta_description = f"{', '.join(keywords[:3])}. {meta_description[:100]}" if meta_description else f"Learn about {', '.join(keywords[:3])}"
                        else:
                            meta_description = meta_description[:155] if meta_description else "Learn more about our content."
                        
                        # Update ONLY meta fields, NOT content or title
                        publish_result = wp.update_post(
                            item_id,
                            title=None,  # Don't update title
                            content=None,  # NEVER update page content
                            meta_title=meta_title,
                            meta_description=meta_description,
                            item_type='page'  # Use pages endpoint for WordPress pages
                        )
                        
                        if publish_result.success:
                            result['post_id'] = item_id
                            result['success'] = True
                            result['meta_only'] = True
                            result['wp_page'] = True
                            state_mgr.mark_completed(action_data['id'], item_id)
                            print(f"  ✅ WordPress page SEO meta updated successfully (content preserved)")
                        else:
                            result['error'] = sanitize_for_json(publish_result.error)
                            result['success'] = False
                        # WordPress page handled - no need to generate article content
                    
                    else:
                        # It's a POST - safe to do full content update
                        existing_content = found_item.get('content', {}).get('rendered', '')
                        title = action_data.get('title', '') or found_item.get('title', {}).get('rendered', '')
                        keywords = action_data.get('keywords', [])

                        # Generate improved content using generate_article with existing_content
                        # First do research
                        research = content_gen.research_topic(title, keywords)

                        # Get internal link suggestions
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
                            internal_links=internal_links,
                            affiliate_links=affiliate_links
                        )

                        # Generate images if requested
                        if generate_images:
                            try:
                                from content.generators.gemini_images import GeminiImageGenerator
                                gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                                if gemini_key:
                                    print(f"  🖼️  Image generation enabled - processing image placeholders...")
                                    image_gen = GeminiImageGenerator(gemini_key)
                                    updated_content, image_info = image_gen.replace_placeholders_with_images(
                                        content=article_data['content'],
                                        article_title=article_data.get('title', title),
                                        keywords=keywords,
                                        wp_publisher=wp,
                                        upload_to_wordpress=True
                                    )
                                    article_data['content'] = updated_content
                                    if image_info:
                                        print(f"  ✅ Generated and uploaded {len(image_info)} images")
                                else:
                                    print(f"  ⚠️  Image generation requested but GOOGLE_GEMINI_API_KEY not configured")
                            except Exception as e:
                                print(f"  ⚠️  Image generation failed: {e}")
                                import traceback
                                traceback.print_exc()
                                # Continue without images if generation fails

                        # Update the post with new content
                        publish_result = wp.update_post(
                            item_id,
                            title=article_data.get('title', title),
                            content=article_data['content'],
                            meta_title=article_data.get('meta_title'),
                            meta_description=article_data.get('meta_description'),
                            categories=article_data.get('categories', []),
                            tags=article_data.get('tags', []),
                            item_type='post'  # Explicitly use posts endpoint
                        )

                        # Update affiliate link usage if any were added
                        if affiliate_mgr and affiliate_links:
                            # Count how many affiliate links appear in the new content
                            for link in affiliate_links:
                                if link['url'] in article_data['content']:
                                    affiliate_mgr.increment_usage(link['id'])

                        # Handle result
                        if publish_result.success:
                            result['post_id'] = item_id
                            result['success'] = True
                            state_mgr.mark_completed(action_data['id'], item_id)
                            print(f"  ✅ Content updated successfully")
                        else:
                            result['error'] = sanitize_for_json(publish_result.error)
                            result['success'] = False

            else:
                result['error'] = sanitize_for_json(f"Unsupported action type: {action_data['action_type']}")

        except Exception as e:
            if str(e) == "SKIP_DUPLICATE":
                # Duplicate detected and skipped - this is not an error
                pass
            else:
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in execute-next: {str(e)}")
        print(f"Traceback: {error_trace}")
        return jsonify({
            "error": "Execution failed",
            "details": str(e),
            "trace": error_trace
        }), 500


@app.route("/api/sites", methods=["GET"])
def list_sites_endpoint():
    """
    List all configured sites with their current status.
    Returns site names and pending action counts.
    """
    import traceback
    
    # Ultra-defensive error handling - always return valid JSON
    try:
        # Try to import modules
        try:
            from config import list_sites
        except Exception as import_error:
            print(f"❌ ERROR importing config: {import_error}")
            return jsonify({
                "sites": [],
                "total_sites": 0,
                "error": "Failed to import config module",
                "details": str(import_error)
            }), 200

        try:
            from core.state_manager import StateManager
        except Exception as import_error:
            print(f"❌ ERROR importing state_manager: {import_error}")
            # Still return sites, just without stats
            try:
                sites = list_sites()
                return jsonify({
                    "sites": [{"name": site, "pending_actions": 0, "completed_actions": 0, "total_actions": 0} for site in sites],
                    "total_sites": len(sites) if sites else 0,
                    "warning": "State manager unavailable - stats not loaded"
                }), 200
            except:
                return jsonify({
                    "sites": [],
                    "total_sites": 0,
                    "error": "Failed to load sites"
                }), 200

        # Get list of sites
        try:
            sites = list_sites()
        except Exception as config_error:
            print(f"❌ ERROR loading sites config: {config_error}")
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                "sites": [],
                "total_sites": 0,
                "error": "Failed to load site configuration",
                "details": str(config_error)
            }), 200
        
        if not sites or len(sites) == 0:
            return jsonify({
                "sites": [],
                "total_sites": 0
            })

        site_status = []

        # Import get_site to get site URLs
        try:
            from config import get_site
        except:
            get_site = None
        
        for site_name in sites:
            try:
                state_mgr = StateManager(site_name)
                stats = state_mgr.get_stats()
                
                # Get site URL if available
                site_url = None
                if get_site:
                    try:
                        site_config = get_site(site_name)
                        site_url = site_config.get('url')
                    except:
                        pass
                
                site_status.append({
                    'name': site_name,
                    'url': site_url,
                    'pending_actions': stats.get('pending', 0) if stats else 0,
                    'completed_actions': stats.get('completed', 0) if stats else 0,
                    'total_actions': stats.get('total_actions', 0) if stats else 0
                })
            except Exception as site_error:
                # If state loading fails for a site, still include it with zero stats
                print(f"  ⚠️  Error loading state for {site_name}: {site_error}")
                
                # Try to get URL even if state fails
                site_url = None
                if get_site:
                    try:
                        site_config = get_site(site_name)
                        site_url = site_config.get('url')
                    except:
                        pass
                
                site_status.append({
                    'name': site_name,
                    'url': site_url,
                    'pending_actions': 0,
                    'completed_actions': 0,
                    'total_actions': 0
                })

        return jsonify({
            "sites": site_status,
            "total_sites": len(sites)
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ CRITICAL ERROR in /api/sites: {e}")
        print(f"Traceback: {error_trace}")
        # Return 200 with empty sites instead of 500 to prevent frontend crash
        return jsonify({
            "sites": [],
            "total_sites": 0,
            "error": "Failed to load sites",
            "details": str(e)
        }), 200  # Changed to 200 so frontend can handle gracefully


@app.route("/api/niche/<site_name>", methods=["GET"])
def get_niche_research(site_name):
    """
    Get cached niche research for a site.
    Returns 404 if no cached research available.
    """
    try:
        from core.state_manager import StateManager
        
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
    Returns ALL actions with their full details and status.
    """
    try:
        from core.state_manager import StateManager

        state_mgr = StateManager(site_name)
        
        plan = state_mgr.state.get('current_plan', [])
        stats = state_mgr.get_stats()

        # Sort actions by priority and status
        # Pending first (sorted by priority), then completed
        pending_actions = [a for a in plan if a.get('status') != 'completed']
        completed_actions = [a for a in plan if a.get('status') == 'completed']

        pending_actions.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        completed_actions.sort(key=lambda x: x.get('completed_at', ''), reverse=True)

        all_actions = pending_actions + completed_actions

        response_data = {
            "site": site_name,
            "stats": stats,
            "total_actions": len(plan),
            "actions": all_actions,  # ALL actions with full details
            "pending_count": len(pending_actions),
            "completed_count": len(completed_actions)
        }
        
        return jsonify(response_data)

    except Exception as e:
        from utils.error_handler import handle_api_error
        return handle_api_error(e)


@app.route("/api/plan/<site_name>", methods=["PATCH"])
def update_action_plan(site_name):
    """
    Update action plan - allows editing priorities, reasoning, etc.
    
    Request body:
    {
        "action_id": "action_123",
        "priority_score": 8.5,  # Optional
        "reasoning": "New reasoning",  # Optional
        "action_type": "update",  # Optional
        "keywords": ["keyword1", "keyword2"]  # Optional
    }
    """
    try:
        from core.state_manager import StateManager
        from utils.error_handler import validate_required_fields, handle_api_error, AppError, ErrorCategory
        
        data = request.get_json()
        if not data:
            raise AppError(
                "Request body required",
                category=ErrorCategory.USER_ERROR,
                suggestion="Please provide action update data in JSON format.",
                status_code=400
            )
        
        validate_required_fields(data, ['action_id'])
        
        state_mgr = StateManager(site_name)
        plan = state_mgr.state.get('current_plan', [])
        
        # Find the action to update
        action_to_update = None
        for action in plan:
            if action.get('id') == data['action_id']:
                action_to_update = action
                break
        
        if not action_to_update:
            raise AppError(
                f"Action {data['action_id']} not found",
                category=ErrorCategory.USER_ERROR,
                suggestion="Please check the action ID and try again.",
                status_code=404
            )
        
        # Update fields if provided
        if 'priority_score' in data:
            action_to_update['priority_score'] = float(data['priority_score'])
        
        if 'reasoning' in data:
            action_to_update['reasoning'] = str(data['reasoning'])
        
        if 'action_type' in data:
            action_to_update['action_type'] = data['action_type']
        
        if 'keywords' in data:
            action_to_update['keywords'] = data['keywords']
        
        if 'title' in data:
            action_to_update['title'] = data['title']
        
        # Recalculate stats
        if 'stats' not in state_mgr.state:
            state_mgr.state['stats'] = {'total_actions': 0, 'completed': 0, 'pending': 0}
        state_mgr.state['stats']['total_actions'] = len(plan)
        state_mgr.state['stats']['pending'] = len([a for a in plan if a.get('status') != 'completed'])
        state_mgr.state['stats']['completed'] = len([a for a in plan if a.get('status') == 'completed'])
        
        # Save updated plan
        state_mgr.save()
        
        return jsonify({
            "success": True,
            "message": "Action updated successfully",
            "action": action_to_update,
            "stats": state_mgr.get_stats()
        })
    
    except Exception as e:
        return handle_api_error(e)


@app.route("/api/export/pdf/<site_name>", methods=["GET"])
def export_analysis_pdf(site_name):
    """
    Export the last analysis result as a styled PDF report.
    """
    try:
        from core.state_manager import StateManager
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
            from wordpress.publisher import WordPressPublisher
            
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
            from wordpress.publisher import WordPressPublisher
            
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
        from wordpress.publisher import WordPressPublisher
        
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


@app.route("/api/seo-audit", methods=["POST"])
def seo_audit():
    """
    Run technical SEO audit on a site.
    
    Accepts:
    - site_url: Site to audit (required)
    - max_urls: Optional limit on number of URLs
    - output_format: json, csv, or html (default: json)
    - check_orphaned: Whether to check for orphaned pages (default: false)
    - rate_limit: Seconds between requests (default: 2.0)
    """
    try:
        # Handle both form data and JSON
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        site_url = data.get("site_url")
        if not site_url:
            return jsonify({"error": "site_url is required"}), 400
        
        max_urls = data.get("max_urls")
        if max_urls:
            try:
                max_urls = int(max_urls)
            except (ValueError, TypeError):
                return jsonify({"error": "max_urls must be an integer"}), 400
        
        output_format = data.get("output_format", "json")
        if output_format not in ["json", "csv", "html"]:
            return jsonify({"error": "output_format must be json, csv, or html"}), 400
        
        check_orphaned = False
        if isinstance(data.get("check_orphaned"), bool):
            check_orphaned = data.get("check_orphaned")
        elif isinstance(data.get("check_orphaned"), str):
            check_orphaned = data.get("check_orphaned", "false").lower() == "true"
        
        rate_limit = data.get("rate_limit", 2.0)
        try:
            rate_limit = float(rate_limit)
        except (ValueError, TypeError):
            rate_limit = 2.0
        
        # Run audit
        from seo.technical_auditor import TechnicalSEOAuditor
        from seo.report_generator import SEOReportGenerator
        
        auditor = TechnicalSEOAuditor(
            site_url=site_url,
            rate_limit_delay=rate_limit
        )
        
        audit_results = auditor.audit_site(
            max_urls=max_urls,
            check_orphaned=check_orphaned
        )
        
        # Generate report
        generator = SEOReportGenerator(audit_results)
        
        if output_format == "json":
            report = generator.generate_json()
            return jsonify(json.loads(report))
        elif output_format == "csv":
            report = generator.generate_csv()
            response = app.response_class(
                report,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=seo_audit_{datetime.now().strftime("%Y%m%d")}.csv'}
            )
            return response
        elif output_format == "html":
            report = generator.generate_html()
            response = app.response_class(
                report,
                mimetype='text/html',
                headers={'Content-Disposition': f'attachment; filename=seo_audit_{datetime.now().strftime("%Y%m%d")}.html'}
            )
            return response
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": "Failed to run SEO audit",
            "details": str(e),
            "traceback": traceback.format_exc() if os.getenv("FLASK_DEBUG") else None
        }), 500


if __name__ == "__main__":
    # For local testing
    app.run(debug=True, port=5000)