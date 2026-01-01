"""
Scheduler untuk auto-post gambar prediksi BMKG setiap tanggal 2
"""
import os
import sys
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from dotenv import load_dotenv
from bmkg_image_fetcher import BMKGImageFetcher

load_dotenv()


class BMKGImageScheduler:
    """Scheduler untuk auto-download dan kirim gambar prediksi BMKG"""
    
    def __init__(self, bot_token: str, chat_id: str = None):
        """
        Initialize scheduler
        
        Args:
            bot_token: Token Telegram bot
            chat_id: Chat ID tujuan (optional, bisa diset via env)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID', '')
        self.image_fetcher = BMKGImageFetcher()
        self.bot = Bot(token=bot_token)
        self.scheduler = AsyncIOScheduler()
    
    async def check_and_send_image(self):
        """Check gambar baru dan kirim jika ada update"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 Checking gambar satelit BMKG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # Download gambar satelit
            filepath, is_updated = self.image_fetcher.download_image('satelit')
            
            if not filepath or not os.path.exists(filepath):
                print("❌ Gagal download gambar dari BMKG")
                return
            
            if not is_updated:
                print("ℹ️ Gambar tidak ada update, skip kirim")
                return
            
            # Ada update, kirim ke Telegram
            print("📤 Gambar ada update, mengirim ke Telegram...")
            
            if not self.chat_id:
                print("⚠️ TELEGRAM_CHAT_ID tidak diset, skip kirim")
                return
            
            # Buat caption
            caption = (
                f"🛰️ *Citra Satelit Himawari - Potensi Hujan*\n\n"
                "📅 *Update terbaru dari BMKG!*\n"
                f"🕐 {datetime.now().strftime('%d %B %Y, %H:%M WIB')}\n\n"
                "📊 Sumber: BMKG Indonesia\n"
                "🌐 https://www.bmkg.go.id/\n\n"
                "*Citra Satelit Himawari-9*\n"
                "Potensi curah hujan berdasarkan citra inframerah\n\n"
                "Gunakan /satelit untuk download gambar terbaru 🛰️"
            )
            
            # Kirim gambar
            with open(filepath, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            print(f"✅ Gambar berhasil dikirim ke chat ID: {self.chat_id}")
            
        except Exception as e:
            print(f"❌ Error in check_and_send_image: {e}")
    
    def start(self):
        """Start scheduler"""
        # Job 1: Cek setiap 3 jam (update satelit lebih sering)
        self.scheduler.add_job(
            self.check_and_send_image,
            CronTrigger(
                hour='*/3',
                timezone='Asia/Jakarta'
            ),
            id='satelit_image_check',
            name='Check BMKG Satelit Image Every 3 Hours',
            replace_existing=True
        )
        
        self.scheduler.start()
        
        print("📅 Scheduler started!")
        print(f"✅ Auto-check setiap 3 jam")
        
        # Print next run times
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            print(f"   - {job.name}: {job.next_run_time}")
    
    def stop(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
        print("🛑 Scheduler stopped")


# Test standalone
if __name__ == "__main__":
    print("=== BMKG Image Scheduler Test ===\n")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN tidak ditemukan di .env")
        sys.exit(1)
    
    if not chat_id:
        print("⚠️ Warning: TELEGRAM_CHAT_ID tidak diset")
        print("   Gambar tidak akan dikirim otomatis")
        print("   Set TELEGRAM_CHAT_ID di .env untuk enable auto-send")
    
    scheduler = BMKGImageScheduler(token, chat_id)
    
    # Test manual check
    print("\n1. Testing manual check...")
    import asyncio
    asyncio.run(scheduler.check_and_send_image())
    
    print("\n" + "="*60)
    print("2. Starting scheduler...")
    scheduler.start()
    
    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping scheduler...")
        scheduler.stop()
