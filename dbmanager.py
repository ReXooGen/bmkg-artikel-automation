"""
Database Management Utility
Tool untuk manage database wilayah Indonesia
"""

import argparse
import sys
from wilayah_db import WilayahDatabase
from city_selector_db import CitySelector


def cmd_import(args):
    """Import SQL file ke database"""
    print(f"Importing {args.sql_file} ke {args.db}...")
    db = WilayahDatabase(args.db)
    
    if db.import_from_sql(args.sql_file):
        print("✓ Import berhasil!")
        return 0
    else:
        print("✗ Import gagal!")
        return 1


def cmd_stats(args):
    """Show database statistics"""
    db = WilayahDatabase(args.db)
    db.connect()
    
    # Total wilayah
    db.cursor.execute("SELECT COUNT(*) FROM wilayah_2020")
    total = db.cursor.fetchone()[0]
    
    # By level
    db.cursor.execute("SELECT COUNT(*) FROM wilayah_2020 WHERE LENGTH(kode) = 2")
    provinsi = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM wilayah_2020 WHERE LENGTH(kode) = 5")
    kabkota = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM wilayah_2020 WHERE LENGTH(kode) = 8")
    kecamatan = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM wilayah_2020 WHERE LENGTH(kode) >= 13")
    kelurahan = db.cursor.fetchone()[0]
    
    # Kota (71/72)
    db.cursor.execute("""
        SELECT COUNT(*) FROM wilayah_2020 
        WHERE LENGTH(kode) = 5 AND (kode LIKE '%.71' OR kode LIKE '%.72')
    """)
    kota = db.cursor.fetchone()[0]
    
    print("="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    print(f"Total Wilayah      : {total:,}")
    print(f"  - Provinsi       : {provinsi}")
    print(f"  - Kabupaten/Kota : {kabkota}")
    print(f"    - Kota         : {kota}")
    print(f"  - Kecamatan      : {kecamatan}")
    print(f"  - Kelurahan/Desa : {kelurahan}")
    print("="*60)
    
    # Cities by timezone
    for tz in ['WIB', 'WITA', 'WIT']:
        cities = db.get_cities_by_timezone(tz)
        print(f"{tz:5s} Cities     : {len(cities)}")
    
    print("="*60)
    db.close()
    return 0


def cmd_search(args):
    """Search city by name"""
    db = WilayahDatabase(args.db)
    db.connect()
    
    city = db.get_city_by_name(args.name)
    
    if city:
        print(f"✓ Ditemukan:")
        print(f"  Nama     : {city['name']}")
        print(f"  Kode     : {city['code']}")
        print(f"  Timezone : {city['timezone']} (UTC+{city['timezone_offset']})")
        db.close()
        return 0
    else:
        print(f"✗ Kota '{args.name}' tidak ditemukan")
        db.close()
        return 1


def cmd_list(args):
    """List cities by timezone"""
    db = WilayahDatabase(args.db)
    db.connect()
    
    cities = db.get_cities_by_timezone(args.timezone)
    
    print(f"\n{'='*70}")
    print(f"KOTA {args.timezone} (Total: {len(cities)})")
    print(f"{'='*70}")
    
    for i, city in enumerate(cities, 1):
        print(f"{i:3d}. {city['name']:30s} {city['code']}")
    
    print(f"{'='*70}\n")
    db.close()
    return 0


def cmd_random(args):
    """Generate random cities"""
    selector = CitySelector(args.db)
    
    # Parse distribution
    if args.distribution:
        parts = args.distribution.split(',')
        wib = int(parts[0]) if len(parts) > 0 else None
        wita = int(parts[1]) if len(parts) > 1 else None
        wit = int(parts[2]) if len(parts) > 2 else None
        
        cities = selector.select_random_cities(
            total_cities=args.count,
            wib_count=wib,
            wita_count=wita,
            wit_count=wit
        )
    else:
        cities = selector.select_random_cities(total_cities=args.count)
    
    selector.print_selected_cities()
    
    # Export to Python dict format jika diminta
    if args.export:
        print(f"\n# Export ke Python dict:")
        print("CITY_CODES = {")
        for city_name, city_data in cities.items():
            print(f"    \"{city_name}\": {{")
            print(f"        \"code\": \"{city_data['code']}\",")
            print(f"        \"timezone\": \"{city_data['timezone']}\",")
            print(f"        \"timezone_offset\": {city_data['timezone_offset']}")
            print(f"    }},")
        print("}")
    
    selector.close()
    return 0


def cmd_query(args):
    """Execute raw SQL query"""
    db = WilayahDatabase(args.db)
    db.connect()
    
    try:
        db.cursor.execute(args.sql)
        results = db.cursor.fetchall()
        
        print(f"\nResults: {len(results)} rows\n")
        for row in results[:50]:  # Limit 50 rows
            print(row)
        
        if len(results) > 50:
            print(f"\n... and {len(results) - 50} more rows")
        
        db.close()
        return 0
    except Exception as e:
        print(f"✗ Query error: {e}")
        db.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Database Management untuk Wilayah Indonesia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import SQL file
  python dbmanager.py import wilayah_2020.sql
  
  # Show statistics
  python dbmanager.py stats
  
  # Search city
  python dbmanager.py search Jakarta
  
  # List cities by timezone
  python dbmanager.py list WIB
  
  # Generate 10 random cities
  python dbmanager.py random -c 10
  
  # Generate with custom distribution (5 WIB, 3 WITA, 2 WIT)
  python dbmanager.py random -c 10 -d 5,3,2
  
  # Export to Python dict
  python dbmanager.py random -c 10 --export
  
  # Raw SQL query
  python dbmanager.py query "SELECT * FROM wilayah_2020 LIMIT 10"
        """
    )
    
    parser.add_argument(
        '--db',
        default='wilayah.db',
        help='Path to database file (default: wilayah.db)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Import command
    parser_import = subparsers.add_parser('import', help='Import SQL file')
    parser_import.add_argument('sql_file', help='SQL file to import')
    parser_import.set_defaults(func=cmd_import)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show database statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Search command
    parser_search = subparsers.add_parser('search', help='Search city by name')
    parser_search.add_argument('name', help='City name to search')
    parser_search.set_defaults(func=cmd_search)
    
    # List command
    parser_list = subparsers.add_parser('list', help='List cities by timezone')
    parser_list.add_argument('timezone', choices=['WIB', 'WITA', 'WIT'], help='Timezone')
    parser_list.set_defaults(func=cmd_list)
    
    # Random command
    parser_random = subparsers.add_parser('random', help='Generate random cities')
    parser_random.add_argument('-c', '--count', type=int, default=10, help='Number of cities')
    parser_random.add_argument('-d', '--distribution', help='Distribution (WIB,WITA,WIT), e.g., 5,3,2')
    parser_random.add_argument('--export', action='store_true', help='Export to Python dict format')
    parser_random.set_defaults(func=cmd_random)
    
    # Query command
    parser_query = subparsers.add_parser('query', help='Execute raw SQL query')
    parser_query.add_argument('sql', help='SQL query to execute')
    parser_query.set_defaults(func=cmd_query)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
