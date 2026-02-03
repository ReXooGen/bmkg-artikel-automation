"""
Flask Webhook Server untuk Telegram Bot
"""

from flask import Flask, render_template, request
from telegram import Update
import asyncio
import os

from telegram_bot import get_telegram_app
from bot_config import BOT_NAME
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Telegram App (Lazy loading)
telegram_app = None

def get_tel_app():
    global telegram_app
    if telegram_app is None:
        try:
            telegram_app = get_telegram_app()
        except Exception as e:
            logger.error(f"Failed to init Telegram app: {e}")
    return telegram_app

def create_app():
    """Create and configure Flask app"""
    
    # Set template folder explicitly for Vercel
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    
    logger.info(f"Initializing {BOT_NAME}...")
    logger.info(f"Template dir: {template_dir}")
    
    # Create Flask app
    app = Flask(__name__, template_folder=template_dir)
    
    # Dashboard route
    @app.route('/', methods=['GET'])
    def dashboard():
        """Dashboard route"""
        webhook_url = os.getenv('WEBHOOK_URL', 'https://bmkg-artikel.vercel.app')
        return render_template('index.html', 
                             bot_name=BOT_NAME, 
                             webhook_url=webhook_url)
    
    # Add health check endpoint
    @app.route('/health')
    def health():
        return {"status": "ok", "bot": BOT_NAME}

    # Telegram Webhook Endpoint
    @app.route('/telegram', methods=['POST'])
    def telegram_webhook():
        application = get_tel_app()
        if not application:
            return {"error": "Telegram bot not configured"}, 500
            
        try:
            # Retrieve the JSON data from the request
            data = request.get_json(force=True)
            # Decode the update from JSON
            update = Update.de_json(data, application.bot)
            
            # Process the update
            async def process_update_async():
                # Initialize application just in case
                if not application._initialized:
                    await application.initialize()
                await application.process_update(update)
            
            # Run async code without closing event loop prematurely
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run and wait for completion, but don't close loop
            loop.run_until_complete(process_update_async())
            
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Telegram webhook error: {e}")
            return {"error": str(e)}, 500
    
    logger.info(f"{BOT_NAME} initialized successfully")
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    PORT = int(os.getenv('PORT', 5000))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:5000')
    
    print("\n" + "="*60)
    print(f"🤖 {BOT_NAME} Starting...")
    print("="*60)
    print(f"\n📡 Webhook URL: {WEBHOOK_URL}")
    print(f"🌐 Port: {PORT}")
    print("\n⚙️  Make sure to:")
    print("   1. Set Telegram webhook URL")
    print("   2. Bot token is configured")
    print("\n🚀 Server starting...\n")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False
    )
