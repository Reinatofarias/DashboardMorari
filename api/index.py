import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set BASE_DIR for Vercel environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from server import app as flask_app

def handler(request):
    return flask_app