from wilayah_db import WilayahDatabase

db = WilayahDatabase()
db.connect()

print("="*60)
print("TEST: get_cities_by_keyword('Surabaya')")
print("="*60)
cities = db.get_cities_by_keyword('Surabaya', limit=5)
for city in cities:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")

print("\n" + "="*60)
print("TEST: get_cities_by_keyword('Jakarta')")
print("="*60)
cities = db.get_cities_by_keyword('Jakarta', limit=5)
for city in cities:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")

print("\n" + "="*60)
print("TEST: get_cities_by_keyword('Bandung')")
print("="*60)
cities = db.get_cities_by_keyword('Bandung', limit=5)
for city in cities:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")

print("\n" + "="*60)
print("TEST: get_city_by_name('Surabaya')")
print("="*60)
city = db.get_city_by_name('Surabaya')
if city:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")
else:
    print("  Not found!")

print("\n" + "="*60)
print("TEST: get_city_by_name('Jakarta')")
print("="*60)
city = db.get_city_by_name('Jakarta')
if city:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")
else:
    print("  Not found!")

print("\n" + "="*60)
print("TEST: get_city_by_name('Bandung')")
print("="*60)
city = db.get_city_by_name('Bandung')
if city:
    print(f"  {city['name']} - {city['code']} ({city['timezone']})")
else:
    print("  Not found!")

db.close()
