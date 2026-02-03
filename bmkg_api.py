"""
Module untuk mengambil data cuaca dari API BMKG
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import time


class BMKGWeatherAPI:
    """Class untuk berinteraksi dengan API BMKG"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_weather_data(self, city_code: str) -> Optional[Dict]:
        """
        Mengambil data prakiraan cuaca dari API BMKG
        
        Args:
            city_code: Kode wilayah tingkat IV (kelurahan/desa)
            
        Returns:
            Dictionary berisi data cuaca atau None jika gagal
        """
        try:
            url = f"{self.base_url}?adm4={city_code}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and 'data' in data and len(data['data']) > 0:
                # Extract weather data from nested structure
                weather_list = []
                if 'cuaca' in data['data'][0]:
                    # Flatten the nested array structure
                    for day_data in data['data'][0]['cuaca']:
                        if isinstance(day_data, list):
                            weather_list.extend(day_data)
                
                # Validate that weather_list has data
                if not weather_list:
                    location_info = data['data'][0].get('lokasi', {})
                    location_name = location_info.get('kotkab', 'Unknown')
                    print(f"⚠️  Data cuaca tidak tersedia untuk {location_name} (kode: {city_code})")
                    print(f"   API mengembalikan array cuaca kosong. Wilayah ini mungkin tidak didukung BMKG.")
                    return None
                    
                return weather_list
            else:
                print(f"Data tidak ditemukan untuk kode: {city_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error mengambil data dari API: {e}")
            return None
        except ValueError as e:
            print(f"Error parsing JSON: {e}")
            return None
    
    def find_weather_at_time(self, weather_data: list, target_hour: int, timezone_offset: int) -> Optional[Dict]:
        """
        Mencari data cuaca pada jam tertentu (waktu lokal)
        
        Args:
            weather_data: List data prakiraan cuaca
            target_hour: Jam target (waktu lokal)
            timezone_offset: Offset timezone (7 untuk WIB, 8 untuk WITA, 9 untuk WIT)
            
        Returns:
            Dictionary data cuaca pada jam tersebut atau yang paling mendekati
        """
        if not weather_data:
            return None
        
        closest_weather = None
        min_diff = float('inf')
        
        for weather in weather_data:
            try:
                # Parse local datetime
                local_dt_str = weather.get('local_datetime', '')
                local_dt = datetime.strptime(local_dt_str, '%Y-%m-%d %H:%M:%S')
                
                # Hitung perbedaan jam
                hour_diff = abs(local_dt.hour - target_hour)
                
                # Jika menemukan yang lebih dekat
                if hour_diff < min_diff:
                    min_diff = hour_diff
                    closest_weather = weather
                
                # Jika menemukan exact match, langsung return
                if hour_diff == 0:
                    break
                    
            except (ValueError, KeyError) as e:
                continue
        
        return closest_weather
    
    def get_city_weather(self, city_code: str, target_hour: int, timezone_offset: int) -> Optional[Dict]:
        """
        Mengambil data cuaca untuk kota pada jam tertentu
        
        Args:
            city_code: Kode wilayah kota
            target_hour: Jam target (waktu lokal)
            timezone_offset: Offset timezone
            
        Returns:
            Dictionary berisi data cuaca yang dibutuhkan
        """
        # Ambil data dari API
        weather_data = self.get_weather_data(city_code)
        
        if not weather_data:
            return None
        
        # Cari data pada jam yang ditentukan
        weather_at_time = self.find_weather_at_time(weather_data, target_hour, timezone_offset)
        
        if not weather_at_time:
            # Jika tidak ada, gunakan data pertama
            weather_at_time = weather_data[0]
        
        # Format data yang akan dikembalikan
        return {
            'datetime': weather_at_time.get('local_datetime', ''),
            'temperature': weather_at_time.get('t', 0),
            'humidity': weather_at_time.get('hu', 0),
            'weather': weather_at_time.get('weather_desc', ''),
            'wind_speed': weather_at_time.get('ws', 0),
            'wind_direction': weather_at_time.get('wd', ''),
            'cloud_cover': weather_at_time.get('tcc', 0),
            'visibility': weather_at_time.get('vs_text', '')
        }


def fetch_city_weather(city_code: str, timezone_offset: int, target_hour: int = 6) -> Optional[Dict]:
    """
    Mengambil data cuaca untuk satu kota
    
    Args:
        city_code: Kode wilayah kota
        timezone_offset: Offset timezone (7 untuk WIB, 8 untuk WITA, 9 untuk WIT)
        target_hour: Jam target (default jam 6 pagi)
        
    Returns:
        Dictionary data cuaca atau None jika gagal
    """
    from config_db import BMKG_API_BASE_URL
    
    api = BMKGWeatherAPI(BMKG_API_BASE_URL)
    return api.get_city_weather(city_code, target_hour, timezone_offset)


def fetch_all_cities_weather(city_configs: Dict, auto_replace_failed: bool = True) -> Dict[str, Dict]:
    """
    Mengambil data cuaca untuk semua kota dengan auto-replacement untuk kota yang gagal
    
    Args:
        city_configs: Dictionary konfigurasi kota dari config_db.py
        auto_replace_failed: Jika True, otomatis ganti kota yang gagal dengan kota lain dari timezone sama
        
    Returns:
        Dictionary dengan nama kota sebagai key dan data cuaca sebagai value
    """
    from config_db import BMKG_API_BASE_URL
    
    DEFAULT_TARGET_HOUR = 6  # Default jam 6 pagi
    api = BMKGWeatherAPI(BMKG_API_BASE_URL)
    results = {}
    failed_cities = []
    
    for city_name, config in city_configs.items():
        print(f"Mengambil data cuaca untuk {city_name}...")
        
        # Gunakan jam 6 pagi untuk semua kota
        target_hour = DEFAULT_TARGET_HOUR
        weather_data = api.get_city_weather(
            config['code'],
            target_hour,
            config['timezone_offset']
        )
        
        if weather_data:
            results[city_name] = {
                **weather_data,
                'timezone': config['timezone'],
                'target_hour': target_hour
            }
            print(f"✓ Data {city_name} berhasil diambil")
        else:
            print(f"✗ Gagal mengambil data {city_name} - Data tidak tersedia dari API BMKG")
            failed_cities.append({'name': city_name, 'timezone': config['timezone'], 'timezone_offset': config['timezone_offset']})
        
        # Rate limiting - tunggu sebentar antar request
        time.sleep(1.5)
    
    # Auto-replacement untuk kota yang gagal
    if auto_replace_failed and failed_cities:
        try:
            from city_selector_db import CitySelector
            
            print(f"\n⚙️  Auto-replacement: {len(failed_cities)} kota gagal, mencari pengganti...")
            selector = CitySelector()
            selector.connect()
            
            # Track kota yang sudah dicoba untuk menghindari loop
            attempted_cities = set(city_configs.keys())
            
            for failed_city in failed_cities:
                timezone = failed_city['timezone']
                timezone_offset = failed_city['timezone_offset']
                max_replacement_tries = 5
                
                for attempt in range(max_replacement_tries):
                    # Pilih kota random dari timezone yang sama
                    replacement_cities = selector.db.get_random_cities(1, timezone)
                    
                    if not replacement_cities:
                        print(f"⚠️  Tidak ada kota pengganti untuk {timezone}")
                        break
                    
                    replacement = replacement_cities[0]
                    replacement_name = replacement['name']
                    
                    # Skip jika kota sudah pernah dicoba
                    if replacement_name in attempted_cities:
                        continue
                    
                    attempted_cities.add(replacement_name)
                    
                    print(f"  🔄 Mencoba {replacement_name} sebagai pengganti {failed_city['name']}...")
                    
                    # Coba ambil data cuaca untuk kota pengganti
                    weather_data = api.get_city_weather(
                        replacement['code'],
                        DEFAULT_TARGET_HOUR,
                        timezone_offset
                    )
                    
                    if weather_data:
                        results[replacement_name] = {
                            **weather_data,
                            'timezone': timezone,
                            'target_hour': DEFAULT_TARGET_HOUR
                        }
                        print(f"  ✓ {replacement_name} berhasil! Menggantikan {failed_city['name']}")
                        break
                    else:
                        print(f"  ✗ {replacement_name} juga gagal, mencoba kota lain...")
                    
                    time.sleep(1.5)
            
            selector.close()
            
        except Exception as e:
            print(f"⚠️  Error saat auto-replacement: {e}")
    
    return results
