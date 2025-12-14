# WordPress Magic SEO - Complete Automation System

AI-powered SEO automation that analyzes your Google Search Console data, identifies content opportunities, and automatically creates/updates/optimizes WordPress content using Claude AI.

## 🎯 What It Does

1. **Analyzes GSC Data** - Processes 12 months of search console metrics
2. **Fetches Sitemap** - Compares your sitemap with actual performance
3. **Identifies Issues** - Finds dead content, duplicates, and opportunities
4. **Creates Strategic Plan** - AI-powered prioritization of actions
5. **Executes Content** - Writes, updates, or removes content automatically
6. **Tracks Results** - Comprehensive CSV reporting

## 🚀 Features

### Content Strategy
- **Delete** dead URLs with zero traffic
- **301 Redirect** duplicate content to best-performing versions
- **Update** high-impression, low-CTR pages
- **Create** new content for high-opportunity keywords

### AI-Powered Content
- Uses Claude Sonnet 4 for research and writing
- Web search integration for current information
- Competitor analysis for content structure
- Natural, helpful writing (not robotic)
- SEO metadata generation
- Internal/external link building

### Scheduling & Safety
- Rate limiting to respect API limits
- Batch processing (e.g., 3 posts every 8 hours)
- Manual review before publishing recommended
- Comprehensive execution logging

## 📋 Setup

### 1. Install Dependencies

**Create and activate virtual environment (recommended):**

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Or install globally (not recommended):**

```bash
pip install -r requirements.txt
```

**Note:** Always activate the virtual environment before running commands:
```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate    # Windows
```

### 2. Set Environment Variables

**Option A: Use .env file (Recommended for Local Development)**

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   # WordPress Site Credentials
   # Format: WP_{DOMAIN}_USERNAME and WP_{DOMAIN}_PASSWORD
   # Replace dots with underscores in domain names
   
   WP_GRIDDLEKING_COM_USERNAME=your_username
   WP_GRIDDLEKING_COM_PASSWORD=your_app_password
   WP_GRIDDLEKING_COM_URL=https://griddleking.com
   WP_GRIDDLEKING_COM_NICHE=outdoor cooking
   
   WP_PHOTOTIPSGUY_COM_USERNAME=your_username
   WP_PHOTOTIPSGUY_COM_PASSWORD=your_app_password
   WP_PHOTOTIPSGUY_COM_URL=https://phototipsguy.com
   WP_PHOTOTIPSGUY_COM_NICHE=photography
   
   # API Keys
   ANTHROPIC_API_KEY=your-anthropic-key
   GOOGLE_GEMINI_API_KEY=your-gemini-key
   ```

**Option B: Export Environment Variables**

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export WP_GRIDDLEKING_COM_USERNAME="your_username"
export WP_GRIDDLEKING_COM_PASSWORD="your_app_password"
```

**Note:** The `.env` file is gitignored and will never be committed to version control. Your credentials are safe!

### 3. WordPress Setup

Create an application password in WordPress:
1. Go to Users → Profile
2. Scroll to "Application Passwords"
3. Create new password
4. Save it securely

### 4. Export GSC Data

1. Go to Google Search Console
2. Select your property
3. Performance → Export → Download CSV
4. **Important:** Export 12 months of data with ALL metrics

## 💻 Usage

### Option 1: Technical SEO Audit (Standalone)

**Audit a single URL:**
```bash
python seo_audit_cli.py https://yoursite.com --url https://yoursite.com/specific-page --output html --output-file audit.html
```

**Audit entire site:**
```bash
python seo_audit_cli.py https://yoursite.com --max-urls 50 --output json --output-file audit.json
```

**Options:**
- `--url`: Audit single URL instead of full site
- `--max-urls`: Limit number of URLs (default: all)
- `--output`: Format (json, csv, html)
- `--output-file`: Save to file
- `--rate-limit`: Seconds between requests (default: 2.0)
- `--check-orphaned`: Check for orphaned pages (requires full crawl)

### Option 2: Command Line (Content Automation)

```bash
python seo_automation_main.py \
  gsc_export.csv \
  https://yoursite.com \
  your_wp_username \
  "your-app-password" \
  --schedule all_at_once \
  --batch-size 3 \
  --delay-hours 8 \
  --max-actions 10
```

### Option 3: API (Vercel Deployment)

**Analysis Only (No Execution):**

```bash
curl -X POST https://wordpress-magic-seo.vercel.app/analyze \
  -F "file=@gsc_export.csv" \
  -F "site_url=https://yoursite.com" \
  -F "username=your_username" \
  -F "application_password=your_app_password"
```

**Full Execution:**

```bash
curl -X POST https://wordpress-magic-seo.vercel.app/execute \
  -F "file=@gsc_export.csv" \
  -F "site_url=https://yoursite.com" \
  -F "username=your_username" \
  -F "application_password=your_app_password" \
  -F "schedule_mode=daily" \
  -F "batch_size=3" \
  -F "delay_hours=8" \
  -F "max_actions=5"
```

**Technical SEO Audit:**

```bash
curl -X POST https://wordpress-magic-seo.vercel.app/api/seo-audit \
  -F "site_url=https://yoursite.com" \
  -F "max_urls=50" \
  -F "output_format=json"
```

## 🎛️ Configuration Options

| Parameter | Options | Description |
|-----------|---------|-------------|
| `schedule_mode` | `all_at_once`, `daily`, `hourly` | Execution timing |
| `batch_size` | Integer (1-20) | Posts per batch |
| `delay_hours` | Float | Hours between batches |
| `max_actions` | Integer or None | Limit for testing |

## 📊 Output

### CSV Results File
Every execution creates a CSV with:
- Timestamp
- Action type (create/update/delete/redirect)
- Status (success/failed)
- URL
- Post ID
- Error message (if failed)

### Console Summary
```
✅ EXECUTION COMPLETE
Total actions: 25
Successful: 23
Failed: 2
Success rate: 92.0%
```

## 🏗️ Architecture

```
┌─────────────────┐
│  GSC CSV Data   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GSCProcessor    │ ← Parse and analyze metrics
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SitemapAnalyzer │ ← Compare with actual site
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ StrategicPlanner│ ← AI-powered prioritization
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ClaudeGenerator │ ← Research & write content
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WPPublisher     │ ← Publish to WordPress
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Results CSV     │
└─────────────────┘
```

## 🔒 Security Notes

- **Never commit** API keys or passwords to Git
- Use environment variables for sensitive data
- WordPress application passwords are safer than main password
- Test with `--max-actions` flag first
- Review AI content before publishing to live site

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY required"
Set your API key: `export ANTHROPIC_API_KEY="sk-ant-..."`

### "Post not found"
URL mismatch - check your sitemap vs GSC export URLs

### Rate limit errors
Increase `delay_hours` or reduce `batch_size`

### 301 Redirect fails
Install WordPress "Redirection" plugin for redirect support

## 📈 Best Practices

1. **Start small** - Use `--max-actions 5` for testing
2. **Review content** - Manually check AI-generated posts
3. **Backup first** - Backup WordPress before bulk changes
4. **Monitor performance** - Track GSC metrics after changes
5. **Iterate** - Run monthly for continuous optimization

## 🤝 Contributing

This is a personal project but open to improvements! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📝 License

MIT License - Use however you want!

## 🎉 Credits

Built with:
- [Claude AI](https://anthropic.com) - Content generation
- [WordPress REST API](https://developer.wordpress.org/rest-api/) - Publishing
- [Pandas](https://pandas.pydata.org/) - Data analysis
- [Flask](https://flask.palletsprojects.com/) - API framework

---

**Made with ❤️ for multi-site SEO automation**