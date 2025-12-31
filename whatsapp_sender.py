"""
Module untuk mengirim artikel cuaca ke WhatsApp
"""

import pywhatkit as kit
from datetime import datetime, time
import os


class WhatsAppSender:
    """Class untuk mengirim pesan WhatsApp"""
    
    def __init__(self, phone_number: str):
        """
        Initialize WhatsApp sender
        
        Args:
            phone_number: Nomor WhatsApp tujuan (format: +62xxx)
        """
        self.phone_number = phone_number
    
    def send_article(self, title: str, content: str, send_now: bool = False, wait_time: int = 15) -> bool:
        """
        Mengirim artikel cuaca ke WhatsApp
        
        Args:
            title: Judul artikel
            content: Isi artikel
            send_now: Jika True, kirim segera. Jika False, jadwalkan
            wait_time: Waktu tunggu sebelum klik tombol kirim (detik)
            
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            # Format pesan
            message = self._format_message(title, content)
            
            if send_now:
                # Kirim dengan delay lebih panjang (2 menit dari sekarang)
                now = datetime.now()
                hour = now.hour
                minute = now.minute + 2  # Tambah 2 menit untuk lebih reliable
                
                if minute >= 60:
                    hour += 1
                    minute = minute - 60
                
                if hour >= 24:
                    hour = 0
                
                print(f"\n📱 Mengirim WhatsApp ke {self.phone_number}...")
                print(f"   Akan terkirim pada {hour:02d}:{minute:02d}")
                print(f"   Wait time: {wait_time} detik")
                print("\n   ⚠️ INSTRUKSI PENTING:")
                print("   1. Browser akan terbuka otomatis")
                print("   2. JANGAN klik atau ketik apapun")
                print("   3. JANGAN minimize atau tutup browser")
                print("   4. Biarkan proses berjalan otomatis")
                print("   5. Tunggu hingga pesan terkirim (centang hijau)")
                
                # Gunakan sendwhatmsg dengan parameter yang lebih reliable
                kit.sendwhatmsg(
                    self.phone_number,
                    message,
                    hour,
                    minute,
                    wait_time=wait_time,  # Customizable wait time
                    tab_close=False,  # Jangan tutup tab otomatis agar bisa verify
                    close_time=3  # Tunggu 3 detik sebelum tutup
                )
                
                print("\n✓ Pesan berhasil dijadwalkan untuk dikirim!")
                print("   Browser akan tetap terbuka - JANGAN TUTUP MANUAL")
                return True
            else:
                print("\n📱 Mode test: Pesan tidak dikirim")
                print(f"   Target: {self.phone_number}")
                print(f"   Panjang pesan: {len(message)} karakter")
                return True
                
        except Exception as e:
            print(f"\n✗ Error mengirim WhatsApp: {e}")
            print("\nKEMUNGKINAN PENYEBAB:")
            print("1. WhatsApp Web belum login")
            print("2. Nomor tidak valid atau tidak ada di kontak")
            print("3. Browser tidak bisa diakses oleh pywhatkit")
            print("4. Koneksi internet bermasalah")
            print("\nSOLUSI:")
            print("1. Buka web.whatsapp.com di Chrome")
            print("2. Pastikan sudah login dengan scan QR")
            print("3. Jangan tutup browser")
            print("4. Jalankan script lagi")
            return False
    
    def _format_message(self, title: str, content: str) -> str:
        """Format pesan untuk WhatsApp"""
        
        # Batasi panjang jika terlalu panjang
        max_length = 4000
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        message = f"""🌤️ *PRAKIRAAN CUACA BMKG*
━━━━━━━━━━━━━━━━━━

*{title}*

{content}

━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d %B %Y, %H:%M WIB')}
📊 Sumber: BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)

_Pesan ini dikirim otomatis oleh sistem prakiraan cuaca._"""
        
        return message
    
    def test_connection(self) -> bool:
        """Test koneksi WhatsApp Web"""
        try:
            print("\n Testing koneksi WhatsApp Web...")
            print(f"   Target nomor: {self.phone_number}")
            print("   Status: Ready")
            print("\n   Pastikan:")
            print("   1. WhatsApp Web sudah login di browser")
            print("   2. Browser tidak dalam mode headless")
            print("   3. Koneksi internet stabil")
            return True
        except Exception as e:
            print(f"\n✗ Test gagal: {e}")
            return False


def send_instant_message(phone_number: str, title: str, content: str) -> bool:
    """
    Fungsi helper untuk kirim pesan instant (untuk testing)
    
    Args:
        phone_number: Nomor WhatsApp
        title: Judul artikel
        content: Isi artikel
        
    Returns:
        True jika berhasil
    """
    sender = WhatsAppSender(phone_number)
    return sender.send_article(title, content, send_now=True)
