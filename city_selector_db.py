"""
City selector dengan database - versi yang menggunakan SQLite database
Menggantikan city_selector.py dengan akses ke database wilayah
"""

import random
import os
from typing import Dict, Optional
from wilayah_db import WilayahDatabase


class CitySelector:
    """Class untuk memilih kota secara random dari database"""
    
    def __init__(self, db_path: str = "wilayah.db"):
        """
        Initialize city selector dengan database
        
        Args:
            db_path: Path ke database SQLite wilayah
        """
        # Adaptation for Vercel (Read-only System)
        if os.environ.get('VERCEL') == '1':
            # Use /tmp directory in Vercel
            self.db_path = os.path.join('/tmp', os.path.basename(db_path))
            print(f"Running in Vercel environment. Using database at: {self.db_path}")
        else:
            self.db_path = db_path

        self.db = WilayahDatabase(self.db_path)
        
        # Inisialisasi database jika belum ada
        if not os.path.exists(self.db_path):
            print("Database tidak ditemukan. Mengimport dari SQL...")
            self.db.import_from_sql("wilayah_2020.sql")
        
        self.db.connect()
        self.selected_cities = {}
    
    def connect(self):
        """Koneksi ke database (helper method untuk kompatibilitas)"""
        return self.db.connect()
    
    def select_random_cities(self, 
                           total_cities: int = 5,
                           wib_count: Optional[int] = None,
                           wita_count: Optional[int] = None, 
                           wit_count: Optional[int] = None) -> Dict[str, Dict]:
        """
        Pilih kota secara random dari database
        
        Args:
            total_cities: Total jumlah kota yang diinginkan (default: 5)
            wib_count: Jumlah kota WIB (None = otomatis)
            wita_count: Jumlah kota WITA (None = otomatis)
            wit_count: Jumlah kota WIT (None = otomatis)
        
        Returns:
            Dict dengan format: {"Nama Kota": {"code": "...", "timezone": "...", "timezone_offset": ...}}
        """
        # Clear selected cities terlebih dahulu
        self.selected_cities = {}
        
        # Jika tidak dispesifikasikan, bagi rata
        if wib_count is None and wita_count is None and wit_count is None:
            wib_count = total_cities // 2  # 50% WIB
            wita_count = total_cities // 3  # 33% WITA
            wit_count = total_cities - wib_count - wita_count  # Sisanya WIT
        
        # Pilih kota WIB
        if wib_count and wib_count > 0:
            cities_wib = self.db.get_random_cities(wib_count, 'WIB')
            for city in cities_wib:
                self.selected_cities[city['name']] = {
                    'code': city['code'],
                    'timezone': city['timezone'],
                    'timezone_offset': city['timezone_offset']
                }
        
        # Pilih kota WITA
        if wita_count and wita_count > 0:
            cities_wita = self.db.get_random_cities(wita_count, 'WITA')
            for city in cities_wita:
                self.selected_cities[city['name']] = {
                    'code': city['code'],
                    'timezone': city['timezone'],
                    'timezone_offset': city['timezone_offset']
                }
        
        # Pilih kota WIT
        if wit_count and wit_count > 0:
            cities_wit = self.db.get_random_cities(wit_count, 'WIT')
            for city in cities_wit:
                self.selected_cities[city['name']] = {
                    'code': city['code'],
                    'timezone': city['timezone'],
                    'timezone_offset': city['timezone_offset']
                }
        
        return self.selected_cities
    
    def add_specific_city(self, city_name: str, validate_api: bool = False) -> bool:
        """
        Tambahkan kota spesifik berdasarkan nama
        
        Args:
            city_name: Nama kota yang ingin ditambahkan
            validate_api: Jika True, validasi bahwa kota memiliki data di BMKG API
        
        Returns:
            True jika berhasil, False jika kota tidak ditemukan atau tidak ada data
        """
        city = self.db.get_city_by_name(city_name)
        if city:
            # Validasi API jika diminta
            if validate_api:
                if not self.validate_city_has_data(city['code']):
                    print(f"⚠️  {city['name']} ditemukan tapi tidak ada data cuaca di API BMKG")
                    return False
            
            self.selected_cities[city['name']] = {
                'code': city['code'],
                'timezone': city['timezone'],
                'timezone_offset': city['timezone_offset']
            }
            return True
        return False
    
    def validate_city_has_data(self, city_code: str) -> bool:
        """
        Validasi apakah kota memiliki data cuaca di API BMKG
        
        Args:
            city_code: Kode wilayah kota
            
        Returns:
            True jika ada data, False jika tidak ada
        """
        try:
            import requests
            url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={city_code}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and len(data['data']) > 0:
                    cuaca = data['data'][0].get('cuaca', [])
                    # Check if cuaca has actual data
                    weather_count = 0
                    if isinstance(cuaca, list):
                        for day in cuaca:
                            if isinstance(day, list):
                                weather_count += len(day)
                            else:
                                weather_count += 1
                    return weather_count > 0
            return False
        except Exception as e:
            print(f"Error validating city data: {e}")
            return False
    
    def get_selected_cities(self) -> Dict[str, Dict]:
        """Return kota yang sudah dipilih"""
        return self.selected_cities
    
    def print_selected_cities(self):
        """Print kota yang terpilih"""
        if not self.selected_cities:
            print("Belum ada kota yang dipilih")
            return
        
        print(f"\n{'='*60}")
        print(f"KOTA TERPILIH: {len(self.selected_cities)} kota")
        print(f"{'='*60}")
        
        # Group by timezone
        by_timezone = {'WIB': [], 'WITA': [], 'WIT': []}
        for city_name, city_info in self.selected_cities.items():
            by_timezone[city_info['timezone']].append((city_name, city_info))
        
        for tz in ['WIB', 'WITA', 'WIT']:
            if by_timezone[tz]:
                print(f"\n{tz} (UTC+{by_timezone[tz][0][1]['timezone_offset']}):")
                for city_name, city_info in by_timezone[tz]:
                    print(f"  - {city_name:20s} : {city_info['code']}")
        
        print(f"{'='*60}\n")
    
    def search_city(self, city_name: str) -> Optional[Dict]:
        """
        Cari kota spesifik di database (exact match atau contains)
        
        Args:
            city_name: Nama kota yang dicari
            
        Returns:
            Dict info kota atau None jika tidak ditemukan
        """
        results = self.search_cities(city_name, limit=1)
        return results[0] if results else None
    
    def search_cities(self, keyword: str, limit: int = 10) -> list:
        """
        Cari kota berdasarkan keyword
        
        Args:
            keyword: Keyword pencarian
            limit: Maksimal hasil yang dikembalikan
            
        Returns:
            List dict info kota
        """
        try:
            # Gunakan fungsi dari WilayahDatabase untuk search
            cities = self.db.get_cities_by_keyword(keyword, limit)
            return cities
        except Exception as e:
            print(f"Error searching cities: {e}")
            return []
    
    def count_cities_by_timezone(self) -> Dict[str, int]:
        """
        Hitung jumlah kota per timezone
        
        Returns:
            Dict dengan key timezone dan value jumlah kota
        """
        try:
            # Hitung per timezone menggunakan fungsi yang ada
            wib_cities = self.db.get_cities_by_timezone('WIB')
            wita_cities = self.db.get_cities_by_timezone('WITA')
            wit_cities = self.db.get_cities_by_timezone('WIT')
            
            result = {
                'WIB': len(wib_cities),
                'WITA': len(wita_cities),
                'WIT': len(wit_cities)
            }
            
            return result
        except Exception as e:
            print(f"Error counting cities: {e}")
            return {}
    
    def clear_selected_cities(self):
        """Hapus semua kota yang sudah dipilih"""
        self.selected_cities = {}
    
    def close(self):
        """Tutup koneksi database"""
        self.db.close()


# Contoh penggunaan
if __name__ == "__main__":
    print("City Selector dengan Database SQL")
    print("="*60)
    
    selector = CitySelector()
    
    # Pilih 10 kota random
    print("\n[1] Memilih 10 kota random...")
    cities = selector.select_random_cities(total_cities=10)
    selector.print_selected_cities()
    
    # Tambah kota spesifik
    print("\n[2] Menambah kota Jakarta...")
    if selector.add_specific_city("Jakarta"):
        print("✓ Jakarta berhasil ditambahkan")
    selector.print_selected_cities()
    
    # Pilih kota dengan distribusi custom
    print("\n[3] Memilih dengan distribusi custom (5 WIB, 3 WITA, 2 WIT)...")
    cities = selector.select_random_cities(
        total_cities=10,
        wib_count=5,
        wita_count=3, 
        wit_count=2
    )
    selector.print_selected_cities()
    
    selector.close()
    print("\nSelesai!")
