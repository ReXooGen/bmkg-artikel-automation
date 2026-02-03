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

# Initialize Telegram App (Lazy loading) - Removed global caching to prevent event loop issues
# telegram_app = None
# telegram_app_loop = None

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
    
    # Check for Vercel environment to warn about persistence
    IS_VERCEL = os.environ.get('VERCEL') == '1'
    
    # Admin password from environment or default
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'bmkg2026')
    
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
        
        # Determine Webhook URL intelligently
        if IS_VERCEL:
            # Use the request host to determine the URL dynamically
            scheme = request.headers.get('X-Forwarded-Proto', 'https')
            host = request.headers.get('Host', request.host)
            webhook_url = f"{scheme}://{host}"
        else:
            webhook_url = os.getenv('WEBHOOK_URL', 'http://localhost:5000')
        
        return render_template('index.html',
                             bot_name=BOT_NAME,
                             webhook_url=webhook_url,
                             total_users=total_users,
                             all_users=all_users,
                             most_active=most_active,
                             recent_activity=recent_activity,
                             is_vercel=IS_VERCEL) # Pass persistence warning flag
    
    # Add health check endpoint
    @app.route('/health')
    def health():
        return {"status": "ok", "bot": BOT_NAME}

    # Telegram Webhook Endpoint
    @app.route('/telegram', methods=['POST'])
    def telegram_webhook():
        try:
            # Retrieve the JSON data from the request
            data = request.get_json(force=True)
            if not data:
                return {"error": "No JSON data received"}, 400

            # Create fresh event loop for each webhook request
            # This is crucial for Vercel Serverless environment
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process_update_async():
                try:
                    # Create NEW application instance per request
                    # This ensures HTTPX client attaches to the CURRENT loop
                    app_instance = get_telegram_app()
                    if not app_instance:
                        logger.error("Failed to create telegram app")
                        return

                    # Initialize app to setup http client
                    await app_instance.initialize()
                    
                    # Process Update
                    update = Update.de_json(data, app_instance.bot)
                    await app_instance.process_update(update)
                    
                except Exception as e:
                    logger.error(f"Error inside async process: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                finally:
                    # Always shutdown to close http client and free loop binding
                    if 'app_instance' in locals() and app_instance and app_instance._initialized:
                        await app_instance.shutdown()

            try:
                loop.run_until_complete(process_update_async())
            finally:
                loop.close()
                asyncio.set_event_loop(None)
            
            return {"status": "ok"}
            
        except Exception as e:
            logger.error(f"Telegram webhook fatal error: {e}")
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
