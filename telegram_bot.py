"""
Telegram Bot untuk BMKG Weather Automation
"""

import os
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown
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
/artikelkota - Generate artikel dengan kota pilihan (1-4 kota)
/cuacakota - Info cuaca singkat real-time
/kota - Lihat 4 kota yang sedang dipilih
/random - Pilih 4 kota random baru
/help - Tampilkan bantuan
/carikota - Cari kota di database 90,826+ kota

💡 Contoh penggunaan:
`/artikel` - 4 kota random
`/artikelkota Bandung` - Bandung + 3 kota random
`/artikelkota Jakarta Bandung` - Jakarta, Bandung + 2 kota random
`/artikelkota Jakarta Bandung Surabaya Denpasar` - 4 kota spesifik
`/cuacakota Jakarta`
`/carikota Surabaya`

Data cuaca dari BMKG Indonesia 🇮🇩
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    help_text = """
📖 *Panduan Penggunaan*

*1. Generate Artikel Cuaca*
/artikel - Generate artikel dengan 4 kota random
/artikelkota [kota1] [kota2] ... - Generate artikel dengan kota tertentu (1-4 kota)

Contoh:
• `/artikel` - 4 kota random
• `/artikelkota Jakarta` - Jakarta + 3 kota random
• `/artikelkota Jakarta Bandung` - Jakarta, Bandung + 2 kota random
• `/artikelkota Jakarta Bandung Surabaya Denpasar` - 4 kota spesifik

*2. Info Cuaca Singkat*
/cuacakota [nama kota] - Informasi cuaca real-time

Contoh:
• `/cuacakota Jakarta`
• `/cuacakota Surabaya`

*3. Cari Kota*
/carikota [nama kota] - Cari kota di database

Contoh:
• `/carikota Malang`
• `/carikota Denpasar`

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
    """Handler untuk command /artikel - random 4 kota"""
    init_components()
    
    await update.message.reply_text("⏳ Mengambil data cuaca dari BMKG...")
    
    try:
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
    
    if not context.args:
        # Tampilkan menu pilihan provinsi dengan inline keyboard
        keyboard = []
        provinces = city_selector.db.get_all_provinces()
        
        # Buat button 2 kolom per row
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
        
        # Tambahkan button random
        keyboard.append([InlineKeyboardButton("🎲 Pilih Random", callback_data="artikel_random")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📍 *Pilih Provinsi:*\n\n"
            "Pilih provinsi untuk melihat daftar kota,\n"
            "atau ketik: `/artikelkota [nama kota]`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text("⏳ Mengambil data cuaca dari BMKG...")
    
    try:
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
                "Contoh: `/artikelkota Jakarta Bandung Surabaya Denpasar`",
                parse_mode='Markdown'
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
    
    if not context.args:
        await update.message.reply_text(
            "❌ Gunakan format: /cuacakota [nama kota]\n\n"
            "Contoh: /cuacakota Jakarta"
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
                f"Gunakan /carikota {city_name} untuk mencari kota yang mirip."
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


async def carikota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /carikota"""
    init_components()
    
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


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk button callback"""
    init_components()
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
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
        
        # Simpan kota ke context user_data
        if 'selected_cities' not in context.user_data:
            context.user_data['selected_cities'] = []
        
        if city_name not in context.user_data['selected_cities']:
            context.user_data['selected_cities'].append(city_name)
        
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
            f"✅ *Kota dipilih: {city_name}*\n\n"
            f"📋 *Daftar kota ({len(selected)}/4):*\n{city_list}\n\n"
            f"{'ℹ️ Pilih maksimal 4 kota' if len(selected) < 4 else '✅ Sudah 4 kota'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle back to provinsi
    elif data == "back_prov":
        keyboard = []
        provinces = city_selector.db.get_all_provinces()
        
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
        
        keyboard.append([InlineKeyboardButton("🎲 Pilih Random", callback_data="artikel_random")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selected_info = ""
        if 'selected_cities' in context.user_data and context.user_data['selected_cities']:
            selected = context.user_data['selected_cities']
            selected_info = f"\n\n📋 Kota terpilih: {len(selected)}"
        
        await query.edit_message_text(
            f"📍 *Pilih Provinsi:*{selected_info}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Handle clear cities
    elif data == "clear_cities":
        context.user_data['selected_cities'] = []
        
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
        
        if not selected_cities:
            await query.edit_message_text("❌ Belum ada kota yang dipilih!")
            return
        
        await query.edit_message_text("⏳ Mengambil data cuaca dari BMKG...")
        
        try:
            # Reset city selector
            city_selector.clear_selected_cities()
            
            # Tambahkan kota yang dipilih
            not_found = []
            for city_name in selected_cities:
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
            
            # Ambil data cuaca
            weather_data = fetch_all_cities_weather(selected)
            
            if not weather_data or len(weather_data) < 4:
                await query.message.reply_text("❌ Gagal mengambil data cuaca dari BMKG.")
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
            
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
            print(f"Error in generate artikel: {e}")
    
    # Handle artikel random
    elif data == "artikel_random":
        await query.edit_message_text("⏳ Mengambil data cuaca dari BMKG...")
        
        try:
            initialize_cities(force_new=True)
            selected_cities = CITY_CODES
            
            weather_data = fetch_all_cities_weather(selected_cities)
            
            if not weather_data or len(weather_data) < 4:
                await query.message.reply_text("❌ Gagal mengambil data cuaca.")
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
    application.add_handler(CommandHandler("artikelkota", artikelkota))
    application.add_handler(CommandHandler("cuacakota", cuacakota))
    application.add_handler(CommandHandler("carikota", carikota))
    application.add_handler(CommandHandler("kota", kota_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("stats", stats))
    
    # Tambahkan callback query handler untuk button
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot siap menerima perintah!")
    print("=" * 60)
    print("\nCommand yang tersedia:")
    print("  /start       - Mulai bot")
    print("  /help        - Bantuan")
    print("  /artikel     - Generate artikel cuaca random")
    print("  /artikelkota - Generate artikel dengan kota pilihan")
    print("  /cuacakota   - Info cuaca kota")
    print("  /carikota    - Cari kota")
    print("  /kota        - Lihat kota terpilih")
    print("  /random      - Pilih kota random")
    print("  /stats       - Statistik database")
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
