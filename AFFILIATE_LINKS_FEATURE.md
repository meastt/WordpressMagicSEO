# Affiliate Link Management Feature

## Overview

This feature enables automated affiliate link management with AI-powered content updates. Users can upload their affiliate links via CSV or add them manually, then use AI to intelligently scan and update their content with relevant affiliate links.

## Features Implemented

### 1. Affiliate Link Storage & Management

**New File: `affiliate_link_manager.py`**
- Stores affiliate links per site with product metadata
- Supports CSV upload for bulk import
- Manual entry for individual links
- Search functionality to find relevant links based on keywords
- Usage tracking for each affiliate link

**Storage Format:**
```json
{
  "id": 1,
  "url": "https://brand.com/product?aff=123",
  "brand": "traeger",
  "product_name": "Flatrock Griddle",
  "product_type": "outdoor griddle",
  "keywords": ["griddle", "cooking"],
  "usage_count": 5,
  "added_at": "2025-10-14T..."
}
```

### 2. AI-Powered Content Updates

**New File: `affiliate_link_updater.py`**
- Uses Claude AI to intelligently update content
- Removes outdated or irrelevant links
- Adds relevant affiliate links where they provide value
- Maintains content quality and readability
- Provides detailed change reports

**Features:**
- Single post update
- Bulk update multiple posts
- Auto-publish option
- Detailed analytics on changes made

### 3. Dashboard UI

**Updated: `index.html`**

New section added with three modes:
1. **Skip** - No affiliate links
2. **Upload CSV** - Bulk import from CSV file
3. **Manual Entry** - Add individual links with a form

**CSV Format:**
```csv
url,brand,product_name,product_type,keywords
https://brand.com/product?aff=123,Traeger,Flatrock Griddle,outdoor griddle,griddle|cooking
```

**UI Features:**
- Toggle to enable AI-powered affiliate link updates
- Dynamic form that shows/hides based on mode selection
- Ability to add multiple links manually
- File upload for CSV import

### 4. Backend API Endpoints

**Updated: `api/generate.py`**

New endpoints:
- `GET /api/affiliate/links?site_name=domain.com` - Get all links
- `POST /api/affiliate/links/add` - Add single link
- `POST /api/affiliate/links/upload` - Upload CSV
- `DELETE /api/affiliate/links/delete/:id?site_name=domain.com` - Delete link
- `POST /api/affiliate/update-content` - Update single post with AI
- `POST /api/affiliate/bulk-update` - Bulk update multiple posts

### 5. GA4 CSV Import Fix

**Updated: `multi_site_content_agent.py`**

Improvements:
- Auto-detect header rows in GA4 exports (skips metadata)
- Better column name normalization
- Remove empty rows automatically
- Support for various GA4 export formats
- Enhanced error messages and logging
- Better encoding detection (UTF-8, Latin-1)

### 6. Content Generation Integration

**Updated: `claude_content_generator.py`, `execution_scheduler.py`, `seo_automation_main.py`**

- Content generator now accepts affiliate links as parameter
- Execution scheduler searches for relevant affiliate links based on keywords
- Automatically includes affiliate links when creating/updating posts
- Tracks usage statistics

## Usage Examples

### Example 1: Upload Affiliate Links via CSV

1. Create a CSV file with your affiliate links:
```csv
url,brand,product_name,product_type,keywords
https://amazon.com/dp/B123?tag=yourtag,Amazon,ZWO ASI533MC,camera,astrophotography|imaging
https://bhphoto.com/c/product/456?BI=789,B&H,Sky-Watcher EQ6-R,mount,telescope|mount
```

2. In the dashboard, select "Upload CSV" mode
3. Upload your CSV file
4. Enable "AI-powered affiliate link updates"
5. Run your SEO automation

### Example 2: Manual Entry

1. In the dashboard, select "Manual Entry" mode
2. Fill in the form:
   - **Affiliate URL:** https://brand.com/product?aff=123
   - **Brand:** Traeger
   - **Product Name:** Flatrock Griddle
   - **Product Type:** outdoor griddle
3. Click "+ Add Another Link" for more entries
4. Enable "AI-powered affiliate link updates"
5. Run your SEO automation

### Example 3: Bulk Update Existing Posts via API

```javascript
const response = await fetch('/api/affiliate/bulk-update', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    site_name: 'griddleking.com',
    post_ids: [123, 456, 789],
    auto_publish: false,
    limit: 10
  })
});
```

### Example 4: Update Single Post via API

```javascript
const response = await fetch('/api/affiliate/update-content', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    site_name: 'griddleking.com',
    post_id: 123,
    keywords: ['griddle', 'outdoor cooking'],
    auto_publish: true
  })
});
```

## How It Works

### Content Update Flow

1. **User uploads affiliate links** (CSV or manual)
2. **Links stored per site** in `/tmp/{site_name}_affiliate_links.json`
3. **When creating/updating content:**
   - System searches for relevant links based on content keywords
   - Finds top 5 most relevant affiliate links
   - Passes links to AI content generator
   - AI intelligently inserts links where they add value
4. **Usage tracking:** Each time a link is used, its usage count increments

### AI Link Insertion Logic

The AI is instructed to:
- Only add affiliate links where they genuinely help readers
- Use natural anchor text (product names, helpful phrases)
- Add 2-5 relevant links maximum per post
- Remove existing affiliate links if they don't match available products
- Maintain content helpfulness and readability

### Relevance Scoring

Links are scored based on:
- Brand match: +10 points
- Product type match: +5 points
- Keyword in product name: +3 points
- Keyword in product type: +2 points
- Keyword in stored keywords: +1 point

Top 5 highest-scoring links are provided to AI.

## File Structure

```
/workspace/
├── affiliate_link_manager.py       # NEW: Link storage & management
├── affiliate_link_updater.py       # NEW: AI-powered content updates
├── api/generate.py                 # UPDATED: Added affiliate endpoints
├── claude_content_generator.py     # UPDATED: Accepts affiliate links
├── execution_scheduler.py          # UPDATED: Integrates affiliate links
├── seo_automation_main.py          # UPDATED: Loads affiliate manager
├── wordpress_publisher.py          # UPDATED: Added get_post method
├── multi_site_content_agent.py     # UPDATED: Fixed GA4 CSV import
├── index.html                      # UPDATED: Added affiliate UI
└── vercel.json                     # UPDATED: Added affiliate routes
```

## Environment Variables

No new environment variables required. Uses existing:
- `ANTHROPIC_API_KEY` - For AI-powered content updates

## Storage Location

- **Affiliate Links:** `/tmp/{site_name}_affiliate_links.json`
- **State Management:** `/tmp/{site_name}_state.json` (existing)

## API Response Examples

### Upload CSV Response
```json
{
  "success": true,
  "site": "griddleking.com",
  "results": {
    "added": 15,
    "skipped": 2,
    "errors": []
  },
  "message": "Processed CSV: 15 added, 2 skipped"
}
```

### Update Content Response
```json
{
  "success": true,
  "updated_content": "<html>...</html>",
  "links_added": [
    {
      "product": "Traeger Flatrock",
      "url": "https://...",
      "placement": "Added in cooking section"
    }
  ],
  "links_removed": [
    {
      "url": "https://old-link.com",
      "reason": "Product no longer available"
    }
  ],
  "analysis": "Updated content with 2 relevant affiliate links...",
  "published": true,
  "post_id": 123
}
```

## Testing

To test the feature:

1. **Add test affiliate links:**
   ```bash
   curl -X POST https://your-app.vercel.app/api/affiliate/links/add \
     -H "Content-Type: application/json" \
     -d '{
       "site_name": "griddleking.com",
       "url": "https://amazon.com/product?tag=test",
       "brand": "TestBrand",
       "product_name": "Test Product",
       "product_type": "test category"
     }'
   ```

2. **View links:**
   ```bash
   curl https://your-app.vercel.app/api/affiliate/links?site_name=griddleking.com
   ```

3. **Update a post:**
   ```bash
   curl -X POST https://your-app.vercel.app/api/affiliate/update-content \
     -H "Content-Type: application/json" \
     -d '{
       "site_name": "griddleking.com",
       "post_id": 123,
       "auto_publish": false
     }'
   ```

## Troubleshooting

### Links not appearing in content
- Check that affiliate links are uploaded for the site
- Ensure keywords match between content and affiliate links
- Verify AI is enabled (ANTHROPIC_API_KEY set)
- Check relevance scores (links need positive score to be considered)

### GA4 CSV not importing
- Ensure file is in correct format (CSV or Excel)
- Check that file has "page" or "landing_page" column
- Look at console logs for specific error messages
- GA4 exports with page titles (not URLs) won't merge with GSC data

### CSV upload errors
- Verify CSV format matches expected structure
- Ensure all required fields are present (url, brand, product_name, product_type)
- Check for special characters that might need escaping

## Future Enhancements

Potential improvements:
- Link performance tracking (clicks, conversions)
- A/B testing different affiliate link placements
- Automatic link expiration/rotation
- Link health checking (detect broken affiliate links)
- Category-based link matching
- Seasonal link prioritization
