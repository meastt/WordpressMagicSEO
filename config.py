"""
Multi-Site Configuration Manager
---------------------------------
Loads site configurations from SITES_CONFIG environment variable or hardcoded defaults.
"""

import os
import json


# Hardcoded site configurations (fallback if SITES_CONFIG env var not set)
HARDCODED_SITES = {
    "phototipsguy.com": {
        "url": "https://phototipsguy.com",
        "wp_username": "YOUR_USERNAME_HERE",
        "wp_app_password": "YOUR_APP_PASSWORD_HERE",
        "niche": "Photography tips, camera reviews, astrophotography"
    },
    # Add more sites here:
    # "example.com": {
    #     "url": "https://example.com",
    #     "wp_username": "username",
    #     "wp_app_password": "xxxx xxxx xxxx xxxx",
    #     "niche": "Your niche description"
    # },
}


def get_sites_config():
    """Load sites from SITES_CONFIG env var or use hardcoded defaults"""
    sites_json = os.getenv('SITES_CONFIG')

    if sites_json:
        # Use environment variable if set
        return json.loads(sites_json)
    else:
        # Fall back to hardcoded sites
        return HARDCODED_SITES


def get_site(site_name):
    """
    Get configuration for a specific site.
    
    Args:
        site_name: Domain name of the site (e.g., "griddleking.com")
    
    Returns:
        dict: Site configuration with keys: url, wp_username, wp_app_password, niche
    
    Raises:
        ValueError: If site is not configured
    """
    sites = get_sites_config()
    if site_name not in sites:
        raise ValueError(f"Site {site_name} not configured. Available sites: {list(sites.keys())}")
    return sites[site_name]


def list_sites():
    """
    Get list of all configured site names.
    
    Returns:
        list: List of site domain names
    """
    return list(get_sites_config().keys())
