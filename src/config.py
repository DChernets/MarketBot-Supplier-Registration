import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "config/google_credentials.json")
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Google Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# Google Drive Configuration
GOOGLE_DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Image Processing Settings
MAX_PHOTO_SIZE_MB = 20
MAX_PHOTO_COUNT = 10
SUPPORTED_PHOTO_FORMATS = ['jpg', 'jpeg', 'png', 'webp']
PHOTO_QUALITY = 85

# Google Drive Folder Settings
DRIVE_FOLDER_NAME = "MarketBot Images"

# Proxy Settings
HTTP_PROXY = os.getenv("HTTP_PROXY")
HTTPS_PROXY = os.getenv("HTTPS_PROXY")

# Configure proxy for all HTTP requests
if HTTP_PROXY or HTTPS_PROXY:
    import urllib.request
    proxy_handler = urllib.request.ProxyHandler({
        'http': HTTP_PROXY,
        'https': HTTPS_PROXY
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)