"""
Modul untuk mengakses data wilayah dari database SQLite
Menggantikan hardcode city pool di config.py dengan query database
"""

import sqlite3
import random
import os
from typing import Dict, List, Optional


class WilayahDatabase:
    """Class untuk mengakses database wilayah Indonesia"""
    
    def __init__(self, db_path: str = "wilayah.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path ke file database SQLite
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Mapping timezone berdasarkan kode provinsi
        self.timezone_mapping = {
            # WIB (UTC+7)
            '11': ('WIB', 7),  # Aceh
            '12': ('WIB', 7),  # Sumatera Utara
            '13': ('WIB', 7),  # Sumatera Barat
            '14': ('WIB', 7),  # Riau
            '15': ('WIB', 7),  # Jambi
            '16': ('WIB', 7),  # Sumatera Selatan
            '17': ('WIB', 7),  # Bengkulu
            '18': ('WIB', 7),  # Lampung
            '19': ('WIB', 7),  # Kepulauan Bangka Belitung
            '21': ('WIB', 7),  # Kepulauan Riau
            '31': ('WIB', 7),  # DKI Jakarta
            '32': ('WIB', 7),  # Jawa Barat
            '33': ('WIB', 7),  # Jawa Tengah
            '34': ('WIB', 7),  # DI Yogyakarta
            '35': ('WIB', 7),  # Jawa Timur
            '36': ('WIB', 7),  # Banten
            '61': ('WIB', 7),  # Kalimantan Barat
            '62': ('WITA', 8), # Kalimantan Tengah
            '63': ('WITA', 8), # Kalimantan Selatan
            '64': ('WITA', 8), # Kalimantan Timur
            '65': ('WITA', 8), # Kalimantan Utara
            # WITA (UTC+8)
            '51': ('WITA', 8), # Bali
            '52': ('WITA', 8), # Nusa Tenggara Barat
            '53': ('WITA', 8), # Nusa Tenggara Timur
            '71': ('WITA', 8), # Sulawesi Utara
            '72': ('WITA', 8), # Sulawesi Tengah
            '73': ('WITA', 8), # Sulawesi Selatan
            '74': ('WITA', 8), # Sulawesi Tenggara
            '75': ('WITA', 8), # Gorontalo
            '76': ('WITA', 8), # Sulawesi Barat
            # WIT (UTC+9)
            '81': ('WIT', 9),  # Maluku
            '82': ('WIT', 9),  # Maluku Utara
            '91': ('WIT', 9),  # Papua
            '92': ('WIT', 9),  # Papua Barat
            '93': ('WIT', 9),  # Papua Selatan
            '94': ('WIT', 9),  # Papua Tengah
            '95': ('WIT', 9),  # Papua Pegunungan
            '96': ('WIT', 9),  # Papua Barat Daya
        }
    
    def connect(self):
        """Buka koneksi ke database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"Error koneksi database: {e}")
            return False
    
    def close(self):
        """Tutup koneksi database"""
        if self.conn:
            self.conn.close()
    
    def import_from_sql(self, sql_file: str = "wilayah_2020.sql"):
        """
        Import data dari file SQL ke SQLite database
        
        Args:
            sql_file: Path ke file SQL yang akan diimport
        """
        if not os.path.exists(sql_file):
            print(f"File {sql_file} tidak ditemukan")
            return False
        
        try:
            self.connect()
            
            print("Membaca file SQL...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Create table terlebih dahulu
            print("Membuat tabel wilayah_2020...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS wilayah_2020 (
                kode varchar(13) NOT NULL,
                nama varchar(100) DEFAULT NULL
            )
            """
            self.cursor.execute(create_table_sql)
            self.conn.commit()
            
            # Extract semua VALUES dari INSERT statements
            import re
            
            # Find all INSERT blocks
            insert_blocks = re.findall(
                r"INSERT INTO `wilayah_2020` \(`kode`, `nama`\) VALUES(.*?);",
                sql_content,
                re.DOTALL
            )
            
            print(f"Menemukan {len(insert_blocks)} blok INSERT...")
            
            # Extract individual value rows dari semua blocks
            all_values = []
            for block in insert_blocks:
                # Find all ('...', '...') patterns
                value_rows = re.findall(r"\('([^']*)',\s*'([^']*)'\)", block)
                all_values.extend(value_rows)
            
            print(f"Total {len(all_values)} baris data untuk diinsert...")
            
            # Prepare insert statement
            insert_sql = "INSERT OR IGNORE INTO wilayah_2020 (kode, nama) VALUES (?, ?)"
            
            # Insert data dalam batch
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(all_values), batch_size):
                batch_data = all_values[i:i+batch_size]
                self.cursor.executemany(insert_sql, batch_data)
                self.conn.commit()
                total_inserted += len(batch_data)
                
                # Show progress every 10k rows
                if total_inserted % 10000 == 0 or i + batch_size >= len(all_values):
                    print(f"Progress: {total_inserted}/{len(all_values)} baris...")
            
            print(f"✓ Import selesai! Total {total_inserted} baris data berhasil diimport.")
            
            # Verify
            self.cursor.execute("SELECT COUNT(*) FROM wilayah_2020")
            count = self.cursor.fetchone()[0]
            print(f"✓ Database berisi {count} wilayah")
            
            self.close()
            return True
            
        except Exception as e:
            print(f"✗ Error import SQL: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_timezone_info(self, kode: str) -> tuple:
        """
        Dapatkan timezone berdasarkan kode wilayah
        
        Args:
            kode: Kode wilayah (format: XX.XX.XX.XXXX)
        
        Returns:
            Tuple (timezone_name, timezone_offset)
        """
        prov_code = kode.split('.')[0]
        return self.timezone_mapping.get(prov_code, ('WIB', 7))
    
    def get_cities_by_timezone(self, timezone: str = 'WIB') -> List[Dict]:
        """
        Dapatkan list kota berdasarkan timezone
        
        Args:
            timezone: WIB, WITA, atau WIT
        
        Returns:
            List of dict dengan info kota
        """
        if not self.conn:
            self.connect()
        
        # Cari kode provinsi yang sesuai timezone
        prov_codes = [code for code, (tz, _) in self.timezone_mapping.items() 
                     if tz == timezone]
        
        cities = []
        
        for prov_code in prov_codes:
            # Query kota (level XX.YY dimana YY >= 71 untuk kota)
            # Includes: .71, .72, .73, .74, .75, .76, .77, .78, .79
            query = """
                SELECT kode, nama 
                FROM wilayah_2020 
                WHERE kode LIKE ? 
                AND LENGTH(kode) = 5
                AND CAST(SUBSTR(kode, 4, 2) AS INTEGER) >= 71
                AND nama LIKE 'KOTA %'
                ORDER BY nama
            """
            
            self.cursor.execute(query, (f"{prov_code}.%",))
            results = self.cursor.fetchall()
            
            for kode_kota, nama_kota in results:
                # Ambil kode kelurahan pertama dari kota ini
                query_kel = """
                    SELECT kode 
                    FROM wilayah_2020 
                    WHERE kode LIKE ? AND LENGTH(kode) >= 13
                    LIMIT 1
                """
                self.cursor.execute(query_kel, (f"{kode_kota}.%",))
                result_kel = self.cursor.fetchone()
                
                if result_kel:
                    tz_name, tz_offset = self.get_timezone_info(result_kel[0])
                    cities.append({
                        'name': nama_kota.replace('KAB. ', '').replace('KOTA ', '').title(),
                        'code': result_kel[0],
                        'timezone': tz_name,
                        'timezone_offset': tz_offset
                    })
        
        return cities
    
    def get_random_cities(self, count: int = 1, timezone: Optional[str] = None) -> List[Dict]:
        """
        Dapatkan kota random
        
        Args:
            count: Jumlah kota yang diinginkan
            timezone: Filter berdasarkan timezone (WIB/WITA/WIT), None untuk semua
        
        Returns:
            List of dict dengan info kota
        """
        if timezone:
            cities = self.get_cities_by_timezone(timezone)
        else:
            cities = []
            for tz in ['WIB', 'WITA', 'WIT']:
                cities.extend(self.get_cities_by_timezone(tz))
        
        if len(cities) <= count:
            return cities
        
        return random.sample(cities, count)
    
    def get_city_by_name(self, city_name: str) -> Optional[Dict]:
        """
        Cari kota berdasarkan nama
        
        Args:
            city_name: Nama kota yang dicari
        
        Returns:
            Dict info kota atau None jika tidak ditemukan
        """
        if not self.conn:
            self.connect()
        
        # Search case-insensitive
        query = """
            SELECT kode, nama 
            FROM wilayah_2020 
            WHERE UPPER(nama) LIKE UPPER(?) 
            AND LENGTH(kode) = 5
            AND CAST(SUBSTR(kode, 4, 2) AS INTEGER) >= 71
            AND nama LIKE 'KOTA %'
            LIMIT 1
        """
        
        self.cursor.execute(query, (f"%{city_name}%",))
        result = self.cursor.fetchone()
        
        if result:
            kode_kota, nama_kota = result
            
            # Ambil kode kelurahan pertama
            query_kel = """
                SELECT kode 
                FROM wilayah_2020 
                WHERE kode LIKE ? AND LENGTH(kode) >= 13
                LIMIT 1
            """
            self.cursor.execute(query_kel, (f"{kode_kota}.%",))
            result_kel = self.cursor.fetchone()
            
            if result_kel:
                tz_name, tz_offset = self.get_timezone_info(result_kel[0])
                return {
                    'name': nama_kota.replace('KAB. ', '').replace('KOTA ', '').title(),
                    'code': result_kel[0],
                    'timezone': tz_name,
                    'timezone_offset': tz_offset
                }
        
        return None
    
    def get_all_cities(self) -> Dict[str, Dict]:
        """
        Dapatkan semua kota dalam format yang kompatibel dengan config.py
        
        Returns:
            Dict dengan format: {"Nama Kota": {"code": "...", "timezone": "...", "timezone_offset": ...}}
        """
        result = {}
        
        for tz in ['WIB', 'WITA', 'WIT']:
            cities = self.get_cities_by_timezone(tz)
            for city in cities:
                result[city['name']] = {
                    'code': city['code'],
                    'timezone': city['timezone'],
                    'timezone_offset': city['timezone_offset']
                }
        
        return result
    
    def get_cities_by_keyword(self, keyword: str, limit: int = 10) -> list:
        """
        Cari kota berdasarkan keyword
        
        Args:
            keyword: Keyword pencarian
            limit: Maksimal hasil yang dikembalikan
            
        Returns:
            List dict info kota
        """
        if not self.conn:
            self.connect()
        
        # Search case-insensitive untuk kota
        query = """
            SELECT DISTINCT kode, nama 
            FROM wilayah_2020 
            WHERE UPPER(nama) LIKE UPPER(?) 
            AND LENGTH(kode) = 5
            AND CAST(SUBSTR(kode, 4, 2) AS INTEGER) >= 71
            AND (nama LIKE 'KOTA %' OR nama LIKE 'KAB. %')
            ORDER BY nama
            LIMIT ?
        """
        
        self.cursor.execute(query, (f"%{keyword}%", limit))
        results = []
        
        for row in self.cursor.fetchall():
            kode_kota, nama_kota = row
            
            # Ambil kode kelurahan pertama
            query_kel = """
                SELECT kode 
                FROM wilayah_2020 
                WHERE kode LIKE ? AND LENGTH(kode) >= 13
                LIMIT 1
            """
            self.cursor.execute(query_kel, (f"{kode_kota}.%",))
            result_kel = self.cursor.fetchone()
            
            if result_kel:
                tz_name, tz_offset = self.get_timezone_info(result_kel[0])
                results.append({
                    'name': nama_kota.replace('KAB. ', '').replace('KOTA ', '').title(),
                    'code': result_kel[0],
                    'timezone': tz_name,
                    'timezone_offset': tz_offset
                })
        
        return results
    
    def get_all_provinces(self) -> list:
        """
        Dapatkan semua provinsi
        
        Returns:
            List dict info provinsi dengan format: [{'code': '11', 'name': 'Aceh'}, ...]
        """
        if not self.conn:
            self.connect()
        
        query = """
            SELECT kode, nama
            FROM wilayah_2020
            WHERE LENGTH(kode) = 2
            ORDER BY nama
        """
        
        self.cursor.execute(query)
        provinces = []
        
        for row in self.cursor.fetchall():
            provinces.append({
                'code': row[0],
                'name': row[1]
            })
        
        return provinces
    
    def get_cities_by_province(self, province_code: str) -> list:
        """
        Dapatkan semua kota/kabupaten dalam provinsi
        
        Args:
            province_code: Kode provinsi (2 digit)
            
        Returns:
            List dict info kota
        """
        if not self.conn:
            self.connect()
        
        query = """
            SELECT kode, nama
            FROM wilayah_2020
            WHERE LENGTH(kode) = 5
            AND kode LIKE ?
            AND CAST(SUBSTR(kode, 4, 2) AS INTEGER) >= 71
            AND (nama LIKE 'KOTA %' OR nama LIKE 'KAB. %')
            ORDER BY nama
        """
        
        self.cursor.execute(query, (f"{province_code}.%",))
        cities = []
        
        for row in self.cursor.fetchall():
            kode_kota, nama_kota = row
            
            # Ambil kode kelurahan pertama untuk mendapatkan timezone
            query_kel = """
                SELECT kode 
                FROM wilayah_2020 
                WHERE kode LIKE ? AND LENGTH(kode) >= 13
                LIMIT 1
            """
            self.cursor.execute(query_kel, (f"{kode_kota}.%",))
            result_kel = self.cursor.fetchone()
            
            if result_kel:
                tz_name, tz_offset = self.get_timezone_info(result_kel[0])
                cities.append({
                    'code': result_kel[0],
                    'name': nama_kota.replace('KAB. ', '').replace('KOTA ', '').title(),
                    'timezone': tz_name,
                    'timezone_offset': tz_offset
                })
        
        return cities


# Contoh penggunaan
if __name__ == "__main__":
    db = WilayahDatabase()
    
    # Import data dari SQL (hanya perlu dilakukan sekali)
    if not os.path.exists("wilayah.db"):
        print("Database tidak ditemukan. Mengimport dari SQL...")
        db.import_from_sql("wilayah_2020.sql")
    
    # Test query
    db.connect()
    
    print("\n=== TEST: Random 5 kota WIB ===")
    cities_wib = db.get_random_cities(5, 'WIB')
    for city in cities_wib:
        print(f"- {city['name']}: {city['code']} ({city['timezone']})")
    
    print("\n=== TEST: Random 3 kota WITA ===")
    cities_wita = db.get_random_cities(3, 'WITA')
    for city in cities_wita:
        print(f"- {city['name']}: {city['code']} ({city['timezone']})")
    
    print("\n=== TEST: Cari kota Jakarta ===")
    jakarta = db.get_city_by_name("Jakarta")
    if jakarta:
        print(f"- {jakarta['name']}: {jakarta['code']} ({jakarta['timezone']})")
    
    print("\n=== TEST: Semua kota WIT ===")
    cities_wit = db.get_cities_by_timezone('WIT')
    print(f"Total kota WIT: {len(cities_wit)}")
    for city in cities_wit[:5]:
        print(f"- {city['name']}: {city['code']}")
    
    db.close()
