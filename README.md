# BMKG Weather Automation

Sistem automasi untuk generate artikel cuaca dari data BMKG dengan dukungan AI enhancement menggunakan Google Gemini.

## Features

- 📊 Mengambil data cuaca real-time dari API BMKG
- 🤖 AI enhancement untuk artikel lebih menarik (Google Gemini)
- 🗄️ Database 90,826+ wilayah Indonesia
- 🌏 Support 3 timezone (WIB, WITA, WIT)
- 📝 Generate artikel otomatis dengan template dinamis

## Instalasi

1. Clone repository:
```bash
git clone <repository-url>
cd bmkg_automation_data
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup environment variables:
```bash
cp .env.example .env
```

4. Edit file `.env` dan isi dengan credentials Anda:
```env
# Google Gemini API Keys (comma separated)
GOOGLE_GEMINI_API_KEYS=your_api_key_1,your_api_key_2

# WhatsApp Target Number (optional)
WHATSAPP_TARGET_NUMBER=+62XXXXXXXXXXXX

# AI Enhancement (True/False)
USE_AI_ENHANCEMENT=True
```

## Cara Menggunakan

### Generate Artikel Cuaca

```bash
python main.py
```

Program akan:
1. Memilih 4 kota random (2 WIB, 1 WITA, 1 WIT)
2. Mengambil data cuaca dari API BMKG
3. Generate artikel dari template
4. Enhance dengan AI (opsional)
5. Simpan hasil ke `artikel_cuaca.txt`

### Database Management

```bash
# Import database wilayah
python wilayah_db.py

# Test integrasi database
python test_database_integration.py
```

## Konfigurasi

Edit `config_db.py` untuk mengatur:
- Jumlah kota per timezone
- Pengaturan AI enhancement

```python
TOTAL_CITIES = 4   # Total kota
WIB_CITIES = 2     # Kota WIB
WITA_CITIES = 1    # Kota WITA
WIT_CITIES = 1     # Kota WIT
```

## Struktur File

```
├── main.py                    # Program utama
├── config_db.py              # Konfigurasi (baca dari .env)
├── bmkg_api.py               # API client BMKG
├── template_generator.py     # Generator artikel
├── ai_generator.py           # AI enhancement
├── city_selector_db.py       # Selector kota dari database
├── wilayah_db.py            # Database manager
├── requirements.txt          # Python dependencies
├── .env.example             # Template environment variables
└── README.md                # Dokumentasi
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_GEMINI_API_KEYS` | Google Gemini API keys (comma separated) | Optional* |
| `WHATSAPP_TARGET_NUMBER` | Nomor WhatsApp tujuan | Optional |
| `USE_AI_ENHANCEMENT` | Enable/disable AI enhancement | Optional |

*Required jika `USE_AI_ENHANCEMENT=True`

## API Keys

### Google Gemini API

1. Kunjungi [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Tambahkan ke `.env`

### WhatsApp (Opsional)

Untuk fitur WhatsApp bot, lihat `PYWA_SETUP_GUIDE.md`

## Sumber Data

Data cuaca diambil dari:
- **BMKG API**: https://api.bmkg.go.id/publik/prakiraan-cuaca
- **Database Wilayah**: 90,826+ wilayah Indonesia (BPS 2020)

## Contoh Output

```
BMKG: Cuaca Kota Bandung 30 Desember 2025 Diprakirakan Hujan Ringan, Denpasar Cerah Berawan

================================================================================

Badan Meteorologi, Klimatologi dan Geofisika (BMKG) memprakirakan cuaca 
di Kota Bandung hujan ringan pada hari Selasa, 30 Desember 2025...
```

## Troubleshooting

### Error: Tidak dapat mengambil data
- Pastikan koneksi internet aktif
- Cek apakah API BMKG sedang maintenance
- Verifikasi kode wilayah yang digunakan valid

### Error: Data kota tidak lengkap
- Beberapa kode wilayah mungkin tidak tersedia di API
- Coba gunakan kode wilayah alternatif

### Warning: AI enhancement tidak tersedia
- Pastikan `GOOGLE_GEMINI_API_KEYS` sudah diset di `.env`
- Program akan tetap berjalan dengan template dasar

## Lisensi

MIT License

## Disclaimer

⚠️ **Wajib mencantumkan BMKG sebagai sumber data!**

Data cuaca disediakan oleh BMKG (Badan Meteorologi, Klimatologi dan Geofisika).

## Credits

- Data cuaca: **BMKG** (Badan Meteorologi, Klimatologi, dan Geofisika)
- AI: Google Gemini
- Database Wilayah: BPS 2020

---

**Catatan**: Program ini dibuat untuk keperluan automasi artikel cuaca. Selalu verifikasi data cuaca dengan sumber resmi BMKG untuk informasi yang paling akurat.
