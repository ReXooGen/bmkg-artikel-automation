"""
Module untuk generate konten tambahan menggunakan Google Gemini AI dengan fallback
"""

import requests
import json
import time
from typing import Dict, Optional, Tuple


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
    
    def generate_title(self, weather_data: Dict[str, Dict]) -> Optional[str]:
        """Generate judul berita yang menarik dan SEO-friendly"""
        if not self.ai_available:
            return None
        
        cities = list(weather_data.keys())
        city_summaries = []
        for city in cities:
            data = weather_data[city]
            city_summaries.append(f"{city}: {data['weather']} ({data['temperature']}°C)")
        
        summary = "\n".join(city_summaries)
        
        prompt = f"""Buatkan 1 judul berita cuaca yang menarik dan SEO-friendly untuk media nasional Indonesia.

Data cuaca:
{summary}

ATURAN:
1. WAJIB cantumkan "BMKG" atau "Prakiraan BMKG"
2. Fokus pada kondisi ekstrem (hujan, badai, panas terik)
3. Sebutkan 2-3 kota dengan kondisi berbeda
4. Gunakan kata kerja aktif: Waspada, Ingatkan, Prakirakan
5. Jangan monoton

Berikan HANYA 1 judul tanpa penjelasan."""
        
        return self._generate_content(prompt)
    
    def generate_intro_paragraph(self, weather_data: Dict[str, Dict]) -> Optional[str]:
        """Generate paragraf pembuka yang menarik"""
        if not self.ai_available:
            return None
        
        weather_summary = []
        for city, data in weather_data.items():
            weather_summary.append(
                f"{city}: {data['weather']} ({data['temperature']}°C)"
            )
        
        prompt = f"""Buatkan 1 paragraf pembuka menarik (2-3 kalimat) untuk artikel berita cuaca:

{chr(10).join(weather_summary)}

Gunakan Bahasa Indonesia formal dan menarik perhatian pembaca.
Berikan HANYA paragraf pembuka tanpa penjelasan."""
        
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