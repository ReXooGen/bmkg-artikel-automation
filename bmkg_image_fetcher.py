"""
Modul untuk mengambil gambar prediksi curah hujan dari BMKG
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


class BMKGImageFetcher:
    """Class untuk download gambar prediksi dari BMKG"""
    
    def __init__(self, save_dir: str = "bmkg_images"):
        """
        Initialize image fetcher
        
        Args:
            save_dir: Directory untuk menyimpan gambar
        """
        # Use /tmp in Vercel environment
        if os.environ.get('VERCEL') == '1':
            self.save_dir = os.path.join('/tmp', os.path.basename(save_dir))
        else:
            self.save_dir = save_dir
            
        self.base_url = "https://inderaja.bmkg.go.id"
        self.extreme_weather_url = "https://www.bmkg.go.id/cuaca/potensi-cuaca-ekstrem"
        self.xml_api_url = "https://data.bmkg.go.id/DataMKG/MEWS/DigitalForecast/DigitalForecast-Indonesia.xml"
        
        # URL gambar yang tersedia
        self.image_urls = {
            'satelit': f"{self.base_url}/IMAGE/HIMA/H08_RP_Indonesia.png",
        }
        
        # Create directory if not exists
        try:
            Path(self.save_dir).mkdir(parents=True, exist_ok=True)
        except OSError:
            # If we can't create directory, use /tmp as fallback
            self.save_dir = '/tmp'
        
        # File untuk menyimpan hash gambar terakhir
        self.hash_file = os.path.join(self.save_dir, "image_hashes.txt")
    
    def _get_image_hash(self, image_data: bytes) -> str:
        """
        Hitung hash MD5 dari gambar
        
        Args:
            image_data: Binary data gambar
            
        Returns:
            String hash MD5
        """
        return hashlib.md5(image_data).hexdigest()
    
    def _load_saved_hash(self, image_type: str) -> Optional[str]:
        """
        Load hash gambar terakhir yang tersimpan
        
        Args:
            image_type: Tipe gambar
            
        Returns:
            Hash string atau None
        """
        if not os.path.exists(self.hash_file):
            return None
        
        try:
            with open(self.hash_file, 'r') as f:
                for line in f:
                    if line.startswith(f"{image_type}:"):
                        return line.split(':', 1)[1].strip()
        except Exception as e:
            print(f"Error loading hash: {e}")
        
        return None
    
    def _save_hash(self, image_type: str, hash_value: str):
        """
        Simpan hash gambar
        
        Args:
            image_type: Tipe gambar
            hash_value: Hash MD5
        """
        try:
            # Baca hash yang ada
            hashes = {}
            if os.path.exists(self.hash_file):
                with open(self.hash_file, 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, val = line.strip().split(':', 1)
                            hashes[key] = val
            
            # Update hash
            hashes[image_type] = hash_value
            
            # Tulis kembali
            with open(self.hash_file, 'w') as f:
                for key, val in hashes.items():
                    f.write(f"{key}:{val}\n")
        except Exception as e:
            print(f"Error saving hash: {e}")
    
    def download_image(self, image_type: str = 'satelit', force: bool = False) -> Tuple[Optional[str], bool]:
        """
        Download gambar prediksi dari BMKG
        
        Args:
            image_type: Tipe gambar ('satelit')
            force: Paksa download meskipun tidak ada perubahan
            
        Returns:
            Tuple (file_path, is_updated)
            - file_path: Path ke file gambar yang di-download, None jika gagal
            - is_updated: True jika gambar ada pembaruan
        """
        if image_type not in self.image_urls:
            print(f"Error: Tipe gambar '{image_type}' tidak valid")
            return None, False
        
        url = self.image_urls[image_type]
        
        try:
            print(f"📥 Downloading gambar {image_type} dari BMKG...")
            
            # Download gambar
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.bmkg.go.id/'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Hitung hash gambar baru
            new_hash = self._get_image_hash(response.content)
            
            # Cek apakah ada perubahan
            old_hash = self._load_saved_hash(image_type)
            is_updated = (old_hash is None or old_hash != new_hash or force)
            
            if not is_updated and not force:
                print(f"ℹ️ Gambar {image_type} tidak ada perubahan")
                # Return file path yang lama jika ada
                old_file = os.path.join(self.save_dir, f"{image_type}_latest.png")
                if os.path.exists(old_file):
                    return old_file, False
                # Jika file tidak ada, tetap save
                is_updated = True
            
            # Simpan gambar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save dengan nama timestamp
            filename_timestamped = f"{image_type}_{timestamp}.png"
            filepath_timestamped = os.path.join(self.save_dir, filename_timestamped)
            
            # Save dengan nama latest (overwrite)
            filename_latest = f"{image_type}_latest.png"
            filepath_latest = os.path.join(self.save_dir, filename_latest)
            
            # Simpan kedua versi
            with open(filepath_timestamped, 'wb') as f:
                f.write(response.content)
            
            with open(filepath_latest, 'wb') as f:
                f.write(response.content)
            
            # Simpan hash
            self._save_hash(image_type, new_hash)
            
            if is_updated:
                print(f"✅ Gambar {image_type} berhasil di-download (ada pembaruan)")
            else:
                print(f"✅ Gambar {image_type} berhasil di-download")
            
            print(f"📁 Saved to: {filepath_latest}")
            
            return filepath_latest, is_updated
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading gambar: {e}")
            return None, False
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, False
    
    def get_image_info(self, image_type: str = 'satelit') -> dict:
        """
        Dapatkan info gambar yang tersimpan
        
        Args:
            image_type: Tipe gambar
            
        Returns:
            Dict dengan info gambar
        """
        filepath = os.path.join(self.save_dir, f"{image_type}_latest.png")
        
        info = {
            'exists': os.path.exists(filepath),
            'path': filepath if os.path.exists(filepath) else None,
            'size': None,
            'modified': None,
            'hash': self._load_saved_hash(image_type)
        }
        
        if info['exists']:
            stat = os.stat(filepath)
            info['size'] = stat.st_size
            info['modified'] = datetime.fromtimestamp(stat.st_mtime)
        
        return info

    def fetch_extreme_weather_data(self, day_offset: int = 0) -> List[Dict[str, str]]:
        """
        Mengambil data cuaca ekstrem dari BMKG.
        Mencoba scraping halaman web terlebih dahulu, fallback ke XML API.
        
        Args:
            day_offset: 0=Hari Ini, 1=Besok, 2=Lusa
            
        Returns:
            List of Warning Dict: [{'region': '...', 'status': '...'}, ...]
        """
        results = []
        
        # Setup headers untuk scraping
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bmkg.go.id/',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        try:
            # 1. Coba Scraping Halaman Visual
            print(f"Mencoba scraping data cuaca ekstrem (Offset: {day_offset})...")
            response = requests.get(self.extreme_weather_url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table', class_='table')
                
                if table:
                    # Index kolom: No | Provinsi | Hari Ini | Besok | Lusa
                    # Hari Ini = col index 2
                    col_idx = 2 + day_offset
                    
                    rows = table.find_all('tr')[1:] # Skip header
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 5:
                            province = cols[1].get_text(strip=True)
                            status = cols[col_idx].get_text(strip=True)
                            
                            # Filter status
                            # Biasanya "-" atau kosong jika aman
                            if status and status != "-" and len(status) > 2:
                                results.append({
                                    'region': province,
                                    'status': status
                                })
                    
                    if results:
                        return results

        except Exception as e:
            print(f"Scraping visual gagal: {e}")
            
        # 2. Fallback: Gunakan API XML Digital Forecast
        # Jika scraping gagal (misal 403 Forbidden), gunakan data open XML
        print("Scraping gagal/kosong, menggunakan fallback XML API...")
        try:
             # Target Date (YYYYMMDD)
            target_date = (datetime.utcnow() + timedelta(hours=7) + timedelta(days=day_offset))
            target_date_str = target_date.strftime("%Y%m%d")
            
            # Use headers to avoid 403 Forbidden on XML API
            # Also check for valid XML content
            response = requests.get(self.xml_api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Check if content looks like HTML (access blocked)
                content_prefix = response.content[:100].decode('utf-8', errors='ignore').lower()
                if "<!doctype html" in content_prefix or "<html" in content_prefix:
                     print("❌ XML API Blocked (HTML received). Using alternate API...")
                     return self.fetch_extreme_weather_alternate(day_offset)

                root = ET.fromstring(response.content)

                
                # Kode Cuaca Ekstrem: 63 (Hujan Lebat), 95 (Hujan Petir), 97 (Hujan Petir)
                extreme_codes = ['63', '95', '97']
                
                temp_results = {} # Gunakan dict untuk dedup per provinsi
                
                for area in root.findall(".//area"):
                    # Kita cari level provinsi jika memungkinkan, atau kota
                    # XML biasanya per-kota. Kita ambil domain-nya (Provinsi)
                    province = area.get("domain")
                    
                    weather_param = area.find("parameter[@id='weather']")
                    if weather_param:
                        for timerange in weather_param.findall("timerange"):
                            dt_str = timerange.get("datetime") # YYYYMMDDHHmm
                            
                            # Cek apakah tanggalnya cocok
                            if dt_str.startswith(target_date_str):
                                val = timerange.find("value").text
                                if val in extreme_codes:
                                    status = "Hujan Lebat" if val == '63' else "Hujan Petir"
                                    
                                    # Simpan jika belum ada atau update prioritaskan hujan petir
                                    if province not in temp_results:
                                        temp_results[province] = status
                                    elif status == "Hujan Petir" and temp_results[province] == "Hujan Lebat":
                                        temp_results[province] = status
                
                # Convert ke list
                for prov, status in temp_results.items():
                    results.append({'region': prov, 'status': status})
                    
                results.sort(key=lambda x: x['region'])
                
        except Exception as e:
            print(f"XML Fallback error: {e}")
            
        return results

    def fetch_extreme_weather_alternate(self, day_offset: int = 0) -> List[Dict[str, str]]:
        """
        Alternate method using api.bmkg.go.id if main XML is blocked.
        Note: This is slower because it might need multiple requests, 
        so we just implement a lightweight check or return empty for now to avoid timeout.
        """
        # For now, just return empty to handle the error gracefully
        print("Mencoba mengambil data alternatif (Not implemented yet due to performance)...")
        return []

    def cleanup_old_images(self, keep_days: int = 30):
        """
        Hapus gambar lama (kecuali yang latest)
        
        Args:
            keep_days: Berapa hari gambar disimpan
        """
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 86400)
            
            for filename in os.listdir(self.save_dir):
                if filename.endswith('.png') and 'latest' not in filename:
                    filepath = os.path.join(self.save_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        print(f"🗑️ Deleted old image: {filename}")
        except Exception as e:
            print(f"Error cleaning up images: {e}")


# Test modul
if __name__ == "__main__":
    print("=== Test BMKG Image Fetcher ===\n")
    
    fetcher = BMKGImageFetcher()
    
    # Test download gambar satelit
    print("1. Download gambar satelit Himawari:")
    filepath, is_updated = fetcher.download_image('satelit')
    
    if filepath:
        print(f"\n✅ Success!")
        print(f"File: {filepath}")
        print(f"Updated: {is_updated}")
        
        # Show info
        info = fetcher.get_image_info('satelit')
        print(f"\nInfo:")
        print(f"  Size: {info['size']:,} bytes")
        print(f"  Modified: {info['modified']}")
        print(f"  Hash: {info['hash']}")
    
    print("\n" + "="*50)
