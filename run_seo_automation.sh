#!/bin/bash
# Wrapper script to run SEO automation with correct Python interpreter

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the SEO automation CLI with the correct Python
exec python3 seo_automation_main.py "$@"

