# Architecture Explained

## What This Application Is

**This is NOT a WordPress plugin.** It's a **standalone web service** that connects to WordPress via the REST API.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (Frontend)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  index.html (Static HTML/JS)                         │   │
│  │  - Uploads GSC CSV files                             │   │
│  │  - Calls API endpoints                               │   │
│  │  - Displays results                                  │   │
│  └───────────────────┬──────────────────────────────────┘   │
└───────────────────────┼───────────────────────────────────────┘
                        │ HTTP/HTTPS (CORS)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Vercel Serverless (Backend API)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  api/generate.py (Flask API)                         │   │
│  │  - Receives file uploads                             │   │
│  │  - Processes GSC data                                │   │
│  │  - Generates AI content                              │   │
│  │  - Returns JSON responses                            │   │
│  └───────────────────┬──────────────────────────────────┘   │
└───────────────────────┼───────────────────────────────────────┘
                        │ WordPress REST API
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              WordPress Site (Target)                         │
│  - Creates/updates/deletes posts                            │
│  - Uses Application Password for auth                        │
└─────────────────────────────────────────────────────────────┘
```

## Three Ways to Use It

### 1. **CLI (Command Line)** - Local Python Script
```bash
python seo_automation_main.py gsc_export.csv https://yoursite.com ...
```
- Runs entirely on your local machine
- No CORS issues (no browser involved)
- No web server needed
- Best for: Automation, scripts, scheduled tasks

### 2. **Web API** - Deployed on Vercel
```bash
curl -X POST https://your-api.vercel.app/api/analyze ...
```
- Serverless Flask API
- Can be called from anywhere
- CORS enabled for browser access
- Best for: Integration with other tools, API access

### 3. **Web UI** - Browser Interface
- Visit: `https://your-api.vercel.app/`
- Upload files via browser
- Interactive dashboard
- CORS configured for browser access
- Best for: Manual use, visual interface

## CORS Configuration

### Current Setup ✅

**File:** `api/generate.py` (line 48)
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ← This enables CORS for ALL origins
```

**What this means:**
- ✅ Allows requests from **any domain** (browser, localhost, etc.)
- ✅ Handles preflight OPTIONS requests automatically
- ✅ Works for browser-based testing
- ⚠️  **Security Note:** Currently allows all origins (fine for personal use, but consider restricting for production)

### How CORS Works Here

1. **Browser makes request** from `index.html` → `https://your-api.vercel.app/api/analyze`
2. **Browser sends CORS headers** automatically
3. **Flask-CORS middleware** adds response headers:
   ```
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Methods: GET, POST, OPTIONS
   Access-Control-Allow-Headers: Content-Type
   ```
4. **Browser allows the response** because CORS headers are present

## Testing Scenarios

### ✅ Scenario 1: Browser Testing (Should Work)
```
Browser → https://your-api.vercel.app/ → API → WordPress
```
- **CORS:** ✅ Configured
- **Works:** Yes, if deployed on Vercel

### ✅ Scenario 2: Local Development
```
Browser (localhost:5000) → Flask (localhost:5000) → WordPress
```
- **CORS:** ✅ Configured
- **Works:** Yes, Flask-CORS handles it

### ✅ Scenario 3: CLI Usage
```
Terminal → Python script → WordPress
```
- **CORS:** ❌ Not needed (no browser)
- **Works:** Yes, direct execution

### ⚠️  Scenario 4: Cross-Origin Issues (If Any)

If you encounter CORS errors, they might be from:

1. **WordPress REST API CORS** (not your API)
   - WordPress may block requests from your API
   - Solution: Install CORS plugin on WordPress OR use server-side requests (which you already do)

2. **File Upload CORS**
   - Large file uploads might have issues
   - Solution: Already handled by Flask-CORS

3. **Preflight Requests**
   - Browser sends OPTIONS request first
   - Solution: Flask-CORS handles this automatically

## Current CORS Status

### ✅ What's Working
- Flask-CORS installed (`flask-cors>=4.0.0` in requirements.txt)
- CORS enabled globally (`CORS(app)`)
- Should work for browser-based testing

### 🔧 If You Have CORS Issues

**Option 1: More Restrictive CORS (Recommended for Production)**
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://your-domain.com", "http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

**Option 2: Allow Specific Origins**
```python
CORS(app, origins=["https://your-domain.com", "http://localhost:5000"])
```

**Option 3: Debug CORS Issues**
```python
CORS(app, supports_credentials=True, expose_headers=["Content-Range"])
```

## Testing CORS

### Test 1: Browser Console
```javascript
fetch('https://your-api.vercel.app/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

### Test 2: Check Headers
```bash
curl -I -X OPTIONS https://your-api.vercel.app/api/analyze \
  -H "Origin: https://your-domain.com" \
  -H "Access-Control-Request-Method: POST"
```

Should return:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
```

## Summary

### ✅ CORS is Already Configured
- Flask-CORS is installed and enabled
- Should work for browser-based testing
- Currently allows all origins (fine for personal use)

### 🎯 Architecture
- **NOT a WordPress plugin** - it's a standalone service
- **Web API** deployed on Vercel
- **Web UI** for browser access
- **CLI** for local/automated use

### 🔒 Security Note
For production, consider restricting CORS to specific origins instead of allowing all (`*`).

---

**Bottom Line:** CORS is already set up and should work for browser testing. If you encounter issues, they're likely from WordPress's CORS settings (not your API), which you can fix with a WordPress CORS plugin.

