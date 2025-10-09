"""
api/index.py
===========
Serve the simple web interface homepage.
"""

from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def home():
    """Serve the HTML interface."""
    index_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    return send_file(index_path)

if __name__ == "__main__":
    app.run(debug=True)