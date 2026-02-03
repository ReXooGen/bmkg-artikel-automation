"""
Program Utama - Automasi Artikel Cuaca BMKG dengan Graceful AI Fallback
Database SQL Version - Menggunakan 90,826+ wilayah dari database
"""

from bmkg_api import fetch_all_cities_weather
from template_generator import WeatherArticleGenerator
from ai_generator import GeminiAIGenerator

# Gunakan config_db untuk akses database SQL
from config_db import (
    CITY_CODES, 
    initialize_cities,
    GOOGLE_GEMINI_API_KEYS, 
    USE_AI_ENHANCEMENT
)
import sys


def main():
    """Fungsi utama untuk menjalankan program"""
    
    print("="*60)
    print("PROGRAM AUTOMASI ARTIKEL CUACA BMKG")
    print("="*60)
    print("\nSumber Data: BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)")
    print("API: https://api.bmkg.go.id/publik/prakiraan-cuaca")
    print("\n✓ Menggunakan Database SQL (90,826+ wilayah)")
    print()
    
    # Step 0: Tampilkan kota yang dipilih dari database
    print("STEP 0: Kota terpilih dari database...")
    print("-" * 60)
    
    # CITY_CODES sudah di-load otomatis dari config_db
    if not CITY_CODES:
        print("⚠️  Database kosong, generating kota random...")
        initialize_cities(force_new=True)
    
    # Display selected cities
    print(f"\nTotal kota: {len(CITY_CODES)}")
    by_timezone = {'WIB': [], 'WITA': [], 'WIT': []}
    for city_name, city_info in CITY_CODES.items():
        by_timezone[city_info['timezone']].append((city_name, city_info))
    
    for tz in ['WIB', 'WITA', 'WIT']:
        if by_timezone[tz]:
            print(f"\n{tz} (UTC+{by_timezone[tz][0][1]['timezone_offset']}):")
            for city_name, city_info in by_timezone[tz]:
                print(f"  - {city_name:20s} : {city_info['code']}")
    
    print("\n" + "-" * 60)
    
    # Step 1: Ambil data cuaca dari API BMKG
    print("\nSTEP 1: Mengambil data cuaca dari API BMKG...")
    print("-" * 60)
    
    try:
        # Auto-replace failed cities dengan kota lain dari timezone yang sama
        weather_data = fetch_all_cities_weather(CITY_CODES, auto_replace_failed=True)
        
        if not weather_data or len(weather_data) < 4:
            print("\n✗ Error: Tidak semua data kota berhasil diambil")
            print("Pastikan koneksi internet aktif dan API BMKG dapat diakses")
            sys.exit(1)
        
        print("\n✓ Semua data cuaca berhasil diambil!")
        
    except Exception as e:
        print(f"\n✗ Error saat mengambil data: {e}")
        sys.exit(1)
    
    # Step 2: Generate artikel dari template
    print("\n" + "="*60)
    print("STEP 2: Generate artikel dari template...")
    print("-" * 60)
    
    try:
        generator = WeatherArticleGenerator()
        
        # Tampilkan ringkasan data
        generator.display_weather_summary(weather_data)
        
        # Generate artikel dasar
        article = generator.generate_article(weather_data)
        title = generator.generate_title(weather_data)
        
        print("\n✓ Artikel dasar berhasil di-generate!")
        print(f"✓ Judul: {title}")
        
    except Exception as e:
        print(f"\n✗ Error saat generate artikel: {e}")
        sys.exit(1)
    
    # Step 3: Enhance artikel dengan AI (opsional dengan graceful fallback)
    ai_title = None
    ai_enhanced = False
    
    if USE_AI_ENHANCEMENT and GOOGLE_GEMINI_API_KEYS:
        print("\n" + "="*60)
        print("STEP 3: Enhance artikel dengan AI...")
        print("-" * 60)
        
        try:
            ai_generator = GeminiAIGenerator(GOOGLE_GEMINI_API_KEYS)
            article, ai_title = ai_generator.enhance_article(article, weather_data)
            
            # Gunakan judul AI jika tersedia
            if ai_title:
                title = ai_title
                ai_enhanced = True
                print(f"✓ Judul AI: {title}")
            
            # Status AI
            print(f"AI Status: {ai_generator.get_status()}")
            
        except Exception as e:
            print(f"\n⚠️  Warning: AI enhancement gagal ({e})")
            print("Melanjutkan dengan artikel dasar...")
    else:
        print("\n" + "="*60)
        print("STEP 3: AI Enhancement dinonaktifkan")
        print("-" * 60)
    
    # Step 4: Tampilkan dan simpan artikel
    print("\n" + "="*60)
    print("STEP 4: Hasil Artikel")
    print("="*60)
    print()
    print("=" * 80)
    print("JUDUL:")
    print(title)
    print("=" * 80)
    print()
    print(article)
    print()
    
    # Simpan ke file dengan judul
    output_file = "artikel_cuaca.txt"
    full_article = f"{title}\n\n{'='*80}\n\n{article}"
    generator.save_article(full_article, output_file)
    
    print("\n" + "="*60)
    print("PROGRAM SELESAI")
    print("="*60)
    print(f"\nArtikel telah disimpan di: {output_file}")
    
    if ai_enhanced:
        print("✓ Artikel telah ditingkatkan dengan AI Google Gemini")
    else:
        if USE_AI_ENHANCEMENT:
            print("⚠️  Artikel menggunakan template dasar (AI tidak tersedia)")
        else:
            print("ℹ️  Artikel menggunakan template dasar (AI dinonaktifkan)")
    
    print("\nPerhatian: Wajib mencantumkan BMKG sebagai sumber data!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram dibatalkan oleh user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error tidak terduga: {e}")
        sys.exit(1)