"""
Command handlers untuk WhatsApp Bot
"""

from typing import Optional
from bmkg_api import fetch_city_weather, fetch_all_cities_weather
from wilayah_db import WilayahDatabase
from config_db import CITY_CODES, search_city, get_cities_by_timezone
from template_generator import WeatherArticleGenerator
from ai_generator import GeminiAIGenerator
from config_db import GOOGLE_GEMINI_API_KEYS, USE_AI_ENHANCEMENT
from bot_config import COMMANDS, TEMPLATES, BOT_NAME


class BotHandlers:
    """Class untuk handle commands WhatsApp bot"""
    
    def __init__(self):
        self.db = WilayahDatabase()
        self.db.connect()
        self.generator = WeatherArticleGenerator()
        
    def handle_start(self, user_name: str = "Pengguna") -> str:
        """Handle /start atau greeting message"""
        return TEMPLATES["welcome"].format(bot_name=BOT_NAME)
    
    def handle_help(self) -> str:
        """Handle /help command"""
        commands_text = ""
        for cmd, desc in COMMANDS.items():
            commands_text += f"/{cmd}\n  _{desc}_\n\n"
        
        return TEMPLATES["help"].format(commands=commands_text.strip())
    
    def handle_cuaca(self, city_name: str) -> str:
        """
        Handle /cuaca [nama_kota] command
        
        Args:
            city_name: Nama kota yang dicari
        
        Returns:
            Formatted weather information
        """
        if not city_name:
            return "❌ Mohon sebutkan nama kota.\n\nContoh: /cuaca Jakarta"
        
        # Search city in database
        city_info = search_city(city_name)
        
        if not city_info:
            return TEMPLATES["not_found"].format(city=city_name)
        
        # Fetch weather data
        try:
            weather_data = fetch_city_weather(
                city_info['code'],
                city_info['name'],
                city_info['timezone']
            )
            
            if not weather_data:
                return f"⚠️ Gagal mengambil data cuaca untuk {city_name}. Silakan coba lagi."
            
            # Format response
            response = f"""🌤️ *Prakiraan Cuaca {city_info['name']}*

📅 {weather_data['datetime']}
🕐 {weather_data['time']} {city_info['timezone']}

🌡️ *Suhu:* {weather_data['temperature']}°C
💧 *Kelembapan:* {weather_data['humidity']}%
🌤️ *Kondisi:* {weather_data['weather']}
💨 *Angin:* {weather_data['wind_speed']} km/jam dari {weather_data['wind_direction']}

_Data dari BMKG_"""
            
            return response
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return TEMPLATES["error"]
    
    def handle_cuaca3(self) -> str:
        """Handle /cuaca3 command - 3 cities (WIB, WITA, WIT)"""
        try:
            # Get one city from each timezone
            cities = {}
            
            for tz in ['WIB', 'WITA', 'WIT']:
                tz_cities = get_cities_by_timezone(tz)
                if tz_cities:
                    # Get first city from this timezone
                    city = tz_cities[0]
                    cities[city['name']] = {
                        'code': city['code'],
                        'timezone': city['timezone'],
                        'timezone_offset': city['timezone_offset']
                    }
            
            if not cities:
                return "⚠️ Gagal mendapatkan data kota. Silakan coba lagi."
            
            # Fetch weather for all cities
            weather_data = fetch_all_cities_weather(cities)
            
            if not weather_data:
                return "⚠️ Gagal mengambil data cuaca. Silakan coba lagi."
            
            # Format response
            response = "🌤️ *Prakiraan 3 Kota Indonesia*\n\n"
            
            for city_name, data in weather_data.items():
                response += f"📍 *{city_name}* ({data['timezone']})\n"
                response += f"   🌡️ {data['temperature']}°C | {data['weather']}\n"
                response += f"   💧 {data['humidity']}% | 💨 {data['wind_speed']} km/jam\n\n"
            
            response += f"📅 {list(weather_data.values())[0]['date']}\n"
            response += "_Data dari BMKG_"
            
            return response
            
        except Exception as e:
            print(f"Error in cuaca3: {e}")
            return TEMPLATES["error"]
    
    def handle_artikel(self) -> str:
        """Handle /artikel command - Full article with AI"""
        try:
            # Use existing CITY_CODES (3 cities)
            if not CITY_CODES:
                return "⚠️ Tidak ada kota yang dipilih. Silakan coba lagi."
            
            # Fetch weather data
            weather_data = fetch_all_cities_weather(CITY_CODES)
            
            if not weather_data:
                return "⚠️ Gagal mengambil data cuaca. Silakan coba lagi."
            
            # Generate article
            article = self.generator.generate_article(weather_data)
            title = self.generator.generate_title(weather_data)
            
            # AI Enhancement (optional)
            if USE_AI_ENHANCEMENT and GOOGLE_GEMINI_API_KEYS:
                try:
                    ai_gen = GeminiAIGenerator(GOOGLE_GEMINI_API_KEYS)
                    article, ai_title = ai_gen.enhance_article(article, weather_data)
                    if ai_title:
                        title = ai_title
                except:
                    pass  # Use base article if AI fails
            
            # Format for WhatsApp (shorten if too long)
            max_length = 3500
            if len(article) > max_length:
                article = article[:max_length] + "..."
            
            response = f"""📰 *{title}*

{article}

━━━━━━━━━━━━━━━
📅 {list(weather_data.values())[0]['date']}
📊 Sumber: BMKG
_Artikel otomatis dengan AI_"""
            
            return response
            
        except Exception as e:
            print(f"Error generating article: {e}")
            return TEMPLATES["error"]
    
    def handle_list(self) -> str:
        """Handle /list command - Show available cities"""
        try:
            response = "📋 *Daftar Kota Tersedia*\n\n"
            
            for tz in ['WIB', 'WITA', 'WIT']:
                cities = get_cities_by_timezone(tz)
                if cities:
                    response += f"*{tz}:*\n"
                    # Show first 10 cities per timezone
                    for city in cities[:10]:
                        response += f"• {city['name']}\n"
                    
                    if len(cities) > 10:
                        response += f"_...dan {len(cities) - 10} kota lainnya_\n"
                    response += "\n"
            
            response += f"💡 *Total:* 98+ kota tersedia\n"
            response += "\n_Ketik /cuaca [nama kota] untuk cek cuaca_"
            
            return response
            
        except Exception as e:
            print(f"Error in list: {e}")
            return TEMPLATES["error"]
    
    def handle_unknown(self, message: str) -> str:
        """Handle unknown command or message"""
        return """❓ Maaf, saya tidak mengerti perintah tersebut.

Ketik /help untuk melihat perintah yang tersedia."""
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
