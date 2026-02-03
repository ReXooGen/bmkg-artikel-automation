"""
Flask Webhook Server untuk WhatsApp Bot
"""

from flask import Flask, render_template, request
from telegram import Update
import asyncio
import os

from whatsapp_bot import BMKGWeatherBot
from telegram_bot import get_telegram_app
from bot_config import PORT, WEBHOOK_URL, BOT_NAME
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
    
    # Initialize bot
    bot = BMKGWeatherBot()
    
    # Get Flask app from PyWa
    app = bot.get_app()
    # Update template folder
    app.template_folder = template_dir
    
    # Add health check endpoint
    @app.route('/health')
    def health():
        return {"status": "ok", "bot": BOT_NAME}
    
    # Add info endpoint
    @app.route('/')
    def info():
        return render_template('index.html', 
                             bot_name=BOT_NAME, 
                             webhook_url=WEBHOOK_URL)

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
                # optionally await application.shutdown() if truly stateless, 
                # but might verify connection close. 
                # For Vercel, simpler is often better.
            
            # Run async loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_update_async())
            loop.close()
            
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Telegram webhook error: {e}")
            return {"error": str(e)}, 500
    
    logger.info(f"{BOT_NAME} initialized successfully")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    print("\n" + "="*60)
    print(f"🤖 {BOT_NAME} Starting...")
    print("="*60)
    print(f"\n📡 Webhook URL: {WEBHOOK_URL}")
    print(f"🌐 Port: {PORT}")
    print("\n⚙️  Make sure to:")
    print("   1. Set webhook URL in Meta Developer Console")
    print("   2. WhatsApp phone number is configured")
    print("   3. Access token is valid")
    print("\n🚀 Server starting...\n")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False
    )
