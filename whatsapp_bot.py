"""
WhatsApp Bot menggunakan PyWa (WhatsApp Cloud API)
"""

from flask import Flask
from pywa import WhatsApp
from pywa.types import Message, Button
from bot_config import (
    WA_PHONE_ID, 
    WA_TOKEN, 
    WA_VERIFY_TOKEN,
    validate_config,
    BOT_NAME
)
from bot_handlers import BotHandlers
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BMKGWeatherBot:
    """BMKG Weather Bot dengan PyWa"""
    
    def __init__(self):
        """Initialize bot"""
        # Validate configuration
        try:
            validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise
        
        # Create Flask app first
        self.flask_app = Flask(__name__)
        
        # Initialize PyWa client without automatic webhook registration
        self.wa = WhatsApp(
            phone_id=WA_PHONE_ID,
            token=WA_TOKEN,
            server=self.flask_app,
            verify_token=WA_VERIFY_TOKEN,
            validate_updates=False,  # Disable signature validation for now
        )
        
        # Initialize handlers
        self.handlers = BotHandlers()
        
        # Register message handlers
        self._register_handlers()
        
        logger.info(f"{BOT_NAME} initialized successfully")
    
    def _register_handlers(self):
        """Register message handlers"""
        
        @self.wa.on_message()
        def handle_message(client: WhatsApp, msg: Message):
            """Main message handler"""
            try:
                user_phone = msg.from_user.wa_id
                user_name = msg.from_user.name
                message_text = msg.text.strip() if msg.text else ""
                
                logger.info(f"Message from {user_name} ({user_phone}): {message_text}")
                
                # Parse command
                if message_text.startswith('/'):
                    response = self._handle_command(message_text, user_name)
                else:
                    # Handle non-command messages
                    response = self._handle_text(message_text, user_name)
                
                # Send response
                msg.reply(text=response, quote=False)
                
                logger.info(f"Response sent to {user_phone}")
                
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                try:
                    msg.reply(text="⚠️ Terjadi kesalahan. Silakan coba lagi.", quote=False)
                except:
                    pass
    
    def _handle_command(self, message: str, user_name: str) -> str:
        """Handle command messages"""
        parts = message.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove /
        args = parts[1] if len(parts) > 1 else ""
        
        # Route to appropriate handler
        if command == "start" or command == "mulai":
            return self.handlers.handle_start(user_name)
        
        elif command == "help" or command == "bantuan":
            return self.handlers.handle_help()
        
        elif command == "cuaca":
            return self.handlers.handle_cuaca(args)
        
        elif command == "cuaca3":
            return self.handlers.handle_cuaca3()
        
        elif command == "artikel":
            return self.handlers.handle_artikel()
        
        elif command == "list" or command == "daftar":
            return self.handlers.handle_list()
        
        else:
            return self.handlers.handle_unknown(message)
    
    def _handle_text(self, message: str, user_name: str) -> str:
        """Handle non-command text messages"""
        message_lower = message.lower()
        
        # Greetings
        if any(word in message_lower for word in ['halo', 'hai', 'hello', 'hi', 'hei']):
            return self.handlers.handle_start(user_name)
        
        # Help keywords
        elif any(word in message_lower for word in ['bantuan', 'help', 'tolong', 'gimana']):
            return self.handlers.handle_help()
        
        # Assume user wants weather for a city
        else:
            # Try to extract city name
            return self.handlers.handle_cuaca(message)
    
    def get_app(self):
        """Get Flask app for webhook"""
        return self.flask_app
    
    def close(self):
        """Cleanup resources"""
        if self.handlers:
            self.handlers.close()
        logger.info(f"{BOT_NAME} closed")


# For testing
if __name__ == "__main__":
    print("⚠️  Don't run this directly!")
    print("Use: python webhook_server.py")
