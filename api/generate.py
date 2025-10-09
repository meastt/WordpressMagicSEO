"""
Serverless Flask API for Vercel – content generation endpoint
-----------------------------------------------------------

This module defines a single endpoint at the root ("/") that accepts a
multipart/form-data POST request containing a CSV export from Google Search
Console (as "file") and optional form fields:

  - site_url: The WordPress site URL (used for publishing via the REST API)
  - username: WordPress username for authentication
  - application_password: WordPress application password for authentication

It then invokes the multi-site content pipeline defined in
multi_site_content_agent.py.  This pipeline analyses the GSC data, plans
new topics, generates article drafts (using an AI model if available), and
returns a list of Topic objects.  The generated articles are returned as
JSON.

To enable AI generation, install the ``openai`` package and set the
``OPENAI_API_KEY`` environment variable in your Vercel project.  If
``OPENAI_API_KEY`` is absent or the openai module isn't installed, the
pipeline will fall back to a heuristic generator.
"""

import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from multi_site_content_agent import run_pipeline_for_site

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["POST"])
def generate():
    """Handle POST requests to generate content from a GSC CSV export.

    Expects a file field named "file" containing a CSV export.  Optional
    form fields ``site_url``, ``username`` and ``application_password``
    enable publishing via WordPress.  Returns a JSON array of article
    objects (title, primary_keywords, publish_month, meta_title,
    meta_description and body).
    """
    # Validate file upload
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    # Extract optional parameters
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
    credentials = None
    if username and application_password:
        credentials = (username, application_password)
    # Run the pipeline
    topics = run_pipeline_for_site(file_path, site_url, credentials)
    result = []
    for t in topics:
        result.append(
            {
                "title": t.title,
                "primary_keywords": t.primary_keywords,
                "publish_month": t.publish_month,
                "meta_title": t.meta_title,
                "meta_description": t.meta_description,
                "body": t.body,
            }
        )
    return jsonify(result)
