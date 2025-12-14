"""
seo_automation_main.py
=====================
Main CLI entry point for SEO automation system.

This is a wrapper that imports from the reorganized core.pipeline module.
"""

from core.pipeline import SEOAutomationPipeline, main

# Re-export for backward compatibility
__all__ = ['SEOAutomationPipeline', 'main']

if __name__ == "__main__":
    main()

