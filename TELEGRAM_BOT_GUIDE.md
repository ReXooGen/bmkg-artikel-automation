# Panduan Setup Telegram Bot

## Cara Mendapatkan Bot Token

1. **Buka Telegram dan cari @BotFather**
   - Search `@BotFather` di Telegram
   - Ini adalah bot resmi dari Telegram untuk membuat bot

2. **Buat Bot Baru**
   ```
   /newbot
   ```
   
3. **Beri Nama Bot**
   - Nama display: `BMKG Weather Bot`
   - Username bot: `bmkg_weather_bot` (harus diakhiri dengan 'bot')

4. **Simpan Token**
   - BotFather akan memberikan token seperti:
     ```
     1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890
     ```
   - Copy token ini ke file `.env`:
     ```env
     TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890
     ```

## Setup dan Jalankan Bot

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Konfigurasi .env**
   ```env
   # Telegram Bot Token
   TELEGRAM_BOT_TOKEN=your_token_here
   
   # Google Gemini API Keys (opsional)
   GOOGLE_GEMINI_API_KEYS=your_api_key_1,your_api_key_2
   
   # AI Enhancement
   USE_AI_ENHANCEMENT=True
   ```

3. **Jalankan Bot**
   ```bash
   python telegram_bot.py
   ```

4. **Test Bot**
   - Buka Telegram
   - Cari username bot Anda (contoh: `@bmkg_weather_bot`)
   - Ketik `/start`

## Command Bot

### Basic Commands
- `/start` - Mulai bot dan lihat welcome message
- `/help` - Panduan lengkap penggunaan

### Generate Artikel
- `/artikel` - Generate artikel cuaca dengan 4 kota random
- `/artikel [kota1] [kota2] ...` - Generate artikel dengan kota pilihan (1-4 kota)

**Contoh:**
```
/artikel                                    → 4 kota random
/artikel Jakarta                            → Jakarta + 3 kota random
/artikel Jakarta Bandung                    → Jakarta, Bandung + 2 kota random
/artikel Jakarta Bandung Surabaya Denpasar  → 4 kota spesifik
```

### Info Cuaca
- `/cuaca Jakarta` - Info cuaca singkat Jakarta
- `/cuaca Surabaya` - Info cuaca singkat Surabaya

### Manajemen Kota
- `/cari Bandung` - Cari kota Bandung di database
- `/cari Malang` - Cari kota yang mengandung kata "Malang"
- `/kota` - Lihat 4 kota yang sedang dipilih
- `/random` - Pilih 4 kota random baru

### Statistik
- `/stats` - Lihat statistik database dan status AI

## Fitur Bot

✅ Generate artikel cuaca otomatis dengan AI enhancement
✅ Support 90,826+ kota di Indonesia
✅ Multi-timezone (WIB, WITA, WIT)
✅ Pencarian kota dengan keyword
✅ Info cuaca real-time dari BMKG
✅ Pemilihan kota random yang seimbang
✅ Statistik database lengkap

## Tips

### Custom Bot Settings (via @BotFather)
- `/setdescription` - Set deskripsi bot
- `/setabouttext` - Set about text
- `/setuserpic` - Set profile picture
- `/setcommands` - Set command list

**Command List untuk /setcommands:**
```
start - Mulai bot
help - Panduan penggunaan
artikel - Generate artikel cuaca
cuaca - Info cuaca kota
cari - Cari kota di database
kota - Lihat kota terpilih
random - Pilih kota random
stats - Statistik database
```

### Deploy ke Server

**Menggunakan Screen (Linux):**
```bash
screen -S telegram_bot
python telegram_bot.py
# Ctrl+A+D untuk detach
```

**Menggunakan PM2:**
```bash
pm2 start telegram_bot.py --name bmkg-bot --interpreter python3
pm2 save
pm2 startup
```

**Menggunakan Systemd Service:**
```ini
[Unit]
Description=BMKG Weather Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bmkg_automation_data
ExecStart=/usr/bin/python3 telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Bot tidak respond
- Cek apakah bot sudah running
- Pastikan token benar di `.env`
- Cek koneksi internet

### Error: Database not found
- Jalankan `python wilayah_db.py` untuk import database
- Pastikan file `wilayah_2020.sql` ada

### AI enhancement tidak berfungsi
- Pastikan `GOOGLE_GEMINI_API_KEYS` sudah diset di `.env`
- Set `USE_AI_ENHANCEMENT=True`
- Bot akan tetap berjalan dengan template dasar jika AI tidak tersedia

### Rate limit Telegram
- Telegram limit: 30 pesan per detik
- Bot sudah handle ini secara otomatis

## Security

⚠️ **Jangan share token bot Anda!**
- Token bot sama pentingnya dengan password
- Jika token bocor, revoke via @BotFather dengan `/revoke`
- File `.env` sudah otomatis di-ignore oleh git

## Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [BotFather Commands](https://core.telegram.org/bots#botfather)
