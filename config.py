"""
Multi-Site Configuration Manager
---------------------------------
Loads site configurations from .env file or SITES_CONFIG environment variable.
Credentials are stored securely in .env file (not in code).
"""

import os
import json

# Try to load .env file (optional - will work without it)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed - will use environment variables directly
    pass


def _normalize_domain(domain: str) -> str:
    """Convert domain to env var format (e.g., 'griddleking.com' -> 'GRIDDLEKING_COM')"""
    return domain.replace('.', '_').upper()


def _get_env_credential(domain: str, key: str) -> str:
    """Get credential from .env file using format: WP_{DOMAIN}_{KEY}"""
    normalized = _normalize_domain(domain)
    env_key = f"WP_{normalized}_{key.upper()}"
    return os.getenv(env_key)


def get_sites_config():
    """
    Load sites configuration from:
    1. .env file (WP_{DOMAIN}_* variables) - highest priority
    2. SITES_CONFIG environment variable (JSON)
    3. Hardcoded defaults (fallback, without passwords)
    
    Returns:
        dict: Site configurations keyed by domain
    """
    sites = {}
    
    # Method 1: Load from .env file
    # Look for all WP_*_USERNAME variables to discover configured sites
    env_vars = os.environ
    discovered_domains = set()
    
    for env_key in env_vars:
        if env_key.startswith('WP_') and env_key.endswith('_USERNAME'):
            # Extract domain: WP_GRIDDLEKING_COM_USERNAME -> griddleking.com
            domain_part = env_key[3:-9]  # Remove 'WP_' and '_USERNAME'
            domain = domain_part.replace('_', '.').lower()
            discovered_domains.add(domain)
    
    # Build site configs from .env
    for domain in discovered_domains:
        username = _get_env_credential(domain, 'USERNAME')
        password = _get_env_credential(domain, 'PASSWORD')
        url = _get_env_credential(domain, 'URL')
        niche = _get_env_credential(domain, 'NICHE')
        
        if username and password:
            sites[domain] = {
                "url": url or f"https://{domain}",
                "wp_username": username,
                "wp_app_password": password,
                "niche": niche or "general"
            }
    
    # Method 2: Load from SITES_CONFIG JSON env var (if no .env sites found)
    if not sites:
        sites_json = os.getenv('SITES_CONFIG')
        if sites_json:
            try:
                sites = json.loads(sites_json)
            except json.JSONDecodeError:
                pass
    
    # Method 3: Fallback to hardcoded structure (without passwords)
    if not sites:
        sites = {
            "griddleking.com": {
                "url": "https://griddleking.com",
                "wp_username": os.getenv("WP_GRIDDLEKING_COM_USERNAME", ""),
                "wp_app_password": os.getenv("WP_GRIDDLEKING_COM_PASSWORD", ""),
                "niche": os.getenv("WP_GRIDDLEKING_COM_NICHE", "outdoor cooking")
            },
            "phototipsguy.com": {
                "url": "https://phototipsguy.com",
                "wp_username": os.getenv("WP_PHOTOTIPSGUY_COM_USERNAME", ""),
                "wp_app_password": os.getenv("WP_PHOTOTIPSGUY_COM_PASSWORD", ""),
                "niche": os.getenv("WP_PHOTOTIPSGUY_COM_NICHE", "photography")
            },
            "tigertribe.net": {
                "url": "https://tigertribe.net",
                "wp_username": os.getenv("WP_TIGERTRIBE_NET_USERNAME", ""),
                "wp_app_password": os.getenv("WP_TIGERTRIBE_NET_PASSWORD", ""),
                "niche": os.getenv("WP_TIGERTRIBE_NET_NICHE", "wild cats")
            }
        }
        # Remove sites without credentials
        sites = {k: v for k, v in sites.items() if v.get('wp_username') and v.get('wp_app_password')}
    
    return sites


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
        available = list(sites.keys())
        raise ValueError(
            f"Site '{site_name}' not configured. "
            f"Available sites: {available}. "
            f"Add credentials to .env file using format: "
            f"WP_{_normalize_domain(site_name)}_USERNAME and "
            f"WP_{_normalize_domain(site_name)}_PASSWORD"
        )
    
    site = sites[site_name]
    
    # Validate required fields
    if not site.get('wp_username') or not site.get('wp_app_password'):
        raise ValueError(
            f"Site '{site_name}' is missing credentials. "
            f"Add to .env: WP_{_normalize_domain(site_name)}_USERNAME and "
            f"WP_{_normalize_domain(site_name)}_PASSWORD"
        )
    
    return site


def list_sites():
    """
    Get list of all configured site names.
    
    Returns:
        list: List of site domain names
    """
    return list(get_sites_config().keys())
