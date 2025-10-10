"""
Multi-Site Configuration Manager
---------------------------------
Loads site configurations from SITES_CONFIG environment variable.
"""

import os
import json


def get_sites_config():
    """Load sites from SITES_CONFIG env var"""
    sites_json = os.getenv('SITES_CONFIG', '{}')
    return json.loads(sites_json)


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
