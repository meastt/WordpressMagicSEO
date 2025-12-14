# Quickstart Commands - Copy & Paste Reference

Ready-to-use commands for each site. Just copy and paste!

## 📊 Quick Reference

**Run Audit:**
```bash
./run_audit.sh https://yoursite.com --max-urls 50 --output json --output-file audit.json
```

**View Summary:**
```bash
./run_summarize.sh audit.json
```

**View Detailed Issues:**
```bash
./run_summarize.sh audit.json --detailed
```

---

## 🏠 GriddleKing.com

### Technical SEO Audit

**Single URL Audit:**
```bash
./run_audit.sh https://griddleking.com \
  --url https://griddleking.com/specific-page \
  --output html \
  --output-file griddleking_audit.html
```

**Full Site Audit (Sample - 50 URLs):**
```bash
./run_audit.sh https://griddleking.com \
  --max-urls 50 \
  --output json \
  --output-file griddleking_sample_audit.json
```

**Full Site Audit (All URLs - No Limit):**
```bash
./run_audit.sh https://griddleking.com \
  --output json \
  --output-file griddleking_full_audit.json
```

**Large Site Audit (300+ URLs - Faster Rate Limit):**
```bash
./run_audit.sh https://griddleking.com \
  --rate-limit 1.0 \
  --output json \
  --output-file griddleking_full_audit.json
```

**Full Site Audit with Orphaned Pages:**
```bash
./run_audit.sh https://griddleking.com \
  --check-orphaned \
  --output csv \
  --output-file griddleking_complete_audit.csv
```

### Content Automation (CLI)

**Note:** CLI currently requires explicit credentials. For .env-based auth, use API commands below.

**Analysis Only (View Plan) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://griddleking.com \
  "$(grep WP_GRIDDLEKING_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_GRIDDLEKING_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule all_at_once \
  --max-actions 0
```

**Full Execution (Test with 5 actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://griddleking.com \
  "$(grep WP_GRIDDLEKING_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_GRIDDLEKING_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8 \
  --max-actions 5
```

**Full Execution (All Actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://griddleking.com \
  "$(grep WP_GRIDDLEKING_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_GRIDDLEKING_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8
```

### API Commands (Using site_name from .env)

**List Sites:**
```bash
curl -X GET https://wordpress-magic-seo.vercel.app/api/sites
```

**Analysis Only:**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/analyze \
  -F "file=@gsc_export.csv" \
  -F "site_name=griddleking.com" \
  -F "use_ai_planner=true"
```

**Execute Next Action (One at a time - Recommended):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute-next \
  -F "site_name=griddleking.com" \
  -F "file=@gsc_export.csv"
```

**Full Execution (All at once):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute \
  -F "file=@gsc_export.csv" \
  -F "site_name=griddleking.com" \
  -F "schedule_mode=daily" \
  -F "batch_size=3" \
  -F "delay_hours=8" \
  -F "max_actions=5"
```

**Technical SEO Audit (API - Sample 50 URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://griddleking.com" \
  -F "max_urls=50" \
  -F "output_format=json"
```

**Technical SEO Audit (API - All URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://griddleking.com" \
  -F "output_format=json"
```

**Technical SEO Audit (API - Large Site 300+ URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://griddleking.com" \
  -F "rate_limit=1.0" \
  -F "output_format=json"
```

---

## 📸 PhotoTipsGuy.com

### Technical SEO Audit

**Single URL Audit:**
```bash
./run_audit.sh https://phototipsguy.com \
  --url https://phototipsguy.com/specific-page \
  --output html \
  --output-file phototipsguy_audit.html
```

**Full Site Audit (Sample - 50 URLs):**
```bash
./run_audit.sh https://phototipsguy.com \
  --max-urls 50 \
  --output json \
  --output-file phototipsguy_sample_audit.json
```

**Full Site Audit (All URLs - No Limit):**
```bash
./run_audit.sh https://phototipsguy.com \
  --output json \
  --output-file phototipsguy_full_audit.json
```

**Large Site Audit (300+ URLs - Faster Rate Limit):**
```bash
./run_audit.sh https://phototipsguy.com \
  --rate-limit 1.0 \
  --output json \
  --output-file phototipsguy_full_audit.json
```

**Full Site Audit with Orphaned Pages:**
```bash
./run_audit.sh https://phototipsguy.com \
  --check-orphaned \
  --output csv \
  --output-file phototipsguy_complete_audit.csv
```

### Content Automation (CLI)

**Note:** CLI currently requires explicit credentials. For .env-based auth, use API commands below.

**Analysis Only (View Plan) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://phototipsguy.com \
  "$(grep WP_PHOTOTIPSGUY_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_PHOTOTIPSGUY_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule all_at_once \
  --max-actions 0
```

**Full Execution (Test with 5 actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://phototipsguy.com \
  "$(grep WP_PHOTOTIPSGUY_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_PHOTOTIPSGUY_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8 \
  --max-actions 5
```

**Full Execution (All Actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://phototipsguy.com \
  "$(grep WP_PHOTOTIPSGUY_COM_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_PHOTOTIPSGUY_COM_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8
```

### API Commands (Using site_name from .env)

**Analysis Only:**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/analyze \
  -F "file=@gsc_export.csv" \
  -F "site_name=phototipsguy.com" \
  -F "use_ai_planner=true"
```

**Execute Next Action (One at a time - Recommended):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute-next \
  -F "site_name=phototipsguy.com" \
  -F "file=@gsc_export.csv"
```

**Full Execution (All at once):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute \
  -F "file=@gsc_export.csv" \
  -F "site_name=phototipsguy.com" \
  -F "schedule_mode=daily" \
  -F "batch_size=3" \
  -F "delay_hours=8" \
  -F "max_actions=5"
```

**Technical SEO Audit (API - Sample 50 URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://phototipsguy.com" \
  -F "max_urls=50" \
  -F "output_format=json"
```

**Technical SEO Audit (API - All URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://phototipsguy.com" \
  -F "output_format=json"
```

**Technical SEO Audit (API - Large Site 300+ URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://phototipsguy.com" \
  -F "rate_limit=1.0" \
  -F "output_format=json"
```

---

## 🐅 TigerTribe.net

### Technical SEO Audit

**Single URL Audit:**
```bash
./run_audit.sh https://tigertribe.net \
  --url https://tigertribe.net/specific-page \
  --output html \
  --output-file tigertribe_audit.html
```

**Full Site Audit (Sample - 50 URLs):**
```bash
./run_audit.sh https://tigertribe.net \
  --max-urls 50 \
  --output json \
  --output-file tigertribe_sample_audit.json
```

**Full Site Audit (All URLs - No Limit):**
```bash
./run_audit.sh https://tigertribe.net \
  --output json \
  --output-file tigertribe_full_audit.json
```

**Large Site Audit (300+ URLs - Faster Rate Limit):**
```bash
./run_audit.sh https://tigertribe.net \
  --rate-limit 1.0 \
  --output json \
  --output-file tigertribe_full_audit.json
```

**Full Site Audit with Orphaned Pages:**
```bash
./run_audit.sh https://tigertribe.net \
  --check-orphaned \
  --output csv \
  --output-file tigertribe_complete_audit.csv
```

### Content Automation (CLI)

**Note:** CLI currently requires explicit credentials. For .env-based auth, use API commands below.

**Analysis Only (View Plan) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://tigertribe.net \
  "$(grep WP_TIGERTRIBE_NET_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_TIGERTRIBE_NET_PASSWORD .env | cut -d'=' -f2)" \
  --schedule all_at_once \
  --max-actions 0
```

**Full Execution (Test with 5 actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://tigertribe.net \
  "$(grep WP_TIGERTRIBE_NET_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_TIGERTRIBE_NET_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8 \
  --max-actions 5
```

**Full Execution (All Actions) - Legacy Mode:**
```bash
./run_seo_automation.sh \
  gsc_export.csv \
  https://tigertribe.net \
  "$(grep WP_TIGERTRIBE_NET_USERNAME .env | cut -d'=' -f2)" \
  "$(grep WP_TIGERTRIBE_NET_PASSWORD .env | cut -d'=' -f2)" \
  --schedule daily \
  --batch-size 3 \
  --delay-hours 8
```

### API Commands (Using site_name from .env)

**Analysis Only:**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/analyze \
  -F "file=@gsc_export.csv" \
  -F "site_name=tigertribe.net" \
  -F "use_ai_planner=true"
```

**Execute Next Action (One at a time - Recommended):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute-next \
  -F "site_name=tigertribe.net" \
  -F "file=@gsc_export.csv"
```

**Full Execution (All at once):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/execute \
  -F "file=@gsc_export.csv" \
  -F "site_name=tigertribe.net" \
  -F "schedule_mode=daily" \
  -F "batch_size=3" \
  -F "delay_hours=8" \
  -F "max_actions=5"
```

**Technical SEO Audit (API - Sample 50 URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://tigertribe.net" \
  -F "max_urls=50" \
  -F "output_format=json"
```

**Technical SEO Audit (API - All URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://tigertribe.net" \
  -F "output_format=json"
```

**Technical SEO Audit (API - Large Site 300+ URLs):**
```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://tigertribe.net" \
  -F "rate_limit=1.0" \
  -F "output_format=json"
```

---

## 📊 Viewing Audit Results

After running an audit, get a summary of issues:

**Quick Summary:**
```bash
./run_summarize.sh audit.json
```

**Detailed Issues (per URL):**
```bash
./run_summarize.sh audit.json --detailed
```

**Custom File:**
```bash
./run_summarize.sh phototipsguy_full_audit.json
```

The summary shows:
- Overall statistics (critical issues, warnings, passed)
- Breakdown by category (Technical, On-Page, Links, Images, Performance, Schema)
- Top 10 most common issues
- URLs with the most issues
- Critical issues breakdown

## 📝 Notes

### For CLI Commands:
- CLI commands use shell substitution to read from `.env` file automatically
- Replace `gsc_export.csv` with your actual GSC export file path
- Use `--max-actions 0` to view plan without executing
- Use `--max-actions 5` to test with limited actions
- **Recommended:** Use API commands with `site_name` parameter for cleaner .env-based auth

### For Technical SEO Audit:

**URL Limits:**
- **No hard limit** - The system can handle sites with 300+ URLs or more
- `--max-urls` is optional - omit it to audit ALL URLs from sitemap
- The "50 URLs" examples are just samples for testing

**Performance & Timing:**
- Default rate limit: 2 seconds between requests (to be respectful to servers)
- **300 URLs** at 2s each = ~10 minutes minimum
- **300 URLs** at 1s each = ~5 minutes minimum
- Use `--rate-limit 1.0` for faster audits (if your server can handle it)
- Use `--rate-limit 0.5` for very fast audits (use with caution)

**Large Site Recommendations:**
- Start with `--max-urls 50` to test
- Then run full audit with `--rate-limit 1.0` for 300+ URLs
- For very large sites (1000+ URLs), consider running in batches:
  ```bash
  # Batch 1: URLs 1-300
  ./run_audit.sh https://yoursite.com --max-urls 300 --output json --output-file batch1.json
  
  # Batch 2: URLs 301-600 (would need to modify to start from offset)
  # Or just let it run - it will process all URLs sequentially
  ```

**Memory & Resources:**
- Processes URLs sequentially (one at a time) - memory efficient
- Results stored in memory until completion, then written to file
- For 300 URLs: ~50-100MB memory usage (depends on page sizes)
- No issues with sites up to 1000+ URLs

### For API Commands:
- Replace `https://wordpress-magic-seo.vercel.app` with your actual API URL
- When using `site_name`, credentials are loaded from `.env` automatically
- For local testing, use `http://localhost:5000` instead

### Schedule Modes:
- `all_at_once` - Execute all actions immediately
- `daily` - Execute in batches with delays (recommended)
- `hourly` - Execute every hour

### Batch Settings:
- `--batch-size 3` - Process 3 posts per batch
- `--delay-hours 8` - Wait 8 hours between batches
- Adjust based on your rate limits and needs

---

## 🔧 Quick Setup Reminder

1. **Create and activate virtual environment (if not done already):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or: venv\Scripts\activate  # Windows
   ```

2. **Install dependencies (if not done already):**
   ```bash
   pip install -r requirements.txt
   ```
   
3. **Running Commands - Choose ONE method:**

   **Method 1: Use wrapper scripts (Easiest - Recommended):**
   ```bash
   ./run_audit.sh https://phototipsguy.com --max-urls 50 --output json
   ./run_seo_automation.sh gsc_export.csv https://phototipsguy.com ...
   ```
   
   **Method 2: Use venv Python directly:**
   ```bash
   ./venv/bin/./run_audit.sh https://phototipsguy.com ...
   ./venv/bin/./run_seo_automation.sh gsc_export.csv ...
   ```
   
   **Method 3: Activate venv and use python3:**
   ```bash
   source venv/bin/activate
   python3 seo_audit_cli.py https://phototipsguy.com ...
   python3 seo_automation_main.py gsc_export.csv ...
   ```
   
   **⚠️ Important:** If you get "ModuleNotFoundError", your `python` command is pointing to the wrong interpreter. Use `python3` or the wrapper scripts instead!

2. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Verify site configuration:**
   ```bash
   python3 -c "from config import list_sites; print(list_sites())"
   ```

---

**Last Updated:** 2025-01-XX

