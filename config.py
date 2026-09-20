import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key-for-dev')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASS = os.environ.get('EMAIL_PASS')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
