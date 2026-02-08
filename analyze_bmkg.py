import requests
from bs4 import BeautifulSoup

url = "https://www.bmkg.go.id/cuaca/potensi-cuaca-ekstrem"
try:
    response = requests.get(url, verify=False) # Skip verify for now to avoid SSL issues in some envs
    soup = BeautifulSoup(response.content, 'html.parser')

    print("--- TABS ANALYSIS ---")
    # specific to bootstrap tabs often used
    tabs = soup.find_all(class_='nav-tabs')
    if tabs:
        for tab in tabs:
            print(tab.prettify()[:500])
    
    # Check for specific "Hari Ini", "Besok" text
    print("\n--- TEXT SEARCH ---")
    headers = soup.find_all(string=["Hari Ini", "Besok", "Lusa"])
    for h in headers:
        parent = h.parent
        print(f"Found '{h}': Tag={parent.name} Class={parent.get('class')} ID={parent.get('id')}")

    print("\n--- MAP ANALYSIS ---")
    maps = soup.find_all(id='map')
    if maps:
        print("Found element with id='map'")
    
    # check for images that might be the maps
    imgs = soup.find_all('img')
    print(f"Found {len(imgs)} images.")
    for img in imgs:
        src = img.get('src', '')
        if 'cuaca' in src or 'pce' in src.lower(): # pce = potensi cuaca ekstrem?
             print(f"Potential Map Image: {src}")

    print("\n--- TABLE ANALYSIS ---")
    tables = soup.find_all('table')
    for i, table in enumerate(tables):
        print(f"Table {i}:")
        # Print headers
        headers = table.find_all('th')
        print(f"Headers: {[h.get_text(strip=True) for h in headers]}")

except Exception as e:
    print(f"Error: {e}")
