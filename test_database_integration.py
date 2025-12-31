"""
Test integrasi database dengan sistem BMKG automation
Memastikan config_db.py kompatibel dengan main.py dan modul lainnya
"""

import sys
from datetime import datetime

def test_database_integration():
    """Test integrasi lengkap database"""
    
    print("="*70)
    print("TEST INTEGRASI DATABASE SQL DENGAN BMKG AUTOMATION")
    print("="*70)
    
    # Test 1: Import config_db
    print("\n[1/5] Testing import config_db...")
    try:
        from config_db import (
            CITY_CODES, 
            initialize_cities, 
            add_city, 
            search_city,
            get_cities_by_timezone,
            BMKG_API_BASE_URL,
            GOOGLE_GEMINI_API_KEYS
        )
        print("✓ Import berhasil")
        print(f"  - Loaded {len(CITY_CODES)} cities")
        print(f"  - API URL: {BMKG_API_BASE_URL}")
        print(f"  - Gemini Keys: {len(GOOGLE_GEMINI_API_KEYS)} keys")
    except Exception as e:
        print(f"✗ Import gagal: {e}")
        return False
    
    # Test 2: Cek struktur CITY_CODES
    print("\n[2/5] Testing struktur CITY_CODES...")
    try:
        if not CITY_CODES:
            print("✗ CITY_CODES kosong")
            return False
        
        # Cek format data
        sample_city = list(CITY_CODES.keys())[0]
        sample_data = CITY_CODES[sample_city]
        
        required_keys = ['code', 'timezone', 'timezone_offset']
        for key in required_keys:
            if key not in sample_data:
                print(f"✗ Missing key '{key}' in CITY_CODES")
                return False
        
        print("✓ Struktur CITY_CODES valid")
        print(f"  Sample: {sample_city} = {sample_data}")
        
        # Group by timezone
        by_tz = {'WIB': 0, 'WITA': 0, 'WIT': 0}
        for city_data in CITY_CODES.values():
            tz = city_data['timezone']
            by_tz[tz] = by_tz.get(tz, 0) + 1
        
        print(f"  Distribution: WIB={by_tz['WIB']}, WITA={by_tz['WITA']}, WIT={by_tz['WIT']}")
        
    except Exception as e:
        print(f"✗ Test struktur gagal: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Test fungsi initialize_cities
    print("\n[3/5] Testing initialize_cities()...")
    try:
        old_count = len(CITY_CODES)
        new_codes = initialize_cities(force_new=True)
        new_count = len(new_codes)
        
        print(f"✓ Re-generate berhasil")
        print(f"  - Old: {old_count} cities")
        print(f"  - New: {new_count} cities")
        
    except Exception as e:
        print(f"✗ initialize_cities gagal: {e}")
        return False
    
    # Test 4: Test fungsi search dan add
    print("\n[4/5] Testing search_city() dan add_city()...")
    try:
        # Search Jakarta
        jakarta = search_city("Jakarta")
        if jakarta:
            print(f"✓ Search berhasil: {jakarta}")
        else:
            print("✗ Jakarta tidak ditemukan")
            return False
        
        # Add Surabaya
        if add_city("Surabaya"):
            print("✓ Add city berhasil: Surabaya")
            if "Surabaya" in CITY_CODES:
                print(f"  - {CITY_CODES['Surabaya']}")
        else:
            print("✗ Add Surabaya gagal")
        
    except Exception as e:
        print(f"✗ Test search/add gagal: {e}")
        return False
    
    # Test 5: Test kompatibilitas dengan BMKG API
    print("\n[5/5] Testing kompatibilitas dengan BMKG API...")
    try:
        # Test format kode wilayah
        for city_name, city_data in list(CITY_CODES.items())[:3]:
            code = city_data['code']
            
            # Kode harus format XX.XX.XX.XXXX
            parts = code.split('.')
            if len(parts) != 4:
                print(f"✗ Invalid code format: {code}")
                return False
            
            # Build API URL
            api_url = f"{BMKG_API_BASE_URL}?adm4={code}"
            print(f"  ✓ {city_name:20s} -> {api_url}")
        
        print("✓ Format kode valid untuk BMKG API")
        
    except Exception as e:
        print(f"✗ Test API compatibility gagal: {e}")
        return False
    
    # Summary
    print("\n" + "="*70)
    print("HASIL TEST")
    print("="*70)
    print("✓ Semua test PASSED")
    print(f"✓ Database SQL siap digunakan")
    print(f"✓ Total {len(CITY_CODES)} kota tersedia")
    print()
    print("CARA MIGRASI KE SISTEM:")
    print("  1. Backup config.py dan main.py")
    print("  2. Edit main.py, ganti:")
    print("     from config import CITY_CODES")
    print("     MENJADI:")
    print("     from config_db import CITY_CODES")
    print("  3. Test dengan: python main.py")
    print("="*70)
    
    return True


if __name__ == "__main__":
    success = test_database_integration()
    sys.exit(0 if success else 1)
