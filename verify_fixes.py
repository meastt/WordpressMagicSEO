import requests
from bs4 import BeautifulSoup
import json
import sys

def verify_url(url):
    print(f"🔍 Verifying: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'MagicSEO-Verifier/1.0'})
        if response.status_code != 200:
            print(f"  ❌ Failed to fetch: {response.status_code}")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. H1 Check
        h1s = soup.find_all('h1')
        h1_status = "❌ Missing"
        if len(h1s) == 1:
            h1_status = f"✅ Present: '{h1s[0].get_text(strip=True)[:50]}...'"
        elif len(h1s) > 1:
            h1_status = f"⚠️ Multiple ({len(h1s)})"
        
        print(f"  • H1: {h1_status}")

        # 2. Schema Check
        schemas = soup.find_all('script', type='application/ld+json')
        schema_status = "❌ Missing"
        if schemas:
            count = len(schemas)
            types = []
            for s in schemas:
                try:
                    data = json.loads(s.string)
                    if isinstance(data, list):
                        for item in data:
                            types.append(item.get('@type', 'Unknown'))
                    else:
                        types.append(data.get('@type', 'Unknown'))
                except:
                    pass
            schema_status = f"✅ Present ({count} blocks): {', '.join(types)}"
        
        print(f"  • Schema: {schema_status}")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    urls_to_check = [
        "https://griddleking.com/do-you-need-a-regulator-for-a-natural-gas-grill/",
        "https://griddleking.com/what-should-i-name-my-smoker/",
        "https://griddleking.com/pellet-smoker-vs-stick-burner/",
        "https://griddleking.com/z-grills-vs-pit-boss-pellet-grill-showdown/",
        "https://griddleking.com/can-you-build-in-a-weber-genesis/"
    ]
    
    print("="*60)
    print("SEO FIX VERIFICATION")
    print("="*60)
    
    for url in urls_to_check:
        verify_url(url)
        print("-" * 60)
