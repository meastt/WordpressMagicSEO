# Quick Setup Guide

## First Time Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "import requests; print('✅ All dependencies installed!')"
```

## Running Commands

**Option 1: Use wrapper scripts (Easiest - Recommended)**
```bash
./run_audit.sh https://yoursite.com --max-urls 50 --output json
./run_seo_automation.sh gsc_export.csv https://yoursite.com ...
```
*These scripts automatically activate venv and use the correct Python*

**Option 2: Use venv Python directly**
```bash
./venv/bin/python seo_audit_cli.py https://yoursite.com
./venv/bin/python seo_automation_main.py gsc_export.csv ...
```

**Option 3: Activate venv and use python3**
```bash
source venv/bin/activate
python3 seo_audit_cli.py https://yoursite.com
python3 seo_automation_main.py gsc_export.csv ...
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'requests'"**
- **Best fix:** Use the wrapper scripts: `./run_audit.sh` or `./run_seo_automation.sh`
- Or use: `./venv/bin/python` instead of `python`
- Or activate venv and use `python3`: `source venv/bin/activate && python3 ...`

**"python: command not found"**
- Use `python3` instead of `python`
- Or use the wrapper scripts (they handle this automatically)

**"python command uses wrong Python even after venv activation"**
- Your shell has a `python` alias that overrides venv
- **Solution:** Use wrapper scripts (`./run_audit.sh`) or `python3` explicitly
- The wrapper scripts always use the correct venv Python

**Virtual environment already exists?**
- Just use the wrapper scripts - they activate it automatically
- Or manually: `source venv/bin/activate`
- No need to recreate unless you want a fresh install

