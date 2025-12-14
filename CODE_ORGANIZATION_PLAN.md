# Code Organization Plan

## Current Problem

**20 Python files in root directory** - This is messy and hard to navigate.

## Proposed Structure

```
WordpressMagicSEO/
├── seo_automation_main.py      # Main CLI entry point (stays in root)
├── config.py                    # Configuration (stays in root)
│
├── api/                         # API endpoints
│   ├── generate.py
│   └── index.py
│
├── core/                        # Core pipeline components
│   ├── __init__.py
│   ├── pipeline.py              # SEOAutomationPipeline (from seo_automation_main.py)
│   ├── execution_scheduler.py
│   └── state_manager.py
│
├── content/                     # Content generation & validation
│   ├── __init__.py
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── claude_generator.py  # claude_content_generator.py
│   │   └── gemini_images.py     # gemini_image_generator.py
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── qa_validator.py     # content_qa_validator.py
│   │   └── seo_validator.py    # seo_checklist_validator.py
│   └── quality_scorer.py       # content_quality_scorer.py
│
├── analysis/                    # Analysis & planning
│   ├── __init__.py
│   ├── planners/
│   │   ├── __init__.py
│   │   ├── ai_planner.py        # ai_strategic_planner.py
│   │   └── rule_planner.py     # strategic_planner.py (legacy)
│   ├── niche_analyzer.py
│   ├── competitive_analyzer.py
│   └── page_type_detector.py
│
├── data/                       # Data processing
│   ├── __init__.py
│   ├── processor.py            # multi_site_content_agent.py (DataProcessor)
│   └── sitemap_analyzer.py
│
├── wordpress/                   # WordPress integration
│   ├── __init__.py
│   └── publisher.py            # wordpress_publisher.py
│
├── seo/                        # SEO intelligence
│   ├── __init__.py
│   └── linking_engine.py       # smart_linking_engine.py
│
├── affiliate/                  # Affiliate features
│   ├── __init__.py
│   ├── manager.py              # affiliate_link_manager.py
│   └── updater.py              # affiliate_link_updater.py
│
└── utils/                       # Utilities (already exists)
    ├── __init__.py
    ├── error_handler.py
    └── state_storage.py
```

## File Mapping

| Current File | New Location | Category |
|--------------|--------------|----------|
| `seo_automation_main.py` | `core/pipeline.py` | Core |
| `execution_scheduler.py` | `core/execution_scheduler.py` | Core |
| `state_manager.py` | `core/state_manager.py` | Core |
| `claude_content_generator.py` | `content/generators/claude_generator.py` | Content |
| `gemini_image_generator.py` | `content/generators/gemini_images.py` | Content |
| `content_qa_validator.py` | `content/validators/qa_validator.py` | Content |
| `seo_checklist_validator.py` | `content/validators/seo_validator.py` | Content |
| `content_quality_scorer.py` | `content/quality_scorer.py` | Content |
| `ai_strategic_planner.py` | `analysis/planners/ai_planner.py` | Analysis |
| `strategic_planner.py` | `analysis/planners/rule_planner.py` | Analysis |
| `niche_analyzer.py` | `analysis/niche_analyzer.py` | Analysis |
| `competitive_analyzer.py` | `analysis/competitive_analyzer.py` | Analysis |
| `page_type_detector.py` | `analysis/page_type_detector.py` | Analysis |
| `multi_site_content_agent.py` | `data/processor.py` | Data |
| `sitemap_analyzer.py` | `data/sitemap_analyzer.py` | Data |
| `wordpress_publisher.py` | `wordpress/publisher.py` | WordPress |
| `smart_linking_engine.py` | `seo/linking_engine.py` | SEO |
| `affiliate_link_manager.py` | `affiliate/manager.py` | Affiliate |
| `affiliate_link_updater.py` | `affiliate/updater.py` | Affiliate |
| `config.py` | `config.py` (stays in root) | Config |

## Benefits

1. **Clear Organization**: Files grouped by functionality
2. **Easier Navigation**: Know where to find things
3. **Better Imports**: `from content.generators import ClaudeGenerator`
4. **Scalability**: Easy to add new features in right place
5. **Professional**: Standard Python project structure

## Migration Steps

1. Create new directory structure
2. Move files to new locations
3. Update all imports across codebase
4. Update `vercel.json` if needed
5. Test that everything still works

## Import Changes

**Before:**
```python
from claude_content_generator import ClaudeContentGenerator
from wordpress_publisher import WordPressPublisher
from ai_strategic_planner import AIStrategicPlanner
```

**After:**
```python
from content.generators import ClaudeGenerator
from wordpress.publisher import WordPressPublisher
from analysis.planners import AIPlanner
```

## Files That Stay in Root

- `seo_automation_main.py` - Main CLI entry point (or move to `core/` and create root wrapper)
- `config.py` - Configuration (common to keep in root)
- `requirements.txt` - Dependencies
- `vercel.json` - Vercel config
- `README.md` - Documentation

## Alternative: Simpler Structure

If you want less nesting:

```
WordpressMagicSEO/
├── core/          # Core pipeline, execution, state
├── content/        # All content generation & validation
├── analysis/       # All analysis & planning
├── data/           # Data processing
├── wordpress/      # WordPress integration
├── seo/            # SEO intelligence
└── affiliate/      # Affiliate features
```

This reduces nesting but still organizes by function.

---

**Recommendation:** Start with the simpler structure (less nesting) to minimize import path changes.

