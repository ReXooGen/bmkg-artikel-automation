"""
Flask Webhook Server untuk Telegram Bot
"""

from flask import Flask, render_template, request, session, redirect, url_for, flash
from telegram import Update
import asyncio
import os
import secrets

from telegram_bot import get_telegram_app
from bot_config import BOT_NAME
from database import UserDatabase
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Telegram App (Lazy loading)
telegram_app = None
telegram_app_loop = None

def get_tel_app():
    global telegram_app, telegram_app_loop
    
    # Get current event loop
    try:
        current_loop = asyncio.get_event_loop()
    except RuntimeError:
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)
    
    # Reinitialize if loop has changed (important for serverless)
    if telegram_app is None or telegram_app_loop != current_loop:
        try:
            telegram_app = get_telegram_app()
            telegram_app_loop = current_loop
            logger.info("Telegram app initialized/refreshed")
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
    
    # Secret key for sessions
    app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
    
    # Admin password from environment or default
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'lukagataupasswordnya')
    
    # Initialize database
    db = UserDatabase()
    
    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login route"""
        if request.method == 'POST':
            password = request.form.get('password', '')
            if password == ADMIN_PASSWORD:
                session['authenticated'] = True
                return redirect(url_for('dashboard'))
            else:
                flash('Password salah!', 'error')
        return render_template('login.html')
    
    # Logout route
    @app.route('/logout')
    def logout():
        """Logout route"""
        session.pop('authenticated', None)
        return redirect(url_for('login'))
    
    # Dashboard route (protected)
    @app.route('/', methods=['GET'])
    def dashboard():
        """Dashboard route - protected"""
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        
        # Get statistics
        total_users = db.get_total_users()
        all_users = db.get_all_users()
        most_active = db.get_most_active_users(limit=10)
        recent_activity = db.get_recent_activity(limit=20)
        
        webhook_url = os.getenv('WEBHOOK_URL', 'https://bmkg-artikel.vercel.app')
        
        return render_template('index.html',
                             bot_name=BOT_NAME,
                             webhook_url=webhook_url,
                             total_users=total_users,
                             all_users=all_users,
                             most_active=most_active,
                             recent_activity=recent_activity)
    
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
            
            # Process the update with fresh event loop per request
            async def process_update_async():
                try:
                    # Initialize application just in case
                    if not application._initialized:
                        await application.initialize()
                    await application.process_update(update)
                finally:
                    # Shutdown application to close httpx client and release loop binding
                    # This ensures next request can re-initialize with new loop
                    if application._initialized:
                        await application.shutdown()
            
            # Create fresh event loop for each webhook request
            # This prevents event loop binding issues in serverless
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run and wait for completion
                loop.run_until_complete(process_update_async())
            finally:
                # Clean up but don't close the loop to avoid httpx issues
                # Let Python garbage collector handle it
                asyncio.set_event_loop(None)
            
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Telegram webhook error: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
