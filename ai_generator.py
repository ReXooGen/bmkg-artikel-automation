"""
Module untuk generate konten tambahan menggunakan Google Gemini AI dengan fallback
dan auto-recovery ketika semua API keys rate limited
"""

import requests
import json
import time
from typing import Dict, Optional, Tuple

# Import auto key generator (optional - won't break if not available)
try:
    from auto_key_generator import AutoKeyGenerator
    AUTO_KEY_GENERATOR_AVAILABLE = True
except ImportError:
    AUTO_KEY_GENERATOR_AVAILABLE = False
    print("⚠️  Auto Key Generator tidak tersedia (opsional)")


class GeminiAIGenerator:
    """Class untuk generate konten artikel menggunakan Google Gemini AI dengan fallback otomatis"""
    
    def __init__(self, api_keys):
        # Support both single key (string) dan multiple keys (list)
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
        else:
            self.api_keys = api_keys
        
        self.current_api_key_index = 0
        self.api_key = self.api_keys[self.current_api_key_index]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.max_retries = 1  # Minimal retry
        self.base_delay = 1
        self.request_timeout = 10
        
        # Model dengan urutan prioritas (based on available quota)
        self.models = [
            "gemini-2.5-flash-lite",
            "gemini-3-flash",
            "gemma-3-1b",
            "gemini-2.5-flash-tts"
        ]
        self.current_model_index = 0
        
        # Flag untuk tracking
        self.ai_available = True
        self.last_error = None
        
        # Auto recovery tracking
        self.auto_recovery_attempted = False
        self.auto_key_generator = None
        
        # Initialize auto key generator if available
        if AUTO_KEY_GENERATOR_AVAILABLE:
            try:
                self.auto_key_generator = AutoKeyGenerator()
                if self.auto_key_generator.is_available():
                    print("✓ Auto Key Generator siap (akan otomatis membuat API keys baru jika semua limit)")
                else:
                    print("⚠️  Auto Key Generator tidak tersedia")
            except Exception as e:
                print(f"⚠️  Gagal inisialisasi Auto Key Generator: {e}")
    
    def generate_title(self, weather_data: Dict[str, Dict]) -> Optional[str]:
        """Generate judul berita yang menarik dan SEO-friendly"""
        if not self.ai_available:
            return None
        
        cities = list(weather_data.keys())
        city_summaries = []
        
        # Ambil tanggal dari kota pertama
        first_city_data = weather_data[cities[0]]
        date_obj = first_city_data.get('datetime')
        
        # Format tanggal ke Bahasa Indonesia
        if date_obj:
            months_id = {
                1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
                5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
                9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
            }
            # Parse string datetime jika masih string
            if isinstance(date_obj, str):
                from dateutil import parser
                date_obj = parser.parse(date_obj)
            
            date_str = f"{date_obj.day} {months_id[date_obj.month]} {date_obj.year}"
        else:
            date_str = "hari ini"
        
        for city in cities:
            data = weather_data[city]
            city_summaries.append(f"{city}: {data['weather']} ({data['temperature']}°C)")
        
        summary = "\n".join(city_summaries)
        
        # Membuat list kota yang valid untuk validasi
        valid_cities = set(cities)
        
        prompt = f"""Buatkan 1 judul berita cuaca nasional yang MENARIK, INFORMATIF, dan SEO-friendly untuk portal berita Indonesia.
Data cuaca untuk tanggal {date_str}:
{summary}
KETENTUAN WAJIB:

Format HARUS: "BMKG: Cuaca Kota [NAMA_KOTA] {date_str} Diprakirakan [KONDISI], [KOTA_LAIN] [KONDISI]"
WAJIB sertakan "Cuaca Kota" dan tanggal "{date_str}" di awal setelah "BMKG:"
Pilih 1 kota UTAMA yang paling menarik untuk judul (kota dengan cuaca EKSTREM atau PENTING)
Sebutkan 1-2 kota lainnya dengan kondisi cuaca yang KONTRAS/berbeda
PRIORITAS pemilihan kota UTAMA:

Kota dengan HUJAN LEBAT/PETIR (prioritas tertinggi)
Kota dengan cuaca EKSTREM (panas terik, kabut tebal, angin kencang)
Kota BESAR/PENTING (ibukota provinsi, kota wisata)
Kota dengan cuaca yang BERBEDA dari lainnya


JANGAN sebutkan semua kota! Pilih yang PALING MENARIK saja
PENTING: HANYA gunakan nama kota yang TERCANTUM di data cuaca, JANGAN tambahkan kota lain
Gunakan kata kerja AKTIF: Waspada, Diprakirakan, Prakirakan, Ingatkan
Bahasa jurnalistik formal, ringkas, tidak clickbait
Panjang maksimal 20 kata
JANGAN gunakan tanda petik (")

CONTOH FORMAT YANG BENAR:

"BMKG: Cuaca Kota Banda Aceh {date_str} Diprakirakan Cerah Berawan, Sejumlah Kota Lainnya Hujan Ringan Hingga Petir"
"BMKG: Cuaca Kota Jakarta {date_str} Diprakirakan Hujan Petir, Denpasar Cerah Berawan"
"BMKG: Cuaca Kota Kupang {date_str} Diprakirakan Hujan Lebat, Banda Aceh Cerah"

OUTPUT:

HANYA 1 judul berita
TANPA bullet, nomor, atau penjelasan tambahan
WAJIB ikuti format di atas"""
        
        title = self._generate_content(prompt)
        
        # Validasi: Pastikan judul hanya mengandung kota yang ada dalam data
        if title:
            # Cek apakah ada kota yang tidak valid dalam judul
            title_lower = title.lower()
            contains_invalid_city = False
            
            # List kota-kota besar yang sering muncul tapi mungkin tidak ada dalam data
            common_cities = ['jakarta', 'surabaya', 'bandung', 'medan', 'semarang', 
                           'makassar', 'palembang', 'tangerang', 'depok', 'bogor',
                           'yogyakarta', 'malang', 'solo', 'batam', 'pekanbaru']
            
            for city in common_cities:
                if city in title_lower and city.capitalize() not in valid_cities:
                    contains_invalid_city = True
                    print(f"  ⚠️  Judul mengandung kota tidak valid: {city.capitalize()}")
                    break
            
            if contains_invalid_city:
                print("  ⚠️  Judul AI tidak valid, gunakan fallback template")
                return None
        
        return title
    
    def generate_intro_paragraph(self, weather_data: Dict[str, Dict]) -> Optional[str]:
        """Generate paragraf pembuka yang menarik"""
        if not self.ai_available:
            return None
        
        weather_summary = []
        for city, data in weather_data.items():
            weather_summary.append(
                f"{city}: {data['weather']} ({data['temperature']}°C)"
            )
        
        prompt = f"""Buatkan 1 paragraf pembuka menarik (2-3 kalimat) untuk artikel berita cuaca berdasarkan data berikut:

{chr(10).join(weather_summary)}

KETENTUAN:
1. HANYA gunakan informasi dari data cuaca di atas
2. HANYA sebutkan kota yang TERCANTUM dalam data
3. JANGAN menambahkan kota atau informasi yang tidak ada dalam data
4. Gunakan Bahasa Indonesia formal dan menarik perhatian pembaca
5. Fokus pada kondisi cuaca yang paling menarik atau kontras

OUTPUT:
Berikan HANYA paragraf pembuka tanpa penjelasan tambahan."""
        
        return self._generate_content(prompt)
    
    def generate_closing_paragraph(self, weather_data: Dict[str, Dict]) -> Optional[str]:
        """Generate paragraf penutup yang informatif"""
        if not self.ai_available:
            return None
        
        rainy_cities = []
        hot_cities = []
        
        for city, data in weather_data.items():
            if 'hujan' in data['weather'].lower():
                rainy_cities.append(city)
            if data['temperature'] >= 30:
                hot_cities.append(city)
        
        context_lines = []
        if rainy_cities:
            context_lines.append(f"Kota dengan hujan: {', '.join(rainy_cities)}")
        if hot_cities:
            context_lines.append(f"Kota dengan suhu tinggi: {', '.join(hot_cities)}")
        
        prompt = f"""Buatkan 1 paragraf penutup (2-3 kalimat) untuk artikel berita cuaca dengan tips/saran masyarakat.

Konteks: {' | '.join(context_lines) if context_lines else 'Kondisi cuaca bervariasi'}

Gunakan Bahasa Indonesia formal dan informatif.
Berikan HANYA paragraf penutup tanpa penjelasan."""
        
        return self._generate_content(prompt)
    
    def _generate_content(self, prompt: str) -> Optional[str]:
        """
        Call Gemini API dengan timeout singkat dan fallback otomatis
        Jika AI tidak tersedia, return None (gunakan fallback template)
        """
        if not self.ai_available:
            return None
        
        # Coba semua API key dengan timeout singkat
        for api_idx, api_key in enumerate(self.api_keys):
            for model_idx, model in enumerate(self.models):
                url = f"{self.base_url}/{model}:generateContent?key={api_key}"
                
                try:
                    # Optimize payload untuk model lite
                    payload = {
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.5,  # Lower untuk lebih konsisten
                            "maxOutputTokens": 500,  # Reduced untuk model lite
                        }
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    
                    # Request dengan timeout singkat (10 detik)
                    response = requests.post(
                        url, 
                        json=payload, 
                        headers=headers, 
                        timeout=self.request_timeout
                    )
                    
                    # Jika berhasil, return hasil
                    if response.status_code == 200:
                        result = response.json()
                        if 'candidates' in result and len(result['candidates']) > 0:
                            candidate = result['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                text = candidate['content']['parts'][0].get('text', '').strip()
                                if text:
                                    print(f"  ✓ Berhasil dengan API key #{api_idx + 1}, model: {model}")
                                    return text
                    
                    # Jika rate limit, coba API key berikutnya
                    elif response.status_code == 429:
                        print(f"  ⚠️  API key #{api_idx + 1} rate limit, mencoba key berikutnya...")
                        break  # Break dari loop model, coba API key berikutnya
                    
                    elif response.status_code in [401, 403]:
                        print(f"  ⚠️  API key #{api_idx + 1} tidak valid, mencoba key berikutnya...")
                        break  # Break dari loop model, coba API key berikutnya
                    
                    elif response.status_code == 404:
                        # Model tidak tersedia, coba model berikutnya
                        continue
                    
                except requests.exceptions.Timeout:
                    print(f"  ⚠️  Timeout dengan API key #{api_idx + 1}, model {model}")
                    continue  # Coba model berikutnya
                
                except requests.exceptions.ConnectionError:
                    print(f"  ⚠️  Connection error dengan API key #{api_idx + 1}")
                    break  # Coba API key berikutnya
                
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"  ⚠️  Parse error: {e}")
                    continue  # Coba model berikutnya
        
        # Semua API key dan model gagal - check untuk auto recovery
        rate_limited_count = 0
        for api_key in self.api_keys:
            # Quick check if key is rate limited
            test_url = f"{self.base_url}/gemini-2.5-flash-lite:generateContent?key={api_key}"
            try:
                test_response = requests.post(test_url, json={"contents": [{"parts": [{"text": "test"}]}]}, timeout=3)
                if test_response.status_code == 429:
                    rate_limited_count += 1
            except:
                pass
        
        # Jika semua key rate limited dan auto recovery belum dicoba
        if rate_limited_count == len(self.api_keys) and not self.auto_recovery_attempted:
            print(f"\n🔄 SEMUA {len(self.api_keys)} API KEY RATE LIMITED!")
            
            if self.auto_key_generator and self.auto_key_generator.is_available():
                print("🔄 Mencoba auto-recovery: Membuat project baru dan generate API keys...")
                self.auto_recovery_attempted = True
                
                try:
                    success, new_keys = self.auto_key_generator.generate_new_keys(num_keys=5)
                    
                    if success and new_keys:
                        print(f"✅ Auto-recovery berhasil! {len(new_keys)} API keys baru telah dibuat")
                        print("📝 File .env telah diupdate dengan API keys baru")
                        
                        # Add new keys to current session
                        self.api_keys.extend(new_keys)
                        print(f"✓ Total API keys sekarang: {len(self.api_keys)}")
                        
                        # Reset availability dan retry
                        self.ai_available = True
                        self.last_error = None
                        
                        # Coba lagi dengan key baru
                        print("🔄 Retry dengan API keys baru...")
                        return self._generate_content(prompt)
                    else:
                        print("❌ Auto-recovery gagal")
                except Exception as e:
                    print(f"❌ Error saat auto-recovery: {e}")
            else:
                print("⚠️  Auto Key Generator tidak tersedia untuk recovery otomatis")
        
        # Jika semua gagal, mark AI unavailable
        self.ai_available = False
        self.last_error = f"Semua {len(self.api_keys)} API key dan {len(self.models)} model tidak tersedia"
        return None
    
    def enhance_article(self, base_article: str, weather_data: Dict[str, Dict]) -> Tuple[str, Optional[str]]:
        """
        Enhance artikel dengan AI, dengan fallback otomatis ke template jika gagal
        Hanya generate judul, tidak mengubah isi artikel
        
        Returns:
            Tuple (artikel asli tanpa modifikasi, judul AI atau None)
        """
        print(f"\n🤖 Mencoba enhance judul dengan AI...")
        
        # Generate title only
        ai_title = None
        try:
            ai_title = self.generate_title(weather_data)
            if ai_title:
                print("✓ Judul AI berhasil di-generate")
            else:
                if not self.ai_available:
                    print(f"⚠️  AI tidak tersedia: {self.last_error}")
                    return base_article, None
        except Exception as e:
            print(f"⚠️  Error generating title: {e}")
            self.ai_available = False
            return base_article, None
        
        # Return artikel asli tanpa modifikasi, hanya judul yang AI-enhanced
        if ai_title:
            print("✓ Judul berhasil ditingkatkan dengan AI")
        else:
            print("⚠️  AI enhancement gagal, menggunakan judul dasar")
        
        return base_article, ai_title
    
    def is_available(self) -> bool:
        """Check apakah AI masih tersedia"""
        return self.ai_available
    
    def get_status(self) -> str:
        """Get status pesan AI"""
        if self.ai_available:
            return "AI siap digunakan"
        else:
            return f"AI tidak tersedia: {self.last_error}"
    
    def trigger_manual_recovery(self, num_keys: int = 5) -> bool:
        """
        Manually trigger auto-recovery untuk generate new API keys
        
        Args:
            num_keys: Jumlah API keys baru yang akan di-generate
        
        Returns:
            bool: True jika berhasil
        """
        if not self.auto_key_generator or not self.auto_key_generator.is_available():
            print("❌ Auto Key Generator tidak tersedia")
            return False
        
        print(f"🔄 Manual recovery: Generating {num_keys} new API keys...")
        
        success, new_keys = self.auto_key_generator.generate_new_keys(num_keys=num_keys)
        
        if success and new_keys:
            self.api_keys.extend(new_keys)
            self.ai_available = True
            self.last_error = None
            self.auto_recovery_attempted = False
            print(f"✅ Manual recovery berhasil! Total keys: {len(self.api_keys)}")
            return True
        else:
            print("❌ Manual recovery gagal")
            return False