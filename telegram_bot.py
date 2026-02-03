"""
Telegram Bot untuk BMKG Weather Automation
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown
from telegram.error import NetworkError, TelegramError, TimedOut, RetryAfter
from dotenv import load_dotenv

from bmkg_api import fetch_all_cities_weather, BMKGWeatherAPI
from template_generator import WeatherArticleGenerator
from ai_generator import GeminiAIGenerator
from bmkg_image_fetcher import BMKGImageFetcher
from bmkg_image_scheduler import BMKGImageScheduler
from config_db import (
    GOOGLE_GEMINI_API_KEYS,
    USE_AI_ENHANCEMENT,
    BMKG_API_BASE_URL,
    initialize_cities,
    CITY_CODES
)
from city_selector_db import CitySelector
from database import UserDatabase

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global variables
city_selector = None
generator = None
ai_generator = None
image_fetcher = None
user_db = None


def init_components():
    """Initialize komponen bot"""
    global city_selector, generator, ai_generator, image_fetcher, user_db
    
    if city_selector is None:
        city_selector = CitySelector()
    
    if generator is None:
        generator = WeatherArticleGenerator()
    
    if ai_generator is None and USE_AI_ENHANCEMENT and GOOGLE_GEMINI_API_KEYS:
        ai_generator = GeminiAIGenerator(GOOGLE_GEMINI_API_KEYS)
    
    if image_fetcher is None:
        image_fetcher = BMKGImageFetcher()
    
    if user_db is None:
        user_db = UserDatabase()
        print(f"✅ UserDatabase initialized: {user_db.db_path}")
        print(f"✅ Database initialized: {user_db.db_path}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Get error details
    error = context.error
    
    try:
        if isinstance(error, NetworkError):
            logger.warning(f"Network error occurred: {error}")
            error_message = (
                "⚠️ *Network Error*\n\n"
                "Koneksi ke server Telegram gagal. Kemungkinan penyebab:\n"
                "• Tidak ada koneksi internet\n"
                "• DNS tidak dapat merespon\n"
                "• Firewall memblokir koneksi\n\n"
                "Bot akan mencoba koneksi ulang secara otomatis."
            )
        elif isinstance(error, TimedOut):
            logger.warning(f"Request timed out: {error}")
            error_message = (
                "⚠️ *Timeout*\n\n"
                "Request terlalu lama dan timeout.\n"
                "Silakan coba lagi dalam beberapa saat."
            )
        elif isinstance(error, RetryAfter):
            logger.warning(f"Rate limited, retry after {error.retry_after} seconds")
            error_message = (
                f"⚠️ *Rate Limited*\n\n"
                f"Terlalu banyak request. Coba lagi setelah {error.retry_after} detik."
            )
        elif isinstance(error, TelegramError):
            logger.error(f"Telegram error: {error}")
            error_message = (
                "❌ *Telegram Error*\n\n"
                f"Terjadi kesalahan: {str(error)}"
            )
        else:
            logger.error(f"Unexpected error: {error}")
            error_message = (
                "❌ *Error*\n\n"
                f"Terjadi kesalahan tidak terduga.\n"
                f"Silakan hubungi admin jika masalah berlanjut."
            )
        
        # Try to notify user if update is available
        if update and isinstance(update, Update):
            if update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        error_message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send error message to user: {e}")
    
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Get error details
    error = context.error
    
    try:
        if isinstance(error, NetworkError):
            logger.warning(f"Network error occurred: {error}")
            error_message = (
                "⚠️ *Network Error*\n\n"
                "Koneksi ke server Telegram gagal. Kemungkinan penyebab:\n"
                "• Tidak ada koneksi internet\n"
                "• DNS tidak dapat merespon\n"
                "• Firewall memblokir koneksi\n\n"
                "Bot akan mencoba koneksi ulang secara otomatis."
            )
        elif isinstance(error, TimedOut):
            logger.warning(f"Request timed out: {error}")
            error_message = (
                "⚠️ *Timeout*\n\n"
                "Request terlalu lama dan timeout.\n"
                "Silakan coba lagi dalam beberapa saat."
            )
        elif isinstance(error, RetryAfter):
            logger.warning(f"Rate limited, retry after {error.retry_after} seconds")
            error_message = (
                f"⚠️ *Rate Limited*\n\n"
                f"Terlalu banyak request. Coba lagi setelah {error.retry_after} detik."
            )
        elif isinstance(error, TelegramError):
            logger.error(f"Telegram error: {error}")
            error_message = (
                "❌ *Telegram Error*\n\n"
                f"Terjadi kesalahan: {str(error)}"
            )
        else:
            logger.error(f"Unexpected error: {error}")
            error_message = (
                "❌ *Error*\n\n"
                f"Terjadi kesalahan tidak terduga.\n"
                f"Silakan hubungi admin jika masalah berlanjut."
            )
        
        # Try to notify user if update is available
        if update and isinstance(update, Update):
            if update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        error_message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send error message to user: {e}")
    
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "start")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /start")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    welcome_text = """
🌤️ *Selamat datang di BMKG Weather Bot!*

Bot ini membantu Anda mendapatkan informasi cuaca dari BMKG dan generate artikel berita cuaca otomatis.

📋 *Command yang tersedia:*
/artikel - Generate artikel cuaca random (4 kota)
/artikelkota - Generate artikel dengan kota & waktu pilihan (1-4 kota)
/cuacakota - Info cuaca singkat real-time
/satelit - Citra satelit Himawari potensi hujan
/kota - Lihat 4 kota yang sedang dipilih
/random - Pilih 4 kota random baru
/help - Tampilkan bantuan lengkap
/carikota - Cari kota di database 90,826+ kota

💡 Contoh penggunaan:
`/artikel` - 4 kota random
`/artikelkota Jakarta 09` - Jakarta jam 09:00
`/artikelkota Jakarta 09 Surabaya 10` - Jakarta 09:00, Surabaya 10:00
`/artikelkota Jakarta 09 Bandung 10 Surabaya 11 Denpasar 12` - 4 kota dengan waktu
`/cuacakota Jakarta` - Jakarta jam 06:00 (default)
`/cuacakota Jakarta 15` - Jakarta jam 15:00
`/carikota Surabaya`

✨ *Fitur Baru:* Pilih waktu spesifik untuk setiap kota!

Data cuaca dari BMKG Indonesia 🇮🇩
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "help")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /help")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    help_text = """
📖 *Panduan Penggunaan*

*1. Generate Artikel Cuaca*
/artikel - Generate artikel dengan 4 kota random
/artikelkota [kota1] [jam1] [kota2] [jam2] ... - Generate artikel dengan kota & waktu tertentu (1-4 kota)

Contoh:
• `/artikel` - 4 kota random (jam default 06:00)
• `/artikelkota Jakarta 09` - Jakarta jam 09:00 + 3 kota random
• `/artikelkota Jakarta 09 Surabaya 10` - Jakarta 09:00, Surabaya 10:00 + 2 kota random
• `/artikelkota Jakarta 09 Bandung 10 Surabaya 11 Denpasar 12` - 4 kota dengan waktu spesifik

*Pilih Waktu via Button:*
Ketik `/artikelkota` tanpa argumen, lalu pilih kota dan waktu via menu interaktif.

*2. Info Cuaca Singkat*
/cuacakota [nama kota] [jam] - Informasi cuaca real-time

Contoh:
• `/cuacakota Jakarta` - Jakarta jam 06:00 (default)
• `/cuacakota Jakarta 09` - Jakarta jam 09:00
• `/cuacakota Surabaya 15` - Surabaya jam 15:00

*3. Cari Kota*
/carikota [nama kota] - Cari kota di database

Contoh:
• `/carikota Malang`
• `/carikota Denpasar`

*4. Citra Satelit*
/satelit - Citra satelit Himawari potensi hujan

*5. Manajemen Kota*
/kota - Lihat kota yang sedang dipilih
/random - Pilih 4 kota random baru

*Fitur:*
✅ 90,826+ kota/kabupaten Indonesia
✅ Data real-time dari BMKG
✅ Pilih waktu spesifik untuk setiap kota (00:00 - 23:00)
✅ AI enhancement dengan Google Gemini
✅ Support semua zona waktu (WIB, WITA, WIT)

Data cuaca dari BMKG Indonesia 🇮🇩
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def artikel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /artikel - random 4 kota"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "artikel")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /artikel")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    await update.message.reply_text("⏳ Mengambil data cuaca dari BMKG...")
    
    try:
        # Gunakan kota yang sudah dipilih dari city_selector (dari /random atau inisialisasi awal)
        selected_cities = city_selector.get_selected_cities()
        
        # Jika belum ada kota yang dipilih, pilih random
        if not selected_cities:
            city_selector.select_random_cities(
                total_cities=4,
                wib_count=2,
                wita_count=1,
                wit_count=1
            )
            selected_cities = city_selector.get_selected_cities()
        
        # Ambil data cuaca dengan auto-replacement untuk kota yang gagal
        weather_data = fetch_all_cities_weather(selected_cities, auto_replace_failed=True)
        
        if not weather_data or len(weather_data) < 4:
            await update.message.reply_text(
                "❌ Gagal mengambil data cuaca lengkap dari BMKG setelah beberapa percobaan.\n"
                "Beberapa wilayah mungkin tidak didukung oleh API BMKG.\n\n"
                "Silakan coba lagi atau gunakan /artikelkota untuk memilih kota spesifik."
            )
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
        
        # Kirim gambar satelit terlebih dahulu
        try:
            filepath, _ = image_fetcher.download_image('satelit', force=True)
            if filepath and os.path.exists(filepath):
                with open(filepath, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="🛰️ Citra Satelit Himawari-9 - Potensi Curah Hujan Indonesia"
                    )
        except Exception as e:
            print(f"Failed to send satellite image: {e}")
        
        # Format hasil - kirim judul terpisah dengan Markdown, artikel tanpa parsing
        escaped_title = escape_markdown(title, version=2)
        await update.message.reply_text(f"*{escaped_title}*", parse_mode='MarkdownV2')
        
        # Split artikel jika terlalu panjang (Telegram limit 4096 chars)
        # Kirim artikel TANPA parse_mode untuk menghindari error parsing
        if len(article) > 4000:
            chunks = [article[i:i+4000] for i in range(0, len(article), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(article)
        
        # Kirim ringkasan kota
        city_list = "\n".join([f"• {name}" for name in weather_data.keys()])
        await update.message.reply_text(f"📍 *Kota dalam artikel:*\n{city_list}", parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in artikel command: {e}")


async def artikelkota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /artikelkota - dengan kota pilihan"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    args_str = ' '.join(context.args) if context.args else 'None'
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, f"artikelkota {args_str}")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /artikelkota {args_str}")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if not context.args:
        # Initialize context untuk interactive mode
        session_data = {
            'selected_cities': [],
            'city_times': {},
            'timezone_filter': None
        }
        
        # Save session to DB if available
        if user_db:
            user_db.update_session(user.id, session_data)
        
        # Also keep in context.user_data for quick access
        context.user_data.update(session_data)
        
        # Tampilkan menu pilihan timezone terlebih dahulu
        keyboard = [
            [
                InlineKeyboardButton("🌏 Indonesia (Semua Zona)", callback_data="tz_ALL")
            ],
            [
                InlineKeyboardButton("🌅 WIB", callback_data="tz_WIB"),
                InlineKeyboardButton("🌄 WITA", callback_data="tz_WITA"),
                InlineKeyboardButton("🌇 WIT", callback_data="tz_WIT")
            ],
            [InlineKeyboardButton("🎲 Pilih Random", callback_data="artikel_random")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🕐 *Pilih Zona Waktu:*\n\n"
            "Pilih zona waktu untuk melihat provinsi,\n"
            "atau ketik: `/artikelkota [nama kota] [jam]`\n\n"
            "📌 *Contoh:*\n"
            "`/artikelkota Jakarta 09` - Jakarta jam 09:00\n"
            "`/artikelkota Jakarta 09 Surabaya 10` - Jakarta 09:00, Surabaya 10:00\n\n"
            "📌 *Zona Waktu Indonesia:*\n"
            "• WIB (UTC+7): Jawa, Sumatra, Kalimantan Barat\n"
            "• WITA (UTC+8): Kalimantan Tengah-Timur, Sulawesi, Bali, NTB, NTT\n"
            "• WIT (UTC+9): Papua, Maluku",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text("⏳ Mengambil data cuaca dari BMKG...")
    
    try:
        # Parse kota dan waktu yang diminta (format: Kota1 jam1 Kota2 jam2 ...)
        city_data = []  # List of (city_name, hour)
        temp_name = []
        i = 0
        
        while i < len(context.args):
            arg = context.args[i]
            
            # Cek apakah arg adalah angka (jam)
            if arg.isdigit():
                # Ini adalah jam untuk kota sebelumnya
                if temp_name:
                    city_name = ' '.join(temp_name)
                    hour = int(arg)
                    if 0 <= hour <= 23:
                        city_data.append((city_name, hour))
                    else:
                        city_data.append((city_name, 6))  # Default 6 jika invalid
                    temp_name = []
                i += 1
            # Jika arg diawali huruf kapital dan ada temp_name, ini kota baru
            elif arg[0].isupper() and temp_name:
                # Simpan kota sebelumnya dengan default hour
                city_name = ' '.join(temp_name)
                city_data.append((city_name, 6))  # Default 6 AM
                temp_name = [arg]
                i += 1
            else:
                temp_name.append(arg)
                i += 1
        
        # Tambahkan kota terakhir jika ada
        if temp_name:
            city_name = ' '.join(temp_name)
            city_data.append((city_name, 6))  # Default 6 AM
        
        # Validasi maksimal 4 kota
        if len(city_data) > 4:
            await update.message.reply_text(
                "❌ Maksimal 4 kota untuk 1 artikel.\n\n"
                "Contoh: `/artikelkota Jakarta 09 Bandung 10 Surabaya 11 Denpasar 12`",
                parse_mode='Markdown'
            )
            return
        
        if not city_data:
            await update.message.reply_text(
                "❌ Tidak ada kota yang valid.\n\n"
                "Contoh: `/artikelkota Jakarta 09 Surabaya 10`",
                parse_mode='Markdown'
            )
            return
            await update.message.reply_text(
                "❌ Maksimal 4 kota untuk 1 artikel.\n\n"
                "Contoh: `/artikelkota Jakarta Bandung Surabaya Denpasar`",
                parse_mode='Markdown'
            )
            return
        
        # Reset selected cities
        city_selector.clear_selected_cities()
        
        # Tambahkan kota yang diminta
        not_found = []
        city_times_map = {}  # Menyimpan mapping city -> hour
        
        for city_name, hour in city_data:
            if not city_selector.add_specific_city(city_name):
                not_found.append(city_name)
            else:
                city_times_map[city_name] = hour
        
        # Jika ada kota yang tidak ditemukan
        if not_found:
            await update.message.reply_text(
                f"❌ Kota tidak ditemukan: {', '.join(not_found)}\n\n"
                f"Gunakan /carikota [nama kota] untuk mencari kota yang tersedia."
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
        
        # Ambil data cuaca dengan waktu yang dipilih
        weather_data = {}
        api = BMKGWeatherAPI(BMKG_API_BASE_URL)
        failed_cities = []
        
        for city_name, city_info in selected_cities.items():
            # Gunakan waktu yang dipilih atau default 6 jika tidak ada
            target_hour = city_times_map.get(city_name, 6)
            
            city_weather = api.get_city_weather(
                city_info['code'],
                target_hour,
                city_info['timezone_offset']
            )
            
            if city_weather:
                # Pastikan target_hour dan timezone tersimpan di weather_data
                city_weather['target_hour'] = target_hour
                city_weather['timezone'] = city_info['timezone']
                city_weather['timezone_offset'] = city_info['timezone_offset']
                weather_data[city_name] = city_weather
            else:
                failed_cities.append(city_name)
        
        # Jika ada kota yang gagal, coba ganti dengan kota random
        if failed_cities and len(weather_data) < 4:
            await update.message.reply_text(
                f"⚠️ Data cuaca tidak tersedia untuk: {', '.join(failed_cities)}\n"
                f"Mencoba kota alternatif..."
            )
            
            # Hitung kota yang masih dibutuhkan per timezone
            existing_tz = [info['timezone'] for info in weather_data.values()]
            needed = 4 - len(weather_data)
            
            # Clear selection dan tambah kota yang berhasil + random baru
            city_selector.clear_selected_cities()
            
            # Re-add kota yang berhasil
            for city_name in weather_data.keys():
                city_selector.add_specific_city(city_name)
            
            # Tambah random untuk yang kurang
            wib_needed = max(0, 2 - existing_tz.count('WIB'))
            wita_needed = max(0, 1 - existing_tz.count('WITA'))
            wit_needed = max(0, 1 - existing_tz.count('WIT'))
            
            total_needed = wib_needed + wita_needed + wit_needed
            if total_needed < needed:
                wib_needed += (needed - total_needed)
            
            city_selector.select_random_cities(
                total_cities=needed,
                wib_count=wib_needed,
                wita_count=wita_needed,
                wit_count=wit_needed
            )
            
            # Ambil data untuk kota random baru
            selected_cities = city_selector.get_selected_cities()
            for city_name, city_info in selected_cities.items():
                if city_name not in weather_data:
                    target_hour = city_times_map.get(city_name, 6)
                    city_weather = api.get_city_weather(
                        city_info['code'],
                        target_hour,
                        city_info['timezone_offset']
                    )
                    
                    if city_weather:
                        city_weather['target_hour'] = target_hour
                        city_weather['timezone'] = city_info['timezone']
                        city_weather['timezone_offset'] = city_info['timezone_offset']
                        weather_data[city_name] = city_weather
        
        if not weather_data or len(weather_data) < 4:
            await update.message.reply_text(
                "❌ Gagal mengambil data cuaca lengkap dari BMKG.\n"
                f"Hanya berhasil untuk {len(weather_data)} kota.\n\n"
                "Beberapa wilayah mungkin tidak didukung oleh API BMKG.\n"
                "Silakan coba dengan kota lain."
            )
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
        
        # Kirim gambar satelit terlebih dahulu
        try:
            filepath, _ = image_fetcher.download_image('satelit', force=True)
            if filepath and os.path.exists(filepath):
                with open(filepath, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="Citra Satelit Himawari-9 - Potensi Curah Hujan Indonesia"
                    )
        except Exception as e:
            print(f"Failed to send satellite image: {e}")
        
        # Format hasil - kirim judul terpisah dengan Markdown, artikel tanpa parsing
        escaped_title = escape_markdown(title, version=2)
        await update.message.reply_text(f"*{escaped_title}*", parse_mode='MarkdownV2')
        
        # Split artikel jika terlalu panjang (Telegram limit 4096 chars)
        # Kirim artikel TANPA parse_mode untuk menghindari error parsing
        if len(article) > 4000:
            chunks = [article[i:i+4000] for i in range(0, len(article), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(article)
        
        # Kirim ringkasan kota
        city_list = "\n".join([f"• {name}" for name in weather_data.keys()])
        await update.message.reply_text(f"📍 *Kota dalam artikel:*\n{city_list}", parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in artikel command: {e}")


async def cuacakota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /cuacakota"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    args_str = ' '.join(context.args) if context.args else 'None'
    
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, f"cuacakota {args_str}")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
        import traceback
        traceback.print_exc()
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /cuacakota {args_str}")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if not context.args:
        # Tampilkan menu pilihan timezone untuk memilih kota
        keyboard = [
            [
                InlineKeyboardButton("🌅 WIB (Jawa, Sumatra)", callback_data="cuaca_tz_WIB"),
                InlineKeyboardButton("🌄 WITA (Kalimantan, Sulawesi)", callback_data="cuaca_tz_WITA")
            ],
            [
                InlineKeyboardButton("🌇 WIT (Papua, Maluku)", callback_data="cuaca_tz_WIT"),
                InlineKeyboardButton("🌏 Semua Zona", callback_data="cuaca_tz_ALL")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🕐 *Info Cuaca Kota*\n\n"
            "Pilih zona waktu untuk melihat provinsi,\n"
            "atau ketik: `/cuacakota [nama kota] [jam]`\n\n"
            "📌 *Contoh:*\n"
            "• `/cuacakota Jakarta` - Pilih jam via button\n"
            "• `/cuacakota Jakarta 09` - Langsung jam 09:00\n\n"
            "📌 *Zona Waktu Indonesia:*\n"
            "• WIB (UTC+7): Jawa, Sumatra, Kalimantan Barat\n"
            "• WITA (UTC+8): Kalimantan Tengah-Timur, Sulawesi, Bali, NTB, NTT\n"
            "• WIT (UTC+9): Papua, Maluku",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Parse argumen: nama kota dan jam (opsional)
    args = list(context.args)
    selected_hour = None
    
    # Cek apakah argumen terakhir adalah angka (jam)
    if len(args) > 1 and args[-1].isdigit():
        hour_value = int(args[-1])
        # Validasi jam (0-23)
        if 0 <= hour_value <= 23:
            selected_hour = hour_value
            # Hapus jam dari args, sisanya adalah nama kota
            args = args[:-1]
        # Jika tidak valid, anggap sebagai bagian dari nama kota
    
    city_name = ' '.join(args).title()
    
    # Jika tidak ada jam yang dipilih, tampilkan button untuk memilih tanggal dulu
    if selected_hour is None:
        # Cari kota di database terlebih dahulu
        city_info = city_selector.search_city(city_name)
        
        if not city_info:
            await update.message.reply_text(
                f"❌ Kota '{city_name}' tidak ditemukan.\n\n"
                f"Gunakan /carikota {city_name} untuk mencari kota yang mirip."
            )
            return
        
        # Tampilkan button untuk memilih tanggal (hari ini atau besok)
        # Fix: Use WIB (UTC+7) instead of Server Time (UTC)
        now = datetime.utcnow() + timedelta(hours=7)
        today = now.strftime('%d %B %Y')
        tomorrow = (now + timedelta(days=1)).strftime('%d %B %Y')
        
        keyboard = [
            [InlineKeyboardButton(f"📅 Hari Ini ({today})", callback_data=f"cuaca_date_{city_name}_0")],
            [InlineKeyboardButton(f"📅 Besok ({tomorrow})", callback_data=f"cuaca_date_{city_name}_1")],
            [InlineKeyboardButton("« Kembali", callback_data="cuaca_back_prov")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📅 *Pilih Tanggal untuk {city_name}:*\n\n"
            f"Pilih tanggal untuk melihat prakiraan cuaca\n"
            f"(Zona waktu: {city_info['timezone']})",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Jika sudah ada jam, langsung tampilkan cuaca
    await update.message.reply_text(f"⏳ Mencari data cuaca {city_name} jam {selected_hour:02d}:00...")
    
    try:
        # Cari kota di database
        city_info = city_selector.search_city(city_name)
        
        if not city_info:
            await update.message.reply_text(
                f"❌ Kota '{city_name}' tidak ditemukan.\n\n"
                f"Gunakan /carikota {city_name} untuk mencari kota yang mirip."
            )
            return
        
        # Ambil data cuaca
        api = BMKGWeatherAPI(BMKG_API_BASE_URL)
        weather_data = api.get_city_weather(
            city_info['code'],
            selected_hour,  # Jam yang dipilih user
            city_info['timezone_offset']
        )
        
        if not weather_data:
            await update.message.reply_text(f"❌ Gagal mengambil data cuaca untuk {city_name}")
            return
        
        # Debug: Print weather_data structure
        print(f"Weather data keys: {weather_data.keys()}")
        print(f"Datetime type: {type(weather_data.get('datetime'))}")
        print(f"Datetime value: {weather_data.get('datetime')}")
        
        # Format hasil dengan error handling yang lebih baik
        try:
            # Gunakan tanggal sekarang + jam yang dipilih
            now = datetime.now()
            dt = now.replace(hour=selected_hour, minute=0, second=0, microsecond=0)
            
            # Jika jam yang dipilih sudah lewat hari ini, gunakan besok
            if dt < now:
                dt = dt + timedelta(days=1)
            
            # Format time
            formatted_time = f"{selected_hour:02d}:00"
            
            # Format tanggal dan hari - convert datetime ke string format yang benar
            if isinstance(dt, datetime):
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                day_name = generator.get_day_name(dt_str)
                formatted_date = generator.get_formatted_date(dt_str)
            else:
                # Fallback ke datetime sekarang
                dt = datetime.now()
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                day_name = generator.get_day_name(dt_str)
                formatted_date = generator.get_formatted_date(dt_str)
            
            timezone = weather_data.get('timezone', 'WIB')
            weather = weather_data.get('weather', 'N/A')
            temp = weather_data.get('temperature', 0)
            humidity = weather_data.get('humidity', 0)
            wind_speed = weather_data.get('wind_speed', 'N/A')
            wind_dir = weather_data.get('wind_direction', 'N/A')
            
            result = f"""
🌤️ *Cuaca {city_name}*

📅 {day_name}, {formatted_date}
🕐 {formatted_time} {timezone}

☁️ Kondisi: {weather}
🌡️ Suhu: {int(round(temp))}°C
💧 Kelembapan: {int(round(humidity))}%
💨 Angin: {wind_speed} km/jam dari {wind_dir}

Data dari BMKG Indonesia 🇮🇩
        """
        except Exception as format_error:
            print(f"Format error in cuacakota: {format_error}")
            import traceback
            traceback.print_exc()
            
            # Fallback sederhana
            result = f"""
🌤️ *Cuaca {city_name}*

☁️ Kondisi: {weather_data.get('weather', 'N/A')}
🌡️ Suhu: {int(round(weather_data.get('temperature', 0)))}°C
💧 Kelembapan: {int(round(weather_data.get('humidity', 0)))}%

Data dari BMKG Indonesia 🇮🇩
        """
        
        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in cuaca command: {e}")


async def carikota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /carikota"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    args_str = ' '.join(context.args) if context.args else 'None'
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, f"carikota {args_str}")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /carikota {args_str}")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan format: /carikota [nama kota]\n\n"
            "Contoh: /carikota Bandung"
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
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "kota")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /kota")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
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
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "random")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /random")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    await update.message.reply_text("🎲 Memilih 4 kota random...")
    
    try:
        # Clear kota lama dan pilih kota random baru
        city_selector.clear_selected_cities()
        
        # Pilih 4 kota random dengan distribusi: 2 WIB, 1 WITA, 1 WIT
        city_selector.select_random_cities(
            total_cities=4,
            wib_count=2,
            wita_count=1,
            wit_count=1
        )
        
        selected_cities = city_selector.get_selected_cities()
        
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
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "stats")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /stats")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Check if user is admin
    admin_username = os.getenv('ADMIN_USERNAME', 'hanyagwyangtau')
    
    # Check by Telegram username (without @)
    user_username = user.username if user.username else ""
    
    if user_username != admin_username:
        await update.message.reply_text(
            "❌ *Akses Ditolak*\n\n"
            "Command ini hanya untuk administrator.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Hitung statistik database
        total_cities = city_selector.count_cities_by_timezone()
        
        # Konversi ke integer untuk memastikan format number bekerja
        wib_count = int(total_cities.get('WIB', 0))
        wita_count = int(total_cities.get('WITA', 0))
        wit_count = int(total_cities.get('WIT', 0))
        
        result_text = "📊 *Statistik Database*\n\n"
        result_text += f"🌍 Total kota: *{wib_count + wita_count + wit_count:,}*\n\n"
        result_text += "*Per Zona Waktu:*\n"
        result_text += f"• WIB (UTC+7): {wib_count:,} kota\n"
        result_text += f"• WITA (UTC+8): {wita_count:,} kota\n"
        result_text += f"• WIT (UTC+9): {wit_count:,} kota\n\n"
        
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


async def userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /userstats - Statistik pengguna bot"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "userstats")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /userstats")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Check if user is admin (using same credentials from .env)
    admin_username = os.getenv('ADMIN_USERNAME', 'hanyagwyangtau')
    
    # Check by Telegram username (without @)
    user_username = user.username if user.username else ""
    
    if user_username != admin_username:
        await update.message.reply_text(
            "❌ *Akses Ditolak*\n\n"
            "Command ini hanya untuk administrator.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Get statistics
        total_users = user_db.get_total_users()
        command_stats = user_db.get_command_stats()
        most_active = user_db.get_most_active_users(limit=5)
        
        # Build result text
        result_text = "👥 *Statistik Pengguna Bot*\n\n"
        result_text += f"📊 Total pengguna: *{total_users}*\n\n"
        
        # Command statistics
        if command_stats:
            result_text += "*📈 Command Terpopuler:*\n"
            for i, (cmd, count) in enumerate(list(command_stats.items())[:5], 1):
                result_text += f"{i}\\. /{cmd}: {count}x\n"
            result_text += "\n"
        
        # Most active users
        if most_active:
            result_text += "*🔥 Pengguna Teraktif:*\n"
            for i, user_info in enumerate(most_active, 1):
                # Escape special characters untuk Markdown
                name = escape_markdown(user_info['name'], version=2) if user_info['name'] else "N/A"
                username = f"@{escape_markdown(user_info['username'], version=2)}" if user_info['username'] else "N/A"
                result_text += f"{i}\\. {name} \\({username}\\)\n"
                result_text += f"   📊 {user_info['total_commands']} commands\n"
            result_text += "\n"
        
        # Your stats
        your_info = user_db.get_user_info(user.id)
        if your_info:
            # Escape dates karena ada karakter '-' dan ':'
            first_seen = escape_markdown(str(your_info['first_seen']), version=2)
            last_seen = escape_markdown(str(your_info['last_seen']), version=2)
            
            result_text += "*📱 Statistik Anda:*\n"
            result_text += f"• Total command: {your_info['total_commands']}\n"
            result_text += f"• Pertama kali: {first_seen}\n"
            result_text += f"• Terakhir: {last_seen}\n"
        
        await update.message.reply_text(result_text, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in userstats command: {e}")


async def satelit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /satelit - Citra satelit Himawari"""
    init_components()
    
    # Log user activity to database
    user = update.effective_user
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, "satelit")
        else:
            print("⚠️  WARNING: user_db is None! Database logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging to database: {e}")
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Command: /satelit")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    await update.message.reply_text("📥 Mengambil citra satelit dari BMKG...")
    
    try:
        # Download gambar satelit
        filepath, is_updated = image_fetcher.download_image('satelit', force=True)
        
        if not filepath or not os.path.exists(filepath):
            await update.message.reply_text("❌ Gagal mengambil citra satelit dari BMKG. Silakan coba lagi nanti.")
            return
        
        # Kirim gambar
        caption = (
            "🛰️ *Citra Satelit Himawari-9*\n\n"
            "*Potensi Curah Hujan Indonesia*\n\n"
            f"📅 Update: {datetime.now().strftime('%d %B %Y, %H:%M WIB')}\n"
            "📊 Sumber: BMKG - Badan Meteorologi Klimatologi dan Geofisika\n\n"
            "*Informasi:*\n"
            "🛰️ Satelit: Himawari-9\n"
            "📡 Citra: Infrared (IR)\n"
            "🌧️ Analisis: Potensi curah hujan\n\n"
            "Produk turunan Himawari-9 Potential Rainfall adalah produk yang dapat digunakan untuk mengestimasi potensi curah hujan, yang disajikan berdasarkan kategori ringan, sedang, lebat, hingga sangat lebat, dengan menggunakan hubungan antara suhu puncak awan dengan curah hujan yang berpotensi dihasilkan.\n\n"
            "Data dari BMKG Indonesia https://www.bmkg.go.id"
        )
        
        with open(filepath, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode='Markdown'
            )
        
        # Info tambahan jika ada update
        if is_updated:
            await update.message.reply_text(
                "✅ *Citra terbaru berhasil diambil!*\n\n"
                "Ini adalah versi terbaru dari satelit Himawari-9.",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in satelit command: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk button callback"""
    init_components()
    query = update.callback_query
    await query.answer()
    
    # Log user activity to database
    user = update.effective_user
    
    try:
        if user_db is not None:
            user_db.log_user_activity(user.id, user.username, user.full_name, f"callback_{query.data}")
        else:
            print("⚠️  WARNING: user_db is None! Callback logging skipped.")
    except Exception as e:
        print(f"❌ ERROR logging callback to database: {e}")
        import traceback
        traceback.print_exc()
    
    # Log user info ke terminal
    print(f"\n{'='*60}")
    print(f"📱 Callback: {query.data}")
    print(f"👤 User ID: {user.id}")
    print(f"📝 Username: @{user.username if user.username else 'N/A'}")
    print(f"👨 Name: {user.full_name}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # -------------------------------------------------------------
    # SESSION MANAGEMENT FOR VERCEL (Stateless)
    # -------------------------------------------------------------
    # Restore session from SQLite if context is empty
    # Always attempt to restore if user_data is empty (new request)
    if user_db and not context.user_data: 
        try:
            session_data = user_db.get_session(user.id)
            if session_data:
                logger.info(f"🔄 Restoring session for user {user.id}")
                context.user_data.update(session_data)
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
    # -------------------------------------------------------------

    data = query.data
    
    # Handle pilih timezone untuk cuaca kota
    if data.startswith("cuaca_tz_"):
        timezone = data.split("_")[2]
        
        # Simpan timezone filter ke context
        context.user_data['cuaca_timezone_filter'] = timezone if timezone != "ALL" else None
        
        # Ambil semua provinsi
        all_provinces = city_selector.db.get_all_provinces()
        
        # Filter provinsi berdasarkan timezone
        if timezone == "ALL":
            provinces = all_provinces
        else:
            tz_mapping = city_selector.db.timezone_mapping
            provinces = [p for p in all_provinces if tz_mapping.get(p['code'], ('', 0))[0] == timezone]
        
        if not provinces:
            await query.edit_message_text(f"❌ Tidak ada provinsi di zona {timezone}")
            return
        
        # Buat keyboard untuk provinsi
        keyboard = []
        for i in range(0, len(provinces), 2):
            row = []
            for j in range(2):
                if i + j < len(provinces):
                    prov = provinces[i + j]
                    row.append(InlineKeyboardButton(prov['name'], callback_data=f"cuaca_prov_{prov['code']}"))
            keyboard.append(row)
        
        # Tambahkan button kembali
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data="cuaca_back_tz")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tz_name = {
            'WIB': 'WIB (UTC+7)',
            'WITA': 'WITA (UTC+8)',
            'WIT': 'WIT (UTC+9)',
            'ALL': 'Semua Zona'
        }.get(timezone, timezone)
        
        await query.edit_message_text(
            f"📍 *Pilih Provinsi - {tz_name}:*\n\n"
            f"Total: {len(provinces)} provinsi",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle pilih provinsi untuk cuaca
    if data.startswith("cuaca_prov_"):
        province_code = data.split("_")[2]
        cities = city_selector.db.get_cities_by_province(province_code)
        
        if not cities:
            await query.edit_message_text("❌ Tidak ada kota ditemukan di provinsi ini.")
            return
        
        # Buat keyboard untuk kota (max 100)
        keyboard = []
        for i in range(0, min(len(cities), 100), 2):
            row = []
            for j in range(2):
                if i + j < len(cities) and i + j < 100:
                    city = cities[i + j]
                    row.append(InlineKeyboardButton(city['name'], callback_data=f"cuaca_selectcity_{city['name']}"))
            keyboard.append(row)
        
        # Tambahkan button kembali
        keyboard.append([InlineKeyboardButton("« Kembali ke Provinsi", callback_data="cuaca_back_prov")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        province_name = city_selector.db.get_all_provinces()
        province_name = next((p['name'] for p in province_name if p['code'] == province_code), "Provinsi")
        
        await query.edit_message_text(
            f"📍 *Pilih Kota di {province_name}:*\n\n"
            f"Total: {len(cities)} kota",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle pilih kota untuk cuaca (setelah pilih dari provinsi)
    if data.startswith("cuaca_selectcity_"):
        city_name = data.split("_", 2)[2]
        
        # Tampilkan keyboard untuk memilih tanggal (hari ini atau besok)
        # Fix: Use WIB (UTC+7) instead of Server Time (UTC)
        now = datetime.utcnow() + timedelta(hours=7)
        today = now.strftime('%d %B %Y')
        tomorrow = (now + timedelta(days=1)).strftime('%d %B %Y')
        
        keyboard = [
            [InlineKeyboardButton(f"📅 Hari Ini ({today})", callback_data=f"cuaca_date_{city_name}_0")],
            [InlineKeyboardButton(f"📅 Besok ({tomorrow})", callback_data=f"cuaca_date_{city_name}_1")],
            [InlineKeyboardButton("« Kembali", callback_data="cuaca_back_prov")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📅 *Pilih Tanggal untuk {city_name}:*\n\n"
            f"Pilih tanggal untuk melihat prakiraan cuaca",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle pilih tanggal untuk cuaca
    if data.startswith("cuaca_date_"):
        parts = data.split("_")
        city_name = "_".join(parts[2:-1])
        days_offset = int(parts[-1])  # 0 = hari ini, 1 = besok
        
        # Simpan pilihan tanggal ke context
        context.user_data['cuaca_days_offset'] = days_offset
        context.user_data['cuaca_city_name'] = city_name
        
        # --- SAVE SESSION (To persist date selection) ---
        if user_db:
            try:
                user_db.update_session(query.from_user.id, context.user_data)
                logger.info(f"💾 Session cuaca saved for user {query.from_user.id} (Offset: {days_offset})")
            except Exception as e:
                logger.error(f"Failed to save cuaca session: {e}")
        # -----------------------------------------------
        
        # Tampilkan keyboard untuk memilih jam
        keyboard = []
        hours = list(range(0, 24))
        
        # Buat 4 kolom button
        for i in range(0, len(hours), 4):
            row = []
            for j in range(4):
                if i + j < len(hours):
                    hour = hours[i + j]
                    row.append(InlineKeyboardButton(
                        f"{hour:02d}:00",
                        callback_data=f"cuaca_{city_name}_{hour}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data=f"cuaca_selectcity_{city_name}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Format tanggal yang dipilih
        # Fix: Use WIB (UTC+7)
        target_date = (datetime.utcnow() + timedelta(hours=7)) + timedelta(days=days_offset)
        date_str = target_date.strftime('%d %B %Y')
        
        await query.edit_message_text(
            f"🕐 *Pilih Waktu untuk {city_name}:*\n\n"
            f"📅 Tanggal: {date_str}\n"
            f"Pilih jam untuk data cuaca",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle tampilkan cuaca dengan jam yang dipilih
    if data.startswith("cuaca_") and not data.startswith(("cuaca_tz_", "cuaca_prov_", "cuaca_selectcity_", "cuaca_date_", "cuaca_back_")):
        parts = data.split("_")
        city_name = "_".join(parts[1:-1])
        selected_hour = int(parts[-1])
        
        await query.edit_message_text(f"⏳ Mencari data cuaca {city_name} jam {selected_hour:02d}:00...")
        
        try:
            # Cari kota di database
            city_info = city_selector.search_city(city_name)
            
            if not city_info:
                await query.message.reply_text(
                    f"❌ Kota '{city_name}' tidak ditemukan.\n\n"
                    f"Gunakan /carikota {city_name} untuk mencari kota yang mirip."
                )
                return
            
            # Ambil data cuaca
            api = BMKGWeatherAPI(BMKG_API_BASE_URL)
            weather_data = api.get_city_weather(
                city_info['code'],
                selected_hour,
                city_info['timezone_offset']
            )
            
            if not weather_data:
                await query.message.reply_text(f"❌ Gagal mengambil data cuaca untuk {city_name}")
                return
            
            # Format hasil dengan error handling
            try:
                # Gunakan tanggal yang dipilih user dari context
                # Fix: Use WIB (UTC+7)
                now = datetime.utcnow() + timedelta(hours=7)
                days_offset = context.user_data.get('cuaca_days_offset', 0)
                
                # Buat datetime berdasarkan pilihan user
                # ABAIKAN datetime dari API, gunakan tanggal hari ini + offset + jam pilihan
                dt = now.replace(hour=selected_hour, minute=0, second=0, microsecond=0)
                dt = dt + timedelta(days=days_offset)
                
                # Clear context setelah digunakan
                if 'cuaca_days_offset' in context.user_data:
                    del context.user_data['cuaca_days_offset']
                if 'cuaca_city_name' in context.user_data:
                    del context.user_data['cuaca_city_name']
                
                # Format time
                formatted_time = f"{selected_hour:02d}:00"
                
                # Format tanggal dan hari - convert datetime ke string format yang benar
                if isinstance(dt, datetime):
                    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    day_name = generator.get_day_name(dt_str)
                    formatted_date = generator.get_formatted_date(dt_str)
                else:
                    dt = datetime.utcnow() + timedelta(hours=7)
                    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    day_name = generator.get_day_name(dt_str)
                    formatted_date = generator.get_formatted_date(dt_str)
                
                timezone = weather_data.get('timezone', 'WIB')
                weather = weather_data.get('weather', 'N/A')
                temp = weather_data.get('temperature', 0)
                humidity = weather_data.get('humidity', 0)
                wind_speed = weather_data.get('wind_speed', 'N/A')
                wind_dir = weather_data.get('wind_direction', 'N/A')
                
                result = f"""
🌤️ *Cuaca {city_name}*

📅 {day_name}, {formatted_date}
🕐 {formatted_time} {timezone}

☁️ Kondisi: {weather}
🌡️ Suhu: {int(round(temp))}°C
💧 Kelembapan: {int(round(humidity))}%
💨 Angin: {wind_speed} km/jam dari {wind_dir}

Data dari BMKG Indonesia 🇮🇩
        """
            except Exception as format_error:
                print(f"Format error in cuaca callback: {format_error}")
                import traceback
                traceback.print_exc()
                
                result = f"""
🌤️ *Cuaca {city_name}*

☁️ Kondisi: {weather_data.get('weather', 'N/A')}
🌡️ Suhu: {int(round(weather_data.get('temperature', 0)))}°C
💧 Kelembapan: {int(round(weather_data.get('humidity', 0)))}%

Data dari BMKG Indonesia 🇮🇩
        """
            
            await query.message.reply_text(result, parse_mode='Markdown')
            
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
            print(f"Error in cuaca callback: {e}")
        
        return
    
    # Handle back to timezone untuk cuaca
    if data == "cuaca_back_tz":
        keyboard = [
            [
                InlineKeyboardButton("🌅 WIB (Jawa, Sumatra)", callback_data="cuaca_tz_WIB"),
                InlineKeyboardButton("🌄 WITA (Kalimantan, Sulawesi)", callback_data="cuaca_tz_WITA")
            ],
            [
                InlineKeyboardButton("🌇 WIT (Papua, Maluku)", callback_data="cuaca_tz_WIT"),
                InlineKeyboardButton("🌏 Semua Zona", callback_data="cuaca_tz_ALL")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🕐 *Info Cuaca Kota*\n\n"
            "Pilih zona waktu untuk melihat provinsi\n\n"
            "📌 *Zona Waktu Indonesia:*\n"
            "• WIB (UTC+7): Jawa, Sumatra, Kalimantan Barat\n"
            "• WITA (UTC+8): Kalimantan Tengah-Timur, Sulawesi, Bali, NTB, NTT\n"
            "• WIT (UTC+9): Papua, Maluku",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle back to provinsi untuk cuaca
    if data == "cuaca_back_prov":
        timezone_filter = context.user_data.get('cuaca_timezone_filter', None)
        
        all_provinces = city_selector.db.get_all_provinces()
        
        if timezone_filter:
            tz_mapping = city_selector.db.timezone_mapping
            provinces = [p for p in all_provinces if tz_mapping.get(p['code'], ('', 0))[0] == timezone_filter]
        else:
            provinces = all_provinces
        
        keyboard = []
        for i in range(0, len(provinces), 2):
            row = []
            for j in range(2):
                if i + j < len(provinces):
                    prov = provinces[i + j]
                    row.append(InlineKeyboardButton(prov['name'], callback_data=f"cuaca_prov_{prov['code']}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data="cuaca_back_tz")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tz_info = ""
        if timezone_filter:
            tz_name = {
                'WIB': 'WIB (UTC+7)',
                'WITA': 'WITA (UTC+8)',
                'WIT': 'WIT (UTC+9)'
            }.get(timezone_filter, timezone_filter)
            tz_info = f" - {tz_name}"
        
        await query.edit_message_text(
            f"📍 *Pilih Provinsi{tz_info}:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle pilih timezone untuk artikel
    if data.startswith("tz_"):
        timezone = data.split("_")[1]
        
        # Load session from DB first
        if user_db and 'selected_cities' not in context.user_data:
            session_data = user_db.get_session(query.from_user.id)
            if session_data:
                context.user_data.update(session_data)
        
        # Set timezone filter (overwrite session value if any)
        context.user_data['timezone_filter'] = timezone if timezone != "ALL" else None

        # Initialize selected_cities dan city_times jika belum ada
        if 'selected_cities' not in context.user_data:
            context.user_data['selected_cities'] = []
        if 'city_times' not in context.user_data:
            context.user_data['city_times'] = {}
            
        # --- SAVE SESSION ---
        if user_db:
            try:
                user_db.update_session(query.from_user.id, context.user_data)
                logger.info(f"💾 Session saved for user {query.from_user.id} (TZ: {timezone})")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
        # --------------------
        
        # Ambil semua provinsi
        all_provinces = city_selector.db.get_all_provinces()
        
        # Filter provinsi berdasarkan timezone
        if timezone == "ALL":
            provinces = all_provinces
        else:
            # Filter berdasarkan mapping timezone
            tz_mapping = city_selector.db.timezone_mapping
            provinces = [p for p in all_provinces if tz_mapping.get(p['code'], ('', 0))[0] == timezone]
        
        if not provinces:
            await query.edit_message_text(f"❌ Tidak ada provinsi di zona {timezone}")
            return
        
        # Buat keyboard untuk provinsi
        keyboard = []
        for i in range(0, len(provinces), 2):
            row = []
            for j in range(2):
                if i + j < len(provinces):
                    prov = provinces[i + j]
                    row.append(InlineKeyboardButton(
                        prov['name'], 
                        callback_data=f"prov_{prov['code']}"
                    ))
            keyboard.append(row)
        
        # Tambahkan button kembali dan random
        keyboard.append([
            InlineKeyboardButton("« Kembali ke Zona Waktu", callback_data="back_timezone"),
            InlineKeyboardButton("🎲 Random", callback_data="artikel_random")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tz_name = {
            'WIB': 'WIB (UTC+7)',
            'WITA': 'WITA (UTC+8)',
            'WIT': 'WIT (UTC+9)',
            'ALL': 'Semua Zona'
        }.get(timezone, timezone)
        
        await query.edit_message_text(
            f"📍 *Pilih Provinsi - {tz_name}:*\n\n"
            f"Total: {len(provinces)} provinsi",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle pilih provinsi
    if data.startswith("prov_"):
        province_code = data.split("_")[1]
        cities = city_selector.db.get_cities_by_province(province_code)
        
        if not cities:
            await query.edit_message_text("❌ Tidak ada kota ditemukan di provinsi ini.")
            return
        
        # Buat keyboard untuk kota (max 100 button per message limit Telegram)
        keyboard = []
        for i in range(0, min(len(cities), 100), 2):
            row = []
            for j in range(2):
                if i + j < len(cities) and i + j < 100:
                    city = cities[i + j]
                    row.append(InlineKeyboardButton(
                        city['name'][:30],  # Limit 30 chars
                        callback_data=f"city_{city['name']}"
                    ))
            keyboard.append(row)
        
        # Tambahkan button kembali
        keyboard.append([InlineKeyboardButton("« Kembali ke Provinsi", callback_data="back_prov")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        province_name = city_selector.db.get_all_provinces()
        province_name = next((p['name'] for p in province_name if p['code'] == province_code), "Provinsi")
        
        await query.edit_message_text(
            f"📍 *Pilih Kota di {province_name}:*\n\n"
            f"Total: {len(cities)} kota",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle pilih kota
    elif data.startswith("city_"):
        city_name = data.split("_", 1)[1]
        
        # Tampilkan keyboard untuk memilih jam
        keyboard = []
        
        # Buat button untuk SEMUA jam (00:00 - 23:00)
        hours = list(range(0, 24))  # Semua jam dari 0-23
        
        # Buat 4 kolom button agar muat semua jam
        for i in range(0, len(hours), 4):
            row = []
            for j in range(4):
                if i + j < len(hours):
                    hour = hours[i + j]
                    row.append(InlineKeyboardButton(
                        f"{hour:02d}:00",
                        callback_data=f"time_{city_name}_{hour}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data="back_prov")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🕐 *Pilih Waktu untuk {city_name}:*\n\n"
            f"Pilih jam untuk data cuaca:\n"
            f"(Jam dalam zona waktu lokal kota)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle pilih waktu untuk kota
    elif data.startswith("time_"):
        parts = data.split("_")
        city_name = "_".join(parts[1:-1])  # Handle kota dengan underscore
        hour = int(parts[-1])
        
        # Simpan kota dan waktu ke context user_data
        if 'selected_cities' not in context.user_data:
            context.user_data['selected_cities'] = []
        if 'city_times' not in context.user_data:
            context.user_data['city_times'] = {}
        
        # Cek apakah kota sudah ada
        city_exists = city_name in [c.split(' (')[0] for c in context.user_data['selected_cities']]
        
        if not city_exists:
            context.user_data['selected_cities'].append(f"{city_name} ({hour:02d}:00)")
            context.user_data['city_times'][city_name] = hour
            
            # --- SAVE SESSION ---
            if user_db:
                try:
                    user_db.update_session(query.from_user.id, context.user_data)
                    logger.info(f"💾 Session saved for user {query.from_user.id}")
                except Exception as e:
                    logger.error(f"Failed to save session: {e}")
            # --------------------
        
        selected = context.user_data['selected_cities']
        
        # Buat keyboard untuk opsi selanjutnya
        keyboard = []
        
        if len(selected) < 4:
            keyboard.append([InlineKeyboardButton("➕ Tambah Kota Lain", callback_data="back_prov")])
        
        keyboard.append([InlineKeyboardButton("✅ Generate Artikel Sekarang", callback_data="gen_artikel")])
        
        if len(selected) > 0:
            keyboard.append([InlineKeyboardButton("🗑️ Hapus Semua Pilihan", callback_data="clear_cities")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        city_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(selected)])
        
        await query.edit_message_text(
            f"✅ *Kota & Waktu dipilih: {city_name} ({hour:02d}:00)*\n\n"
            f"📋 *Daftar kota ({len(selected)}/4):*\n{city_list}\n\n"
            f"{'ℹ️ Pilih maksimal 4 kota' if len(selected) < 4 else '✅ Sudah 4 kota'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle back to provinsi
    elif data == "back_prov":
        # Cek apakah ada timezone filter
        timezone_filter = context.user_data.get('timezone_filter', None)
        
        all_provinces = city_selector.db.get_all_provinces()
        
        # Filter provinsi jika ada timezone filter
        if timezone_filter:
            tz_mapping = city_selector.db.timezone_mapping
            provinces = [p for p in all_provinces if tz_mapping.get(p['code'], ('', 0))[0] == timezone_filter]
        else:
            provinces = all_provinces
        
        keyboard = []
        for i in range(0, len(provinces), 2):
            row = []
            for j in range(2):
                if i + j < len(provinces):
                    prov = provinces[i + j]
                    row.append(InlineKeyboardButton(
                        prov['name'], 
                        callback_data=f"prov_{prov['code']}"
                    ))
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("« Kembali ke Zona Waktu", callback_data="back_timezone"),
            InlineKeyboardButton("🎲 Random", callback_data="artikel_random")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selected_info = ""
        if 'selected_cities' in context.user_data and context.user_data['selected_cities']:
            selected = context.user_data['selected_cities']
            selected_info = f"\n\n📋 Kota terpilih: {len(selected)}"
        
        tz_info = ""
        if timezone_filter:
            tz_name = {
                'WIB': 'WIB (UTC+7)',
                'WITA': 'WITA (UTC+8)',
                'WIT': 'WIT (UTC+9)'
            }.get(timezone_filter, timezone_filter)
            tz_info = f" - {tz_name}"
        
        await query.edit_message_text(
            f"📍 *Pilih Provinsi{tz_info}:*{selected_info}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle back to timezone
    elif data == "back_timezone":
        context.user_data['timezone_filter'] = None
        
        keyboard = [
            [
                InlineKeyboardButton("� Indonesia (Semua Zona)", callback_data="tz_ALL")
            ],
            [
                InlineKeyboardButton("🌅 WIB", callback_data="tz_WIB"),
                InlineKeyboardButton("🌄 WITA", callback_data="tz_WITA"),
                InlineKeyboardButton("🌇 WIT", callback_data="tz_WIT")
            ],
            [InlineKeyboardButton("🎲 Pilih Random", callback_data="artikel_random")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selected_info = ""
        if 'selected_cities' in context.user_data and context.user_data['selected_cities']:
            selected = context.user_data['selected_cities']
            selected_info = f"\n\n📋 Kota terpilih: {len(selected)}"
        
        await query.edit_message_text(
            f"🕐 *Pilih Zona Waktu:*{selected_info}\n\n"
            "📌 *Zona Waktu Indonesia:*\n"
            "• WIB (UTC+7): Jawa, Sumatra, Kalimantan Barat\n"
            "• WITA (UTC+8): Kalimantan Tengah-Timur, Sulawesi, Bali, NTB, NTT\n"
            "• WIT (UTC+9): Papua, Maluku",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle clear cities
    elif data == "clear_cities":
        context.user_data['selected_cities'] = []
        context.user_data['city_times'] = {}
        
        # --- CLEAR SESSION ---
        if user_db:
            try:
                user_db.clear_session(query.from_user.id)
                logger.info(f"🗑️ Session cleared for user {query.from_user.id}")
            except Exception as e:
                logger.error(f"Failed to clear session: {e}")
        # ---------------------
        
        keyboard = [[InlineKeyboardButton("« Kembali ke Provinsi", callback_data="back_prov")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ *Semua pilihan dihapus*\n\nSilakan pilih kota lagi.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle generate artikel
    elif data == "gen_artikel":
        selected_cities = context.user_data.get('selected_cities', [])
        city_times = context.user_data.get('city_times', {})
        
        if not selected_cities:
            await query.edit_message_text("❌ Belum ada kota yang dipilih!")
            return
        
        await query.edit_message_text("⏳ Mengambil data cuaca dari BMKG...")
        
        try:
            # Reset city selector
            city_selector.clear_selected_cities()
            
            # Tambahkan kota yang dipilih (tanpa info waktu)
            not_found = []
            city_names_only = [c.split(' (')[0] for c in selected_cities]
            
            for city_name in city_names_only:
                if not city_selector.add_specific_city(city_name):
                    not_found.append(city_name)
            
            if not_found:
                await query.message.reply_text(
                    f"❌ Kota tidak ditemukan: {', '.join(not_found)}"
                )
                return
            
            # Jika kurang dari 4, tambahkan random
            selected = city_selector.get_selected_cities()
            if len(selected) < 4:
                remaining = 4 - len(selected)
                await query.message.reply_text(f"ℹ️ Menambahkan {remaining} kota random...")
                
                existing_tz = [info['timezone'] for info in selected.values()]
                wib_needed = max(0, 2 - existing_tz.count('WIB'))
                wita_needed = max(0, 1 - existing_tz.count('WITA'))
                wit_needed = max(0, 1 - existing_tz.count('WIT'))
                
                total_needed = wib_needed + wita_needed + wit_needed
                if total_needed < remaining:
                    wib_needed += (remaining - total_needed)
                
                city_selector.select_random_cities(
                    total_cities=remaining,
                    wib_count=wib_needed,
                    wita_count=wita_needed,
                    wit_count=wit_needed
                )
                
                selected = city_selector.get_selected_cities()
            
            # Ambil data cuaca dengan waktu yang dipilih
            weather_data = {}
            api = BMKGWeatherAPI(BMKG_API_BASE_URL)
            failed_cities = []
            
            for city_name, city_info in selected.items():
                # Gunakan waktu yang dipilih atau default 6 jika tidak ada
                target_hour = city_times.get(city_name, 6)
                
                city_weather = api.get_city_weather(
                    city_info['code'],
                    target_hour,
                    city_info['timezone_offset']
                )
                
                if city_weather:
                    # Pastikan target_hour dan timezone tersimpan di weather_data
                    city_weather['target_hour'] = target_hour
                    city_weather['timezone'] = city_info['timezone']
                    city_weather['timezone_offset'] = city_info['timezone_offset']
                    weather_data[city_name] = city_weather
                else:
                    failed_cities.append(city_name)
            
            # Jika ada kota yang gagal, coba ganti dengan kota random
            if failed_cities and len(weather_data) < 4:
                await query.message.reply_text(
                    f"⚠️ Data tidak tersedia untuk: {', '.join(failed_cities)}\n"
                    f"Mencoba kota alternatif..."
                )
                
                # Hitung kota yang masih dibutuhkan
                existing_tz = [info['timezone'] for info in weather_data.values()]
                needed = 4 - len(weather_data)
                
                # Clear dan re-add kota yang berhasil
                city_selector.clear_selected_cities()
                for city_name in weather_data.keys():
                    city_selector.add_specific_city(city_name)
                
                # Tambah random untuk yang kurang
                wib_needed = max(0, 2 - existing_tz.count('WIB'))
                wita_needed = max(0, 1 - existing_tz.count('WITA'))
                wit_needed = max(0, 1 - existing_tz.count('WIT'))
                
                total_needed = wib_needed + wita_needed + wit_needed
                if total_needed < needed:
                    wib_needed += (needed - total_needed)
                
                city_selector.select_random_cities(
                    total_cities=needed,
                    wib_count=wib_needed,
                    wita_count=wita_needed,
                    wit_count=wit_needed
                )
                
                # Ambil data untuk kota random baru
                selected = city_selector.get_selected_cities()
                for city_name, city_info in selected.items():
                    if city_name not in weather_data:
                        target_hour = city_times.get(city_name, 6)
                        city_weather = api.get_city_weather(
                            city_info['code'],
                            target_hour,
                            city_info['timezone_offset']
                        )
                        
                        if city_weather:
                            city_weather['target_hour'] = target_hour
                            city_weather['timezone'] = city_info['timezone']
                            city_weather['timezone_offset'] = city_info['timezone_offset']
                            weather_data[city_name] = city_weather
            
            if not weather_data or len(weather_data) < 4:
                await query.message.reply_text(
                    "❌ Gagal mengambil data cuaca lengkap.\n"
                    f"Hanya berhasil untuk {len(weather_data)} kota."
                )
                return
            
            # Generate artikel
            article = generator.generate_article(weather_data)
            title = generator.generate_title(weather_data)
            
            # Enhance dengan AI
            if ai_generator:
                try:
                    await query.message.reply_text("🤖 Meningkatkan artikel dengan AI...")
                    article, ai_title = ai_generator.enhance_article(article, weather_data)
                    if ai_title:
                        title = ai_title
                except Exception as e:
                    print(f"AI enhancement failed: {e}")
            
            # Kirim hasil
            escaped_title = escape_markdown(title, version=2)
            await query.message.reply_text(f"*{escaped_title}*", parse_mode='MarkdownV2')
            
            if len(article) > 4000:
                chunks = [article[i:i+4000] for i in range(0, len(article), 4000)]
                for chunk in chunks:
                    await query.message.reply_text(chunk)
            else:
                await query.message.reply_text(article)
            
            city_list = "\n".join([f"• {name}" for name in weather_data.keys()])
            await query.message.reply_text(
                f"📍 *Kota dalam artikel:*\n{city_list}", 
                parse_mode='Markdown'
            )
            
            # Clear selection
            context.user_data['selected_cities'] = []
            context.user_data['city_times'] = {}
            
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
            print(f"Error in generate artikel: {e}")
    
    # Handle artikel random
    elif data == "artikel_random":
        await query.edit_message_text("⏳ Mengambil data cuaca dari BMKG...")
        
        try:
            initialize_cities(force_new=True)
            selected_cities = CITY_CODES
            
            # Ambil data cuaca dengan auto-replacement untuk kota yang gagal
            weather_data = fetch_all_cities_weather(selected_cities, auto_replace_failed=True)
            
            if not weather_data or len(weather_data) < 4:
                await query.message.reply_text(
                    "❌ Gagal mengambil data cuaca lengkap.\n"
                    "Silakan coba lagi."
                )
                return
            
            article = generator.generate_article(weather_data)
            title = generator.generate_title(weather_data)
            
            if ai_generator:
                try:
                    await query.message.reply_text("🤖 Meningkatkan artikel dengan AI...")
                    article, ai_title = ai_generator.enhance_article(article, weather_data)
                    if ai_title:
                        title = ai_title
                except Exception as e:
                    print(f"AI enhancement failed: {e}")
            
            escaped_title = escape_markdown(title, version=2)
            await query.message.reply_text(f"*{escaped_title}*", parse_mode='MarkdownV2')
            
            if len(article) > 4000:
                chunks = [article[i:i+4000] for i in range(0, len(article), 4000)]
                for chunk in chunks:
                    await query.message.reply_text(chunk)
            else:
                await query.message.reply_text(article)
            
            city_list = "\n".join([f"• {name}" for name in weather_data.keys()])
            await query.message.reply_text(
                f"📍 *Kota dalam artikel:*\n{city_list}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
            print(f"Error in artikel random: {e}")
        
    # Handle weather warning (ekstrem)
    elif data.startswith("warn_day_"):
        offset = int(data.split("_")[-1])
        
        day_labels = ["Hari Ini", "Besok", "Lusa"]
        day_label = day_labels[offset]
        
        # Calculate date (WIB)
        target_date = datetime.utcnow() + timedelta(hours=7) + timedelta(days=offset)
        date_str = target_date.strftime('%d %B %Y')
        
        await query.edit_message_text(f"⏳ Mengambil data cuaca ekstrem untuk {day_label} ({date_str})...")
        
        try:
            warnings = image_fetcher.fetch_extreme_weather_data(day_offset=offset)
            
            if not warnings:
                msg = f"✅ *Tidak ada peringatan cuaca ekstrem* untuk {day_label} ({date_str})."
                keyboard = [
                    [InlineKeyboardButton("📅 Hari Ini", callback_data="warn_day_0")],
                    [InlineKeyboardButton("📅 Besok", callback_data="warn_day_1")],
                    [InlineKeyboardButton("📅 Lusa", callback_data="warn_day_2")]
                ]
            else:
                msg = f"⚠️ *Peringatan Cuaca Ekstrem {day_label} ({date_str})*\n\n"
                msg += f"Ditemukan {len(warnings)} peringatan:\n\n"
                
                limit = 30
                sorted_warnings = sorted(warnings, key=lambda x: x.get('region', x.get('province', 'N/A')))
                
                for i, w in enumerate(sorted_warnings):
                    if i >= limit:
                        msg += f"\n... dan {len(warnings) - limit} lainnya."
                        break
                    
                    status = w.get('status', 'Waspada')
                    region = w.get('region', w.get('province', 'Wilayah'))
                    
                    # Icons
                    icon = "🌧️" if "Hujan" in status else "⚠️"
                    if "Petir" in status: icon = "⛈️"
                    if "Angin" in status: icon = "💨"
                    if "Lebat" in status: icon = "🌧️🌊"
                    
                    # Clean region name
                    region = region.replace('Provinsi ', '')
                    msg += f"{icon} *{region}*: {status}\n"
            
                # Button back
                keyboard = [
                    [InlineKeyboardButton("« Kembali", callback_data="back_warn_menu")],
                    [InlineKeyboardButton("📅 Hari Ini", callback_data="warn_day_0")],
                    [InlineKeyboardButton("📅 Besok", callback_data="warn_day_1")],
                    [InlineKeyboardButton("📅 Lusa", callback_data="warn_day_2")]
                ]
            
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
            print(f"Error fetching extreme weather: {e}")
            import traceback
            traceback.print_exc()
            
    elif data == "back_warn_menu":
        keyboard = [
            [InlineKeyboardButton("📅 Hari Ini", callback_data="warn_day_0")],
            [InlineKeyboardButton("📅 Besok", callback_data="warn_day_1")],
            [InlineKeyboardButton("📅 Lusa", callback_data="warn_day_2")]
        ]
        await query.edit_message_text(
            "⚠️ *Peringatan Dini Cuaca Ekstrem*\n\n"
            "Silakan pilih hari:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


async def extreme_weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /ekstrem"""
    init_components()
    
    keyboard = [
        [InlineKeyboardButton("📅 Hari Ini", callback_data="warn_day_0")],
        [InlineKeyboardButton("📅 Besok", callback_data="warn_day_1")],
        [InlineKeyboardButton("📅 Lusa", callback_data="warn_day_2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *Peringatan Dini Cuaca Ekstrem*\n\n"
        "Silakan pilih hari untuk melihat potensi cuaca ekstrem di Indonesia:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def get_telegram_app():
    """Create and configure Telegram Application for Webhook"""
    init_components()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN tidak ditemukan!")
        return None
        
    # Increase timeouts for Serverless Environment stability
    application = (
        Application.builder()
        .token(token)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .build()
    )
    
    # Tambahkan command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("artikel", artikel))
    application.add_handler(CommandHandler("artikelkota", artikelkota))
    application.add_handler(CommandHandler("cuacakota", cuacakota))
    application.add_handler(CommandHandler("carikota", carikota))
    application.add_handler(CommandHandler("satelit", satelit_command))
    application.add_handler(CommandHandler("kota", kota_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("userstats", userstats))
    application.add_handler(CommandHandler("ekstrem", extreme_weather_command))
    
    # Tambahkan callback query handler untuk button
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    return application


def main():
    """Fungsi utama untuk menjalankan bot"""
    
    # Ambil token dari environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN tidak ditemukan di .env file")
        print("Silakan tambahkan TELEGRAM_BOT_TOKEN ke file .env")
        sys.exit(1)
    
    print("🤖 Starting BMKG Weather Telegram Bot...")
    print("=" * 60)
    
    # Buat aplikasi via helper
    application = get_telegram_app()
    
    # Start scheduler untuk auto-check gambar
    if chat_id:
        print("\n📅 Starting image scheduler...")
        scheduler = BMKGImageScheduler(token, chat_id)
        scheduler.start()
        print(f"   Target chat ID: {chat_id}")
    else:
        print("\n⚠️ TELEGRAM_CHAT_ID tidak diset")
        print("   Auto-send gambar disabled")
        print("   Set TELEGRAM_CHAT_ID di .env untuk enable")
    
    print("\n✅ Bot siap menerima perintah!")
    print("=" * 60)
    print("\nCommand yang tersedia:")
    print("  /start       - Mulai bot")
    # ... rest of print statements inherited from original main ...
    print("  /help        - Bantuan")
    print("  /artikel     - Generate artikel cuaca random")
    print("  /artikelkota - Generate artikel dengan kota pilihan")
    print("  /cuacakota   - Info cuaca kota")
    print("  /carikota    - Cari kota")
    print("  /satelit     - Gambar satelit Himawari rainfall potential")
    print("  /kota        - Lihat kota terpilih")
    print("  /random      - Pilih kota random")
    print("\n🔧 Network Configuration:")
    print("  • Timeout: 30s")
    print("  • Auto-retry enabled")
    print("  • Error handler: Registered")
    print("\n⚠️  Troubleshooting jika error 'getaddrinfo failed':")
    print("  1. Periksa koneksi internet")
    print("  2. Coba ping google.com atau api.telegram.org")
    print("  3. Periksa firewall/antivirus")
    print("  4. Gunakan VPN jika Telegram diblokir")
    print("\nTekan Ctrl+C untuk stop bot")
    print("=" * 60)
    
    # Jalankan bot dengan error handling
    try:
        logger.info("Starting bot polling...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except NetworkError as e:
        logger.error(f"Network error during polling: {e}")
        print("\n❌ Network Error: Tidak dapat terhubung ke server Telegram")
        print("   Periksa koneksi internet Anda")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during polling: {e}")
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot dihentikan oleh user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
