from city_selector_db import CitySelector

print("="*60)
print("TEST: Add Specific Cities")
print("="*60)

selector = CitySelector()
selector.clear_selected_cities()

# Test add cities
print("\n1. Adding Surabaya...")
result = selector.add_specific_city('Surabaya')
print(f"   Result: {result}")

print("\n2. Adding Jakarta...")
result = selector.add_specific_city('Jakarta')
print(f"   Result: {result}")

print("\n3. Adding Bandung...")
result = selector.add_specific_city('Bandung')
print(f"   Result: {result}")

print("\n4. Get selected cities:")
selected = selector.get_selected_cities()
for name, info in selected.items():
    print(f"   {name} - {info['code']} ({info['timezone']})")

print("\n5. Add 1 random city to make total 4...")
selector.select_random_cities(total_cities=1)

print("\n6. Final selected cities:")
selected = selector.get_selected_cities()
for name, info in selected.items():
    print(f"   {name} - {info['code']} ({info['timezone']})")

print("\n" + "="*60)
print(f"Total: {len(selected)} cities")
print("="*60)

selector.close()
