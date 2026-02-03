import sys
import os

# Add parent directory to path for Vercel serverless
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webhook_server import create_app

app = create_app()
