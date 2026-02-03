"""
Konfigurasi untuk WhatsApp Bot (PyWa)
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# WhatsApp Cloud API Configuration
WA_PHONE_ID = os.getenv('WA_PHONE_ID')
WA_TOKEN = os.getenv('WA_TOKEN')
WA_VERIFY_TOKEN = os.getenv('WA_VERIFY_TOKEN')
WA_APP_SECRET = os.getenv('WA_APP_SECRET')

# Server Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:5000')
PORT = int(os.getenv('PORT', 5000))

# Bot Settings
BOT_NAME = "BMKG Weather Bot"
BOT_VERSION = "1.0.0"

# Command prefix
COMMAND_PREFIX = "/"

# Available commands
COMMANDS = {
    "cuaca": "Cek cuaca kota tertentu. Contoh: /cuaca Jakarta",
    "cuaca3": "Prakiraan 3 kota (WIB, WITA, WIT)",
    "artikel": "Dapatkan artikel cuaca lengkap dengan AI",
    "list": "Lihat daftar kota yang tersedia",
    "help": "Tampilkan bantuan"
}

# Response templates
TEMPLATES = {
    "welcome": """🌤️ *Selamat datang di {bot_name}!*

Saya dapat memberikan informasi prakiraan cuaca dari BMKG untuk berbagai kota di Indonesia.

Ketik /help untuk melihat perintah yang tersedia.""",
    
    "help": """📋 *Perintah yang Tersedia:*

{commands}

💡 *Tips:*
• Data real-time dari BMKG
• 98+ kota tersedia
• Prakiraan akurat

_Powered by BMKG API_""",
    
    "not_found": """❌ Maaf, kota *{city}* tidak ditemukan dalam database.

Ketik /list untuk melihat daftar kota yang tersedia.""",
    
    "error": """⚠️ Terjadi kesalahan saat memproses permintaan Anda.

Silakan coba lagi dalam beberapa saat atau hubungi admin jika masalah berlanjut."""
}

# Validate configuration
def validate_config():
    """Validate bot configuration"""
    missing = []
    
    if not WA_PHONE_ID:
        missing.append("WA_PHONE_ID")
    if not WA_TOKEN:
        missing.append("WA_TOKEN")
    if not WA_VERIFY_TOKEN:
        missing.append("WA_VERIFY_TOKEN")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return True
