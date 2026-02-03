"""
Modul untuk mengambil gambar prediksi curah hujan dari BMKG
"""
import os
import requests
from datetime import datetime
from typing import Optional, Tuple
import hashlib
from pathlib import Path


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
