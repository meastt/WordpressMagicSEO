# 🚀 Vercel Deployment Checklist - Phase 1

## Step 1: Environment Variables

Set these in Vercel Dashboard → Settings → Environment Variables:

### 1. ANTHROPIC_API_KEY
```
Your Claude API key (sk-ant-api03-...)
```

### 2. SITES_CONFIG
```json
{"griddleking.com":{"url":"https://griddleking.com","wp_username":"meastt09","wp_app_password":"6MVb4gZoOJ2BcWQAe1XKVMN6","niche":"outdoor cooking"},"phototipsguy.com":{"url":"https://phototipsguy.com","wp_username":"meastt09@gmail.com","wp_app_password":"BHxWFZhbJh8oziKEzHMA4Bpp","niche":"photography"},"tigertribe.net":{"url":"https://tigertribe.net","wp_username":"joeedwards","wp_app_password":"m32Gutsp3JW1FQRPSFcjKcve","niche":"wild cats"}}
```

**⚠️ IMPORTANT:** 
- Must be valid JSON (no line breaks)
- No spaces in WordPress app passwords
- Use double quotes for JSON, wrap entire value in single quotes

---

## Step 2: Verify Files

Ensure these files exist:
- ✅ `config.py`
- ✅ `state_manager.py`
- ✅ `api/generate.py` (updated with /sites endpoint)
- ✅ `requirements.txt` (includes flask-cors)
- ✅ `vercel.json`

---

## Step 3: Test Endpoints After Deployment

### Test 1: Health Check
```bash
curl https://wordpress-magic-seo.vercel.app/api/health
```
Expected:
```json
{"status": "healthy", "timestamp": "..."}
```

### Test 2: API Info
```bash
curl https://wordpress-magic-seo.vercel.app/api/
```
Expected:
```json
{
  "name": "WordPress Magic SEO - Multi-Site Portfolio Manager",
  "version": "3.0",
  ...
}
```

### Test 3: Sites List (NEW)
```bash
curl https://wordpress-magic-seo.vercel.app/api/sites
```
Expected:
```json
{
  "sites": [
    {"name": "griddleking.com", "pending_actions": 0, "completed_actions": 0, "total_actions": 0},
    {"name": "phototipsguy.com", "pending_actions": 0, "completed_actions": 0, "total_actions": 0},
    {"name": "tigertribe.net", "pending_actions": 0, "completed_actions": 0, "total_actions": 0}
  ],
  "total_sites": 3
}
```

---

## Step 4: Verify Dependencies

Ensure `requirements.txt` includes:
- ✅ Flask==2.3.2
- ✅ flask-cors>=4.0.0
- ✅ pandas>=1.5.0
- ✅ requests>=2.31.0
- ✅ anthropic>=0.18.0
- ✅ werkzeug>=2.3.0
- ✅ openpyxl>=3.0.0

---

## Step 5: Git Commit & Push

```bash
# Check status
git status

# Add Phase 1 files
git add config.py state_manager.py api/generate.py requirements.txt

# Add documentation
git add PHASE1_COMPLETE.md DEPLOYMENT_CHECKLIST.md test_phase1.py

# Commit
git commit -m "Phase 1: Multi-site infrastructure with state management

- Add config.py for multi-site configuration from env vars
- Add state_manager.py for per-site action tracking
- Add /sites API endpoint to list configured sites
- Update API to v3.0 with multi-site support
- Add comprehensive test suite (test_phase1.py)
- All tests passing ✓"

# Push to trigger Vercel deployment
git push origin cursor/set-up-multi-site-infrastructure-4322
```

---

## Step 6: Monitor Deployment

1. Go to Vercel Dashboard
2. Watch deployment logs
3. Check for build errors
4. Verify environment variables are set

---

## Step 7: Post-Deployment Verification

### Check /sites endpoint works:
```bash
curl https://wordpress-magic-seo.vercel.app/api/sites
```

If you see the 3 sites listed, Phase 1 is successfully deployed! 🎉

---

## Troubleshooting

### Error: "Site X not configured"
→ Check SITES_CONFIG env var is set correctly in Vercel

### Error: "Failed to load sites"
→ Check Vercel logs for JSON parsing errors in SITES_CONFIG

### Error: Module not found
→ Check requirements.txt includes all dependencies
→ Redeploy to rebuild dependencies

### State files not persisting
→ Expected on Vercel (uses /tmp which is ephemeral)
→ Will fix in future phase with Vercel KV

---

## Phase 1 Deployment Success Criteria

- ✅ `/api/health` returns 200
- ✅ `/api/` shows version 3.0
- ✅ `/api/sites` returns all 3 configured sites
- ✅ No build errors in Vercel logs
- ✅ Environment variables are set

---

**Once all criteria are met, Phase 1 is live and ready for Phase 2!**
