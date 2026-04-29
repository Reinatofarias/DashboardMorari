import sys
import os

# Add scripts folder to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Set working directory for file paths
os.chdir(os.path.join(os.path.dirname(__file__), 'scripts'))

# Import the Flask app
from server import app

# Vercel requires returning the app directly
def handler(request):
    return app