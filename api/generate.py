# api/generate.py
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from multi_site_content_agent import run_pipeline_for_site

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["POST"])
def handle():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    site_url = request.form.get("site_url")
    username = request.form.get("username")
    application_password = request.form.get("application_password")
    credentials = None
    if username and application_password:
        credentials = (username, application_password)
    topics = run_pipeline_for_site(file_path, site_url, credentials)
    result = []
    for t in topics:
        result.append({
            "title": t.title,
            "primary_keywords": t.primary_keywords,
            "publish_month": t.publish_month,
            "meta_title": t.meta_title,
            "meta_description": t.meta_description,
            "body": t.body,
        })
    return jsonify(result)
