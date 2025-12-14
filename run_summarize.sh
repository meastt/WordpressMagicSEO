#!/bin/bash
# Wrapper script to summarize SEO audit results

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the summarize script with the correct Python
exec python3 summarize_audit.py "$@"

