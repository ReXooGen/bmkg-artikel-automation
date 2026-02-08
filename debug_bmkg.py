import requests

url = "https://www.bmkg.go.id/cuaca/potensi-cuaca-ekstrem"
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, verify=False)
    print(response.text[:2000])
except Exception as e:
    print(f"Error: {e}")
