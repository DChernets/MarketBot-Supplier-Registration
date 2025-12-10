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

# Content Generation Settings
ENABLE_CONTENT_GENERATION = os.getenv("ENABLE_CONTENT_GENERATION", "True").lower() == "true"
DAILY_IMAGE_GENERATION_LIMIT = int(os.getenv("DAILY_IMAGE_GENERATION_LIMIT", "1"))
DAILY_DESCRIPTION_GENERATION_LIMIT = int(os.getenv("DAILY_DESCRIPTION_GENERATION_LIMIT", "1"))
DAILY_CONTENT_ENHANCEMENT_LIMIT = int(os.getenv("DAILY_CONTENT_ENHANCEMENT_LIMIT", "1"))

# Background Templates Settings
BACKGROUND_TEMPLATES_PATH = os.getenv("BACKGROUND_TEMPLATES_PATH", "assets/backgrounds/")
MAX_IMAGE_SIZE = (1920, 1080)  # 16:9 соотношение для контент-генерации
ENHANCED_IMAGE_QUALITY = 95
ENHANCED_IMAGE_FORMAT = "JPEG"

# Content Generation Auto-enhancement Settings
AUTO_GENERATE_CONTENT = os.getenv("AUTO_GENERATE_CONTENT", "True").lower() == "true"
PREFERRED_BACKGROUND_TYPE = os.getenv("PREFERRED_BACKGROUND_TYPE", "professional")  # "professional" or "marketing"