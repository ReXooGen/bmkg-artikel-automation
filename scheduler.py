"""
Scheduler untuk menjalankan program otomatis pada jam 4 pagi
"""

import schedule
import time
from datetime import datetime
import subprocess
import sys


def run_weather_automation():
    """Menjalankan program automasi cuaca"""
    print("\n" + "="*60)
    print(f"🕐 SCHEDULER TRIGGERED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # Jalankan main.py
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 menit timeout
        )
        
        if result.returncode == 0:
            print("\n✓ Program berhasil dijalankan!")
            print("\nOutput:")
            print(result.stdout)
        else:
            print(f"\n✗ Program error (exit code: {result.returncode})")
            print("\nError:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("\n✗ Program timeout (lebih dari 5 menit)")
    except Exception as e:
        print(f"\n✗ Error menjalankan program: {e}")


def start_scheduler():
    """Memulai scheduler"""
    
    print("="*60)
    print("🤖 SCHEDULER AUTOMASI CUACA BMKG")
    print("="*60)
    print("\n⏰ Jadwal:")
    print("   - Mulai: 2 Januari 2026")
    print("   - Setiap hari jam 04:00 pagi")
    print("   - Artikel akan digenerate dan dikirim ke WhatsApp")
    print("\n📱 Target WhatsApp: +62 858-0626-8213")
    print("\n⚠️ PERHATIAN:")
    print("   - Jangan tutup terminal ini")
    print("   - WhatsApp Web harus tetap login")
    print("   - Komputer harus tetap menyala")
    print("\n" + "="*60)
    
    # Jadwalkan untuk jam 4 pagi setiap hari
    schedule.every().day.at("04:00").do(run_weather_automation)
    
    print(f"\n✓ Scheduler aktif sejak: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⏳ Menunggu jadwal berikutnya...\n")
    
    # Loop untuk menjalankan scheduler
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check setiap 1 menit
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Scheduler dihentikan oleh user")
        print("Program berhenti.\n")


if __name__ == "__main__":
    start_scheduler()
