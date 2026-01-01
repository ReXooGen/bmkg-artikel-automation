"""
Konfigurasi dengan database SQL - alternatif untuk config.py
Menggunakan SQLite database untuk data wilayah
"""

from city_selector_db import CitySelector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BMKG_API_BASE_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

# Google Gemini API Keys (dengan fallback)
# Baca dari environment variable, fallback ke list kosong
gemini_keys_env = os.getenv('GOOGLE_GEMINI_API_KEYS', '')
if gemini_keys_env:
    GOOGLE_GEMINI_API_KEYS = [key.strip() for key in gemini_keys_env.split(',')]
else:
    GOOGLE_GEMINI_API_KEYS = []
    print("⚠️  Warning: GOOGLE_GEMINI_API_KEYS tidak diset. AI enhancement akan dinonaktifkan.")

# Backward compatibility
GOOGLE_GEMINI_API_KEY = GOOGLE_GEMINI_API_KEYS[0] if GOOGLE_GEMINI_API_KEYS else None

# AI Enhancement Settings
USE_AI_ENHANCEMENT = os.getenv('USE_AI_ENHANCEMENT', 'True').lower() == 'true' and len(GOOGLE_GEMINI_API_KEYS) > 0

# WhatsApp Configuration
WHATSAPP_TARGET_NUMBER = os.getenv('WHATSAPP_TARGET_NUMBER', '')
WHATSAPP_SEND_TIME = "04:00"  # Jam pengiriman otomatis (format 24 jam)

# Database Configuration
DATABASE_PATH = "wilayah.db"
SQL_FILE = "wilayah_2020.sql"

# City Selection Settings
TOTAL_CITIES = 4   # Total kota yang akan dipilih
WIB_CITIES = 2     # Jumlah kota WIB
WITA_CITIES = 1    # Jumlah kota WITA
WIT_CITIES = 1     # Jumlah kota WIT

# Initialize city selector
_city_selector = None

def initialize_cities(force_new: bool = False):
    """
    Initialize atau reload kota dari database
    
    Args:
        force_new: True untuk generate ulang kota random
    """
    global _city_selector, CITY_CODES
    
    if _city_selector is None:
        _city_selector = CitySelector(DATABASE_PATH)
    
    # Cek apakah sudah ada kota yang dipilih
    if not force_new and CITY_CODES:
        return CITY_CODES
    
    # Pilih kota random dari database
    CITY_CODES = _city_selector.select_random_cities(
        total_cities=TOTAL_CITIES,
        wib_count=WIB_CITIES,
        wita_count=WITA_CITIES,
        wit_count=WIT_CITIES
    )
    
    return CITY_CODES

def add_city(city_name: str) -> bool:
    """
    Tambahkan kota spesifik
    
    Args:
        city_name: Nama kota yang ingin ditambahkan
    
    Returns:
        True jika berhasil
    """
    global _city_selector, CITY_CODES
    
    if _city_selector is None:
        initialize_cities()
    
    if _city_selector.add_specific_city(city_name):
        CITY_CODES = _city_selector.get_selected_cities()
        return True
    return False

def get_cities_by_timezone(timezone: str):
    """
    Dapatkan semua kota dalam timezone tertentu dari database
    
    Args:
        timezone: WIB, WITA, atau WIT
    
    Returns:
        List kota
    """
    global _city_selector
    
    if _city_selector is None:
        initialize_cities()
    
    return _city_selector.db.get_cities_by_timezone(timezone)

def search_city(city_name: str):
    """
    Cari kota berdasarkan nama
    
    Args:
        city_name: Nama kota (bisa sebagian)
    
    Returns:
        Info kota atau None
    """
    global _city_selector
    
    if _city_selector is None:
        initialize_cities()
    
    return _city_selector.db.get_city_by_name(city_name)

# Kota yang aktif digunakan (akan di-load dari database)
CITY_CODES = {}

# Auto-initialize saat import
if not os.path.exists(DATABASE_PATH):
    print("⚠️  Database tidak ditemukan!")
    print(f"   Jalankan: python wilayah_db.py")
    print(f"   Atau jalankan: initialize_cities() untuk auto-import")
else:
    # Load kota dari database
    initialize_cities()

# Mapping kondisi cuaca Indonesia ke format yang lebih natural
WEATHER_MAPPING = {
    "Cerah": "cerah",
    "Cerah Berawan": "cerah berawan",
    "Berawan": "berawan",
    "Berawan Tebal": "berawan tebal",
    "Udara Kabur": "udara kabur",
    "Asap": "berasap",
    "Hujan Ringan": "hujan ringan",
    "Hujan Sedang": "hujan sedang",
    "Hujan Lebat": "hujan lebat",
    "Hujan Lokal": "hujan lokal",
    "Hujan Petir": "hujan petir",
    "Kabut": "berkabut"
}

# Target waktu untuk semua kota (jam lokal pagi hari)
DEFAULT_TARGET_HOUR = 6  # Jam 6 pagi untuk semua kota


# Print selected cities saat di-import
if _city_selector and CITY_CODES:
    print(f"\n✓ Loaded {len(CITY_CODES)} cities from database")
    _city_selector.print_selected_cities()