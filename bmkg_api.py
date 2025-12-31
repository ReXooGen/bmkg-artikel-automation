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


def fetch_all_cities_weather(city_configs: Dict) -> Dict[str, Dict]:
    """
    Mengambil data cuaca untuk semua kota
    
    Args:
        city_configs: Dictionary konfigurasi kota dari config_db.py
        
    Returns:
        Dictionary dengan nama kota sebagai key dan data cuaca sebagai value
    """
    from config_db import BMKG_API_BASE_URL
    
    DEFAULT_TARGET_HOUR = 6  # Default jam 6 pagi
    api = BMKGWeatherAPI(BMKG_API_BASE_URL)
    results = {}
    
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
            print(f"✗ Gagal mengambil data {city_name}")
        
        # Rate limiting - tunggu sebentar antar request
        time.sleep(1.5)
    
    return results
