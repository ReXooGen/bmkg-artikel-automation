"""
Module untuk generate artikel cuaca dari template
"""

from datetime import datetime
from typing import Dict


class WeatherArticleGenerator:
    """Class untuk generate artikel cuaca dari template (dinamis untuk kota apapun)"""
    
    def __init__(self):
        """Initialize generator"""
        pass
    
    @staticmethod
    def get_day_name(date_str: str) -> str:
        """
        Mendapatkan nama hari dalam Bahasa Indonesia
        
        Args:
            date_str: String tanggal format YYYY-MM-DD HH:MM:SS
            
        Returns:
            Nama hari dalam Bahasa Indonesia
        """
        days = {
            0: "Senin",
            1: "Selasa",
            2: "Rabu",
            3: "Kamis",
            4: "Jumat",
            5: "Sabtu",
            6: "Minggu"
        }
        
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return days[dt.weekday()]
        except:
            return "Senin"
    
    @staticmethod
    def get_formatted_date(date_str: str) -> str:
        """
        Format tanggal ke format Indonesia
        
        Args:
            date_str: String tanggal format YYYY-MM-DD HH:MM:SS
            
        Returns:
            Tanggal format Indonesia (DD NamaBulan YYYY)
        """
        months = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return f"{dt.day} {months[dt.month]} {dt.year}"
        except:
            return "1 Januari 2026"
    
    @staticmethod
    def format_time(hour: int) -> str:
        """Format jam ke format 2 digit"""
        return f"{hour:02d}.00"
    
    def generate_title(self, weather_data: Dict[str, Dict]) -> str:
        """
        Generate judul artikel berita yang menarik dengan prioritas cuaca menarik
        
        Args:
            weather_data: Dictionary berisi data cuaca untuk setiap kota
            
        Returns:
            String judul artikel
        """
        cities = list(weather_data.keys())
        
        # Parse datetime jika masih string
        first_city_datetime = weather_data[cities[0]]['datetime']
        if isinstance(first_city_datetime, str):
            from dateutil import parser
            first_city_datetime = parser.parse(first_city_datetime)
        
        # Format datetime object ke string
        months = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        date_str = f"{first_city_datetime.day} {months[first_city_datetime.month]} {first_city_datetime.year}"
        
        # Cari kota dengan cuaca paling menarik/ekstrem
        priority_cities = []
        
        # 1. Prioritas tertinggi: Hujan lebat/petir
        for city in cities:
            weather = weather_data[city]['weather'].lower()
            if 'petir' in weather or 'lebat' in weather:
                priority_cities.append((city, weather_data[city], 'ekstrem'))
        
        # 2. Prioritas menengah: Hujan ringan/sedang
        if not priority_cities:
            for city in cities:
                weather = weather_data[city]['weather'].lower()
                if 'hujan' in weather:
                    priority_cities.append((city, weather_data[city], 'hujan'))
        
        # 3. Prioritas rendah: Cuaca cerah/berawan di kota pertama
        if not priority_cities:
            priority_cities.append((cities[0], weather_data[cities[0]], 'normal'))
        
        # Pilih kota utama (yang paling menarik)
        main_city = priority_cities[0][0]
        main_weather = weather_data[main_city]['weather']
        
        # Cari 1-2 kota lain dengan cuaca kontras
        other_cities = []
        for city in cities:
            if city != main_city:
                other_cities.append((city, weather_data[city]['weather']))
        
        # Format judul dengan kota utama + 1-2 kota lain
        if len(other_cities) >= 2:
            # Pilih 2 kota dengan cuaca paling berbeda
            city2_name, city2_weather = other_cities[0]
            city3_name, city3_weather = other_cities[1]
            
            # Jika kota ke-2 dan ke-3 mirip, gabungkan
            if city2_weather.lower() == city3_weather.lower():
                title = f"BMKG: Cuaca Kota {main_city} {date_str} Diprakirakan {main_weather}, Sejumlah Kota Lainnya {city2_weather}"
            else:
                title = f"BMKG: Cuaca Kota {main_city} {date_str} Diprakirakan {main_weather}, {city2_name} {city2_weather}"
        elif len(other_cities) == 1:
            city2_name, city2_weather = other_cities[0]
            title = f"BMKG: Cuaca Kota {main_city} {date_str} Diprakirakan {main_weather}, {city2_name} {city2_weather}"
        else:
            title = f"BMKG: Cuaca Kota {main_city} {date_str} Diprakirakan {main_weather}"
        
        return title
    
    def generate_article(self, weather_data: Dict[str, Dict]) -> str:
        """
        Generate artikel dari data cuaca (dinamis untuk kota apapun)
        
        Args:
            weather_data: Dictionary berisi data cuaca untuk setiap kota
            
        Returns:
            String artikel yang sudah diisi dengan data cuaca
        """
        # Validasi minimal 4 kota
        if len(weather_data) < 4:
            raise ValueError("Minimal 4 kota diperlukan untuk generate artikel")
        
        # Ambil 4 kota pertama (urutan dari dict)
        cities = list(weather_data.keys())
        city1_name = cities[0]
        city2_name = cities[1]
        city3_name = cities[2]
        city4_name = cities[3]
        
        city1 = weather_data[city1_name]
        city2 = weather_data[city2_name]
        city3 = weather_data[city3_name]
        city4 = weather_data[city4_name]
        
        # Generate template dinamis
        template = f"""Badan Meteorologi, Klimatologi dan Geofisika (BMKG) memprakirakan cuaca di Kota {city1_name} {city1['weather'].lower()} pada hari {self.get_day_name(city1['datetime'])}, {self.get_formatted_date(city1['datetime'])}. Kondisi ini berbeda dengan beberapa daerah lainnya di Indonesia yang mengalami cuaca berbeda-beda.

Berdasarkan pantauan di laman resmi BMKG.go.id pada pukul {self.format_time(city1['target_hour'])} {city1['timezone']}, suhu udara di Kota {city1_name} berkisar {int(round(city1['temperature']))} derajat Celcius. Sementara, tingkat kelembapan udara berada pada {int(round(city1['humidity']))} persen.

Berbeda dengan kota {city1_name}, {city2_name} pada pukul {self.format_time(city2['target_hour'])} {city2['timezone']} diprakirakan {city2['weather'].lower()} dengan suhu udara berkisar {int(round(city2['temperature']))} derajat Celcius. Sementara, untuk tingkat kelembapan udara berada pada angka {int(round(city2['humidity']))} persen.

Kota {city3_name} diprakirakan terjadi {city3['weather'].lower()} pada pukul {self.format_time(city3['target_hour'])} {city3['timezone']}. Suhu udara kota ini berkisar {int(round(city3['temperature']))} derajat Celcius. Tingkat kelembapan udaranya berada pada angka {int(round(city3['humidity']))} persen.

Berbeda dengan kota-kota yang telah dilaporkan, pada pukul {self.format_time(city4['target_hour'])} {city4['timezone']} di kota {city4_name} diprakirakan {city4['weather'].lower()}. Suhu udara di kota tersebut berkisar {int(round(city4['temperature']))} derajat Celcius, dengan tingkat kelembapan udara berada pada angka antara {int(round(city4['humidity']))} persen.

BMKG juga mengingatkan bahwa kondisi cuaca dapat berubah sewaktu-waktu. Masyarakat diimbau untuk selalu memantau informasi terkini dari sumber resmi dan mempersiapkan diri sesuai dengan kondisi cuaca di lokasi masing-masing. (*)"""
        
        return template
    
    def save_article(self, article: str, filename: str = "artikel_cuaca.txt"):
        """
        Simpan artikel ke file
        
        Args:
            article: String artikel
            filename: Nama file output
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(article)
            print(f"\n✓ Artikel berhasil disimpan ke: {filename}")
        except Exception as e:
            print(f"✗ Error menyimpan artikel: {e}")
    
    def display_weather_summary(self, weather_data: Dict[str, Dict]):
        """
        Menampilkan ringkasan data cuaca yang diambil
        
        Args:
            weather_data: Dictionary berisi data cuaca untuk setiap kota
        """
        print("\n" + "="*60)
        print("RINGKASAN DATA CUACA")
        print("="*60)
        
        for city_name, data in weather_data.items():
            print(f"\n{city_name}:")
            print(f"  Waktu       : {self.format_time(data['target_hour'])} {data['timezone']}")
            print(f"  Cuaca       : {data['weather']}")
            print(f"  Suhu        : {int(round(data['temperature']))}°C")
            print(f"  Kelembapan  : {int(round(data['humidity']))}%")
            if data.get('wind_speed'):
                print(f"  Angin       : {data['wind_speed']} km/jam dari {data.get('wind_direction', 'N/A')}")
        
        print("\n" + "="*60)
