"""
Telegram Bot untuk BMKG Weather Automation
"""

import os
import sys
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

from bmkg_api import fetch_all_cities_weather, BMKGWeatherAPI
from template_generator import WeatherArticleGenerator
from ai_generator import GeminiAIGenerator
from config_db import (
    GOOGLE_GEMINI_API_KEYS,
    USE_AI_ENHANCEMENT,
    BMKG_API_BASE_URL,
    initialize_cities,
    CITY_CODES
)
from city_selector_db import CitySelector

# Load environment variables
load_dotenv()

# Global variables
city_selector = None
generator = None
ai_generator = None


def init_components():
    """Initialize komponen bot"""
    global city_selector, generator, ai_generator
    
    if city_selector is None:
        city_selector = CitySelector()
    
    if generator is None:
        generator = WeatherArticleGenerator()
    
    if ai_generator is None and USE_AI_ENHANCEMENT and GOOGLE_GEMINI_API_KEYS:
        ai_generator = GeminiAIGenerator(GOOGLE_GEMINI_API_KEYS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    welcome_text = """
🌤️ *Selamat datang di BMKG Weather Bot!*

Bot ini membantu Anda mendapatkan informasi cuaca dari BMKG dan generate artikel berita cuaca otomatis.

📋 *Command yang tersedia:*
/artikel - Generate artikel cuaca random (4 kota)
/artikel [kota1] [kota2] ... - Generate artikel dengan kota pilihan (1-4 kota)
/cuaca [kota] - Info cuaca singkat untuk kota tertentu
/cari [kota] - Cari kota di database
/kota - Lihat kota yang sedang dipilih
/random - Pilih 4 kota random baru
/help - Tampilkan bantuan

💡 Contoh penggunaan:
`/artikel` - 4 kota random
`/artikel Bandung` - Bandung + 3 kota random
`/artikel Jakarta Bandung` - Jakarta, Bandung + 2 kota random
`/artikel Jakarta Bandung Surabaya Denpasar` - 4 kota spesifik
`/cuaca Jakarta`
`/cari Surabaya`

Data cuaca dari BMKG Indonesia 🇮🇩
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    help_text = """
📖 *Panduan Penggunaan*

*1. Generate Artikel Cuaca*
/artikel - Generate artikel dengan 4 kota random
/artikel [kota1] [kota2] ... - Generate artikel dengan kota tertentu (1-4 kota)

Contoh:
• `/artikel` - 4 kota random
• `/artikel Jakarta` - Jakarta + 3 kota random
• `/artikel Jakarta Bandung` - Jakarta, Bandung + 2 kota random
• `/artikel Jakarta Bandung Surabaya Denpasar` - 4 kota spesifik

*2. Info Cuaca Singkat*
/cuaca [nama kota] - Informasi cuaca real-time

Contoh:
• `/cuaca Jakarta`
• `/cuaca Surabaya`

*3. Cari Kota*
/cari [nama kota] - Cari kota di database

Contoh:
• `/cari Malang`
• `/cari Denpasar`

*4. Manajemen Kota*
/kota - Lihat kota yang sedang dipilih
/random - Pilih 4 kota random baru

*Fitur:*
✅ 90,826+ kota/kabupaten Indonesia
✅ Data real-time dari BMKG
✅ AI enhancement dengan Google Gemini
✅ Support semua zona waktu (WIB, WITA, WIT)

Data cuaca dari BMKG Indonesia 🇮🇩
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def artikel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /artikel"""
    init_components()
    
    await update.message.reply_text("⏳ Mengambil data cuaca dari BMKG...")
    
    try:
        # Cek apakah ada argumen kota
        if context.args:
            # Parse kota yang diminta (bisa 1 atau lebih)
            city_names = []
            temp_name = []
            
            for arg in context.args:
                # Jika arg diawali huruf kapital, itu awal nama kota baru
                if arg[0].isupper() and temp_name:
                    city_names.append(' '.join(temp_name))
                    temp_name = [arg]
                else:
                    temp_name.append(arg)
            
            # Tambahkan kota terakhir
            if temp_name:
                city_names.append(' '.join(temp_name))
            
            # Validasi maksimal 4 kota
            if len(city_names) > 4:
                await update.message.reply_text(
                    "❌ Maksimal 4 kota untuk 1 artikel.\n\n"
                    "Contoh: `/artikel Jakarta Bandung Surabaya Denpasar`"
                )
                return
            
            # Reset selected cities
            city_selector.clear_selected_cities()
            
            # Tambahkan kota yang diminta
            not_found = []
            for city_name in city_names:
                if not city_selector.add_specific_city(city_name):
                    not_found.append(city_name)
            
            # Jika ada kota yang tidak ditemukan
            if not_found:
                await update.message.reply_text(
                    f"❌ Kota tidak ditemukan: {', '.join(not_found)}\n\n"
                    f"Gunakan /cari [nama kota] untuk mencari kota yang tersedia."
                )
                return
            
            # Jika kurang dari 4 kota, tambahkan random
            selected_cities = city_selector.get_selected_cities()
            if len(selected_cities) < 4:
                remaining = 4 - len(selected_cities)
                await update.message.reply_text(f"ℹ️ Menambahkan {remaining} kota random...")
                
                # Hitung distribusi timezone yang dibutuhkan
                existing_tz = [info['timezone'] for info in selected_cities.values()]
                wib_needed = max(0, 2 - existing_tz.count('WIB'))
                wita_needed = max(0, 1 - existing_tz.count('WITA'))
                wit_needed = max(0, 1 - existing_tz.count('WIT'))
                
                # Jika masih kurang, distribusi sisanya
                total_needed = wib_needed + wita_needed + wit_needed
                if total_needed < remaining:
                    wib_needed += (remaining - total_needed)
                
                city_selector.select_random_cities(
                    total_cities=remaining,
                    wib_count=wib_needed,
                    wita_count=wita_needed,
                    wit_count=wit_needed
                )
                
                selected_cities = city_selector.get_selected_cities()
        else:
            # Generate artikel dengan kota random
            initialize_cities(force_new=True)
            selected_cities = CITY_CODES
        
        # Ambil data cuaca
        weather_data = fetch_all_cities_weather(selected_cities)
        
        if not weather_data or len(weather_data) < 4:
            await update.message.reply_text("❌ Gagal mengambil data cuaca dari BMKG. Silakan coba lagi.")
            return
        
        # Generate artikel
        article = generator.generate_article(weather_data)
        title = generator.generate_title(weather_data)
        
        # Enhance dengan AI jika tersedia
        if ai_generator:
            try:
                await update.message.reply_text("🤖 Meningkatkan artikel dengan AI...")
                article, ai_title = ai_generator.enhance_article(article, weather_data)
                if ai_title:
                    title = ai_title
            except Exception as e:
                print(f"AI enhancement failed: {e}")
        
        # Format hasil
        result = f"*{title}*\n\n{article}"
        
        # Split jika terlalu panjang (Telegram limit 4096 chars)
        if len(result) > 4000:
            # Kirim judul dulu
            await update.message.reply_text(f"*{title}*", parse_mode='Markdown')
            
            # Split artikel
            chunks = [article[i:i+4000] for i in range(0, len(article), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(result, parse_mode='Markdown')
        
        # Kirim ringkasan kota
        city_list = "\n".join([f"• {name}" for name in weather_data.keys()])
        await update.message.reply_text(f"📍 *Kota dalam artikel:*\n{city_list}", parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in artikel command: {e}")


async def cuaca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /cuaca [kota]"""
    init_components()
    
    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan format: /cuaca [nama kota]\n\n"
            "Contoh: /cuaca Jakarta"
        )
        return
    
    city_name = ' '.join(context.args).title()
    
    await update.message.reply_text(f"⏳ Mencari data cuaca {city_name}...")
    
    try:
        # Cari kota di database
        city_info = city_selector.search_city(city_name)
        
        if not city_info:
            await update.message.reply_text(
                f"❌ Kota '{city_name}' tidak ditemukan.\n\n"
                f"Gunakan /cari {city_name} untuk mencari kota yang mirip."
            )
            return
        
        # Ambil data cuaca
        api = BMKGWeatherAPI(BMKG_API_BASE_URL)
        weather_data = api.get_city_weather(
            city_info['code'],
            6,  # Jam 6 pagi
            city_info['timezone_offset']
        )
        
        if not weather_data:
            await update.message.reply_text(f"❌ Gagal mengambil data cuaca untuk {city_name}")
            return
        
        # Format hasil
        result = f"""
🌤️ *Cuaca {city_name}*

📅 {generator.get_day_name(weather_data['datetime'])}, {generator.get_formatted_date(weather_data['datetime'])}
🕐 {generator.format_time(weather_data['target_hour'])} {weather_data['timezone']}

☁️ Kondisi: {weather_data['weather']}
🌡️ Suhu: {int(round(weather_data['temperature']))}°C
💧 Kelembapan: {int(round(weather_data['humidity']))}%
💨 Angin: {weather_data.get('wind_speed', 'N/A')} km/jam dari {weather_data.get('wind_direction', 'N/A')}

Data dari BMKG Indonesia 🇮🇩
        """
        
        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in cuaca command: {e}")


async def cari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /cari [kota]"""
    init_components()
    
    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan format: /cari [nama kota]\n\n"
            "Contoh: /cari Bandung"
        )
        return
    
    city_name = ' '.join(context.args)
    
    try:
        # Cari kota di database
        results = city_selector.search_cities(city_name, limit=10)
        
        if not results:
            await update.message.reply_text(f"❌ Tidak ditemukan kota dengan kata kunci '{city_name}'")
            return
        
        # Format hasil
        result_text = f"🔍 *Hasil pencarian '{city_name}':*\n\n"
        
        for city in results:
            result_text += f"📍 *{city['name']}*\n"
            result_text += f"   Kode: `{city['code']}`\n"
            result_text += f"   Zona: {city['timezone']} (UTC+{city['timezone_offset']})\n\n"
        
        result_text += f"Ditemukan {len(results)} kota."
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in cari command: {e}")


async def kota_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /kota"""
    init_components()
    
    try:
        # Ambil kota yang sedang dipilih
        selected_cities = city_selector.get_selected_cities()
        
        if not selected_cities:
            initialize_cities()
            selected_cities = CITY_CODES
        
        # Format hasil per timezone
        result_text = "📍 *Kota yang sedang dipilih:*\n\n"
        
        by_timezone = {'WIB': [], 'WITA': [], 'WIT': []}
        for city_name, city_info in selected_cities.items():
            by_timezone[city_info['timezone']].append((city_name, city_info))
        
        for tz in ['WIB', 'WITA', 'WIT']:
            if by_timezone[tz]:
                result_text += f"*{tz} (UTC+{by_timezone[tz][0][1]['timezone_offset']}):*\n"
                for city_name, city_info in by_timezone[tz]:
                    result_text += f"  • {city_name}\n"
                result_text += "\n"
        
        result_text += f"Total: {len(selected_cities)} kota\n\n"
        result_text += "Gunakan /random untuk pilih kota baru"
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in kota command: {e}")


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /random"""
    init_components()
    
    await update.message.reply_text("🎲 Memilih 4 kota random...")
    
    try:
        # Pilih kota random baru
        initialize_cities(force_new=True)
        selected_cities = CITY_CODES
        
        # Format hasil
        result_text = "✅ *Kota baru berhasil dipilih!*\n\n"
        
        by_timezone = {'WIB': [], 'WITA': [], 'WIT': []}
        for city_name, city_info in selected_cities.items():
            by_timezone[city_info['timezone']].append((city_name, city_info))
        
        for tz in ['WIB', 'WITA', 'WIT']:
            if by_timezone[tz]:
                result_text += f"*{tz}:*\n"
                for city_name, city_info in by_timezone[tz]:
                    result_text += f"  • {city_name}\n"
                result_text += "\n"
        
        result_text += "Gunakan /artikel untuk generate berita cuaca"
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in random command: {e}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /stats"""
    init_components()
    
    try:
        # Hitung statistik database
        total_cities = city_selector.count_cities_by_timezone()
        
        result_text = "📊 *Statistik Database*\n\n"
        result_text += f"🌍 Total kota: *{sum(total_cities.values())}*\n\n"
        result_text += "*Per Zona Waktu:*\n"
        result_text += f"• WIB (UTC+7): {total_cities.get('WIB', 0):,} kota\n"
        result_text += f"• WITA (UTC+8): {total_cities.get('WITA', 0):,} kota\n"
        result_text += f"• WIT (UTC+9): {total_cities.get('WIT', 0):,} kota\n\n"
        
        result_text += "*Status AI:*\n"
        if ai_generator:
            result_text += f"✅ AI Enhancement: Aktif\n"
            result_text += f"🤖 Model: Google Gemini\n"
            result_text += f"🔑 API Keys: {len(GOOGLE_GEMINI_API_KEYS)} tersedia\n"
        else:
            result_text += "⚠️ AI Enhancement: Tidak aktif\n"
        
        result_text += "\nData dari BMKG Indonesia 🇮🇩"
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in stats command: {e}")


def main():
    """Fungsi utama untuk menjalankan bot"""
    
    # Ambil token dari environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN tidak ditemukan di .env file")
        print("Silakan tambahkan TELEGRAM_BOT_TOKEN ke file .env")
        sys.exit(1)
    
    print("🤖 Starting BMKG Weather Telegram Bot...")
    print("=" * 60)
    
    # Buat aplikasi bot
    application = Application.builder().token(token).build()
    
    # Tambahkan command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("artikel", artikel))
    application.add_handler(CommandHandler("cuaca", cuaca))
    application.add_handler(CommandHandler("cari", cari))
    application.add_handler(CommandHandler("kota", kota_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("stats", stats))
    
    print("✅ Bot siap menerima perintah!")
    print("=" * 60)
    print("\nCommand yang tersedia:")
    print("  /start   - Mulai bot")
    print("  /help    - Bantuan")
    print("  /artikel - Generate artikel cuaca")
    print("  /cuaca   - Info cuaca kota")
    print("  /cari    - Cari kota")
    print("  /kota    - Lihat kota terpilih")
    print("  /random  - Pilih kota random")
    print("  /stats   - Statistik database")
    print("\nTekan Ctrl+C untuk stop bot")
    print("=" * 60)
    
    # Jalankan bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot dihentikan oleh user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
