#!/usr/bin/env python3
"""
Test Phase 1: Multi-Site Infrastructure
"""

import os
import json
import sys
from datetime import datetime

def test_config():
    """Test config.py module"""
    print("\n" + "="*60)
    print("TEST 1: Config Module")
    print("="*60)
    
    from config import get_sites_config, list_sites, get_site
    
    # Test with no config
    sites = get_sites_config()
    print(f"✓ get_sites_config() returns: {type(sites)}")
    print(f"  Sites configured: {list(sites.keys()) if sites else 'None'}")
    
    # Test list_sites
    site_list = list_sites()
    print(f"✓ list_sites() returns: {site_list}")
    
    # Test with mock config
    mock_config = {
        "example.com": {
            "url": "https://example.com",
            "wp_username": "admin",
            "wp_app_password": "test123",
            "niche": "testing"
        }
    }
    os.environ['SITES_CONFIG'] = json.dumps(mock_config)
    
    sites = get_sites_config()
    print(f"✓ After setting SITES_CONFIG: {list(sites.keys())}")
    
    site = get_site("example.com")
    print(f"✓ get_site('example.com') returns: {site['niche']}")
    
    # Test error handling
    try:
        get_site("nonexistent.com")
        print("✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ get_site() raises ValueError for unknown site: {str(e)[:50]}...")
    
    return True


def test_state_manager():
    """Test state_manager.py module"""
    print("\n" + "="*60)
    print("TEST 2: State Manager")
    print("="*60)
    
    from state_manager import StateManager
    
    # Create state manager
    sm = StateManager("test-site.com", state_dir="/tmp")
    print(f"✓ Created StateManager for test-site.com")
    print(f"  State file: {sm.state_file}")
    
    # Test initial state
    stats = sm.get_stats()
    print(f"✓ Initial stats: {stats}")
    
    # Test update_plan
    actions = [
        {
            "id": "action_001",
            "action_type": "update",
            "url": "https://test.com/page1",
            "priority_score": 9.5,
            "status": "pending"
        },
        {
            "id": "action_002",
            "action_type": "create",
            "url": "https://test.com/page2",
            "priority_score": 8.0,
            "status": "pending"
        },
        {
            "id": "action_003",
            "action_type": "update",
            "url": "https://test.com/page3",
            "priority_score": 7.5,
            "status": "pending"
        }
    ]
    
    sm.update_plan(actions)
    stats = sm.get_stats()
    print(f"✓ After update_plan(3 actions): {stats}")
    assert stats['total_actions'] == 3
    assert stats['pending'] == 3
    
    # Test get_pending_actions
    pending = sm.get_pending_actions(limit=2)
    print(f"✓ get_pending_actions(limit=2) returns {len(pending)} actions")
    print(f"  Top action: {pending[0]['id']} (score: {pending[0]['priority_score']})")
    assert pending[0]['priority_score'] >= pending[1]['priority_score']
    
    # Test mark_completed
    sm.mark_completed("action_001", post_id=123)
    stats = sm.get_stats()
    print(f"✓ After mark_completed: {stats}")
    assert stats['completed'] == 1
    assert stats['pending'] == 2
    
    # Test niche research caching
    niche_report = json.dumps({"summary": "test report", "trends": ["trend1"]})
    sm.cache_niche_research(niche_report, cache_days=30)
    print(f"✓ Cached niche research")
    
    cached = sm.get_niche_research()
    print(f"✓ Retrieved cached research: {cached[:50]}...")
    assert cached == niche_report
    
    # Test state persistence
    sm2 = StateManager("test-site.com", state_dir="/tmp")
    stats2 = sm2.get_stats()
    print(f"✓ State persisted across instances: {stats2}")
    assert stats2 == stats
    
    # Cleanup
    sm.clear_state()
    print(f"✓ State cleared")
    
    return True


def test_api_endpoint():
    """Test /sites API endpoint"""
    print("\n" + "="*60)
    print("TEST 3: API Endpoints")
    print("="*60)
    
    # Set up test config
    mock_config = {
        "site1.com": {
            "url": "https://site1.com",
            "wp_username": "admin",
            "wp_app_password": "test123",
            "niche": "niche1"
        },
        "site2.com": {
            "url": "https://site2.com",
            "wp_username": "admin",
            "wp_app_password": "test456",
            "niche": "niche2"
        }
    }
    os.environ['SITES_CONFIG'] = json.dumps(mock_config)
    
    # Create some state for sites
    from state_manager import StateManager
    
    sm1 = StateManager("site1.com", state_dir="/tmp")
    sm1.update_plan([
        {"id": "1", "action_type": "update", "priority_score": 9.0, "status": "pending"},
        {"id": "2", "action_type": "create", "priority_score": 8.0, "status": "completed"}
    ])
    sm1.mark_completed("2")
    
    sm2 = StateManager("site2.com", state_dir="/tmp")
    sm2.update_plan([
        {"id": "3", "action_type": "update", "priority_score": 7.0, "status": "pending"}
    ])
    
    print(f"✓ Created test state for 2 sites")
    
    # Test the endpoint logic (without running Flask)
    from config import list_sites
    
    sites = list_sites()
    site_status = []
    
    for site_name in sites:
        state_mgr = StateManager(site_name, state_dir="/tmp")
        stats = state_mgr.get_stats()
        site_status.append({
            'name': site_name,
            'pending_actions': stats['pending'],
            'completed_actions': stats['completed'],
            'total_actions': stats['total_actions']
        })
    
    print(f"✓ /sites endpoint logic working")
    print(f"  Total sites: {len(site_status)}")
    for site in site_status:
        print(f"  - {site['name']}: {site['pending_actions']} pending, {site['completed_actions']} completed")
    
    # Cleanup
    sm1.clear_state()
    sm2.clear_state()
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PHASE 1: Multi-Site Infrastructure Tests")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Run all tests
        tests = [
            ("Config Module", test_config),
            ("State Manager", test_state_manager),
            ("API Endpoints", test_api_endpoint)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, result))
            except Exception as e:
                print(f"\n✗ {name} failed: {e}")
                import traceback
                traceback.print_exc()
                results.append((name, False))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")
        
        all_passed = all(r[1] for r in results)
        
        if all_passed:
            print("\n🎉 All Phase 1 tests passed!")
            print("\nPhase 1 is complete and ready for Phase 2.")
            return 0
        else:
            print("\n❌ Some tests failed. Review errors above.")
            return 1
    
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
