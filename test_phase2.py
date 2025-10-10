#!/usr/bin/env python3
"""
Test Phase 2: Dual Data Input (GSC + GA4)
"""

import os
import sys
import tempfile
from datetime import datetime

def test_dataprocessor_gsc_only():
    """Test DataProcessor with GSC data only (backward compatibility)"""
    print("\n" + "="*60)
    print("TEST 1: DataProcessor with GSC Only")
    print("="*60)
    
    from multi_site_content_agent import DataProcessor
    
    # Create a mock GSC CSV
    import pandas as pd
    
    gsc_data = {
        'page': ['https://example.com/page1', 'https://example.com/page2', 'https://example.com/page3'],
        'query': ['best griddles', 'outdoor cooking', 'photography tips'],
        'clicks': [100, 50, 75],
        'impressions': [1000, 500, 800],
        'ctr': [0.10, 0.10, 0.09],
        'position': [5.2, 8.3, 6.1]
    }
    
    df = pd.DataFrame(gsc_data)
    
    # Save to temp CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        gsc_path = f.name
    
    try:
        # Test loading
        processor = DataProcessor(gsc_path)
        print(f"✓ Created DataProcessor with GSC path")
        
        # Test load_gsc
        gsc_df = processor.load_gsc()
        print(f"✓ load_gsc() returned {len(gsc_df)} rows")
        assert len(gsc_df) == 3
        assert 'clicks' in gsc_df.columns
        assert 'impressions' in gsc_df.columns
        
        # Test backward compatibility (load() method)
        df2 = processor.load()
        print(f"✓ load() method works (backward compatible)")
        assert len(df2) == 3
        
        return True
        
    finally:
        os.unlink(gsc_path)


def test_dataprocessor_ga4_loading():
    """Test DataProcessor GA4 data loading"""
    print("\n" + "="*60)
    print("TEST 2: DataProcessor with GA4")
    print("="*60)
    
    from multi_site_content_agent import DataProcessor
    import pandas as pd
    
    # Create mock GA4 CSV
    ga4_data = {
        'page': ['https://example.com/page1', 'https://example.com/page2'],
        'sessions': [500, 300],
        'engagement_rate': ['65%', '72%'],  # Test percentage format
        'avg_engagement_time': [120, 95],
        'bounce_rate': [35.5, 28.2],  # Already decimal
        'conversions': [10, 15]
    }
    
    df = pd.DataFrame(ga4_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        ga4_path = f.name
    
    try:
        # Test loading GA4 only
        processor = DataProcessor('dummy.csv', ga4_path=ga4_path)
        print(f"✓ Created DataProcessor with GA4 path")
        
        # Test load_ga4
        ga4_df = processor.load_ga4()
        print(f"✓ load_ga4() returned {len(ga4_df)} rows")
        assert len(ga4_df) == 2
        
        # Check normalization
        assert 'page' in ga4_df.columns
        assert 'sessions' in ga4_df.columns
        assert 'engagement_rate' in ga4_df.columns
        print(f"✓ Columns normalized correctly")
        
        # Check percentage conversion
        assert ga4_df['engagement_rate'].iloc[0] == 0.65
        assert ga4_df['engagement_rate'].iloc[1] == 0.72
        print(f"✓ Percentages converted to decimals (65% → 0.65)")
        
        # Check numeric types
        assert pd.api.types.is_numeric_dtype(ga4_df['sessions'])
        assert pd.api.types.is_numeric_dtype(ga4_df['engagement_rate'])
        print(f"✓ Numeric columns have correct types")
        
        return True
        
    finally:
        os.unlink(ga4_path)


def test_dataprocessor_merge():
    """Test merging GSC and GA4 data"""
    print("\n" + "="*60)
    print("TEST 3: Merge GSC + GA4 Data")
    print("="*60)
    
    from multi_site_content_agent import DataProcessor
    import pandas as pd
    
    # Create GSC data
    gsc_data = {
        'page': [
            'https://example.com/page1/',  # With trailing slash
            'https://example.com/page2?utm=test',  # With query params
            'https://example.com/page3'
        ],
        'query': ['query1', 'query2', 'query3'],
        'clicks': [100, 50, 75],
        'impressions': [1000, 500, 800],
        'ctr': [0.10, 0.10, 0.09],
        'position': [5.2, 8.3, 6.1]
    }
    
    # Create GA4 data (URLs normalized differently)
    ga4_data = {
        'page': [
            'https://example.com/page1',  # No trailing slash
            'https://example.com/page2',  # No query params
        ],
        'sessions': [500, 300],
        'engagement_rate': [65, 72],  # Already as numbers
        'avg_engagement_time': [120, 95],
        'bounce_rate': [0.35, 0.28]
    }
    
    # Save to temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        pd.DataFrame(gsc_data).to_csv(f.name, index=False)
        gsc_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        pd.DataFrame(ga4_data).to_csv(f.name, index=False)
        ga4_path = f.name
    
    try:
        # Test merge
        processor = DataProcessor(gsc_path, ga4_path)
        print(f"✓ Created DataProcessor with both GSC and GA4 paths")
        
        merged_df = processor.merge_data()
        print(f"✓ merge_data() returned {len(merged_df)} rows")
        
        # Check merged data has all rows from GSC
        assert len(merged_df) == 3
        print(f"✓ All GSC rows preserved (left join)")
        
        # Check GSC columns present
        assert 'clicks' in merged_df.columns
        assert 'impressions' in merged_df.columns
        print(f"✓ GSC columns present")
        
        # Check GA4 columns present
        assert 'sessions' in merged_df.columns
        assert 'engagement_rate' in merged_df.columns
        print(f"✓ GA4 columns present")
        
        # Check URL normalization worked
        # page1 should have GA4 data (matched despite trailing slash)
        page1_row = merged_df[merged_df['page'] == 'https://example.com/page1/'].iloc[0]
        assert not pd.isna(page1_row['sessions'])
        assert page1_row['sessions'] == 500
        print(f"✓ URL normalization worked (trailing slashes handled)")
        
        # page2 should have GA4 data (matched despite query params)
        page2_row = merged_df[merged_df['page'] == 'https://example.com/page2?utm=test'].iloc[0]
        assert not pd.isna(page2_row['sessions'])
        assert page2_row['sessions'] == 300
        print(f"✓ URL normalization worked (query params handled)")
        
        # page3 should have null GA4 data (no match)
        page3_row = merged_df[merged_df['page'] == 'https://example.com/page3'].iloc[0]
        assert pd.isna(page3_row['sessions'])
        print(f"✓ Unmatched GSC rows have null GA4 data")
        
        return True
        
    finally:
        os.unlink(gsc_path)
        os.unlink(ga4_path)


def test_backward_compatibility():
    """Test that GSCProcessor alias still works"""
    print("\n" + "="*60)
    print("TEST 4: Backward Compatibility (GSCProcessor alias)")
    print("="*60)
    
    from multi_site_content_agent import GSCProcessor, DataProcessor
    import pandas as pd
    
    # Create mock GSC CSV
    gsc_data = {
        'page': ['https://example.com/page1'],
        'query': ['test query'],
        'clicks': [100],
        'impressions': [1000],
        'ctr': [0.10],
        'position': [5.2]
    }
    
    df = pd.DataFrame(gsc_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        gsc_path = f.name
    
    try:
        # Test that GSCProcessor is an alias
        assert GSCProcessor is DataProcessor
        print(f"✓ GSCProcessor is DataProcessor (same class)")
        
        # Test using old name
        processor = GSCProcessor(gsc_path)
        gsc_df = processor.load()
        print(f"✓ GSCProcessor alias works (backward compatible)")
        assert len(gsc_df) == 1
        
        return True
        
    finally:
        os.unlink(gsc_path)


def test_ga4_column_variations():
    """Test GA4 handles various column name formats"""
    print("\n" + "="*60)
    print("TEST 5: GA4 Column Name Variations")
    print("="*60)
    
    from multi_site_content_agent import DataProcessor
    import pandas as pd
    
    # Test various column name formats
    ga4_data = {
        'Landing Page': ['https://example.com/page1'],  # Space and capitals
        'Sessions': [500],
        'Engagement rate': ['65%'],  # Space in name
        'Average Engagement Time': [120],  # Multiple spaces
        'Bounce Rate': ['35.5%'],
    }
    
    df = pd.DataFrame(ga4_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        ga4_path = f.name
    
    try:
        processor = DataProcessor('dummy.csv', ga4_path=ga4_path)
        ga4_df = processor.load_ga4()
        
        print(f"✓ Loaded GA4 with various column formats")
        
        # Check normalization
        assert 'page' in ga4_df.columns  # Landing Page → page
        assert 'sessions' in ga4_df.columns  # Sessions → sessions
        assert 'engagement_rate' in ga4_df.columns  # Engagement rate → engagement_rate
        assert 'avg_engagement_time' in ga4_df.columns  # Average Engagement Time → avg_engagement_time
        print(f"✓ Column names normalized correctly")
        
        return True
        
    finally:
        os.unlink(ga4_path)


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PHASE 2: Dual Data Input (GSC + GA4) Tests")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Run all tests
        tests = [
            ("DataProcessor with GSC Only", test_dataprocessor_gsc_only),
            ("DataProcessor with GA4", test_dataprocessor_ga4_loading),
            ("Merge GSC + GA4 Data", test_dataprocessor_merge),
            ("Backward Compatibility", test_backward_compatibility),
            ("GA4 Column Variations", test_ga4_column_variations),
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
            print("\n🎉 All Phase 2 tests passed!")
            print("\nPhase 2 is complete and ready for Phase 3.")
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
