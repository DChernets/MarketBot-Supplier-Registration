# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MarketBot is a Telegram bot for wholesale suppliers to:
- Register with marketplace locations (markets, pavilions)
- Upload product photos for AI recognition
- Auto-generate professional product content (images & descriptions)
- Store supplier data and products in Google Sheets
- Post content to Telegram channels (VK planned for future)

**Tech Stack:** Python 3, python-telegram-bot v20.7, Google Sheets/Drive APIs, Google Gemini API, Pillow, httpx (async)

## Commands

```bash
# Run the bot
./run_bot.sh                    # Starts bot in background with log rotation
python3 src/main.py             # Direct run (foreground)

# Stop the bot
pkill -f "python.*src/main.py"

# View logs
./view_logs.sh
tail -f logs/bot.log

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Core Services

| File | Purpose |
|------|---------|
| `src/main.py` | Bot orchestrator, all Telegram handlers, state machine |
| `src/config.py` | Environment variables, API keys, limits configuration |
| `src/google_sheets.py` | Google Sheets data layer (suppliers, locations, products) |
| `src/gemini_service.py` | Product image recognition via Gemini 2.0 Flash |
| `src/content_generation_service.py` | AI content enhancement via Gemini 2.5 Flash Image |
| `src/image_storage.py` | Google Drive image upload/management |
| `src/usage_limits.py` | Daily rate limiting per user |
| `src/background_templates.py` | Image background templates with Pillow |

### State Machine Flow

```
Registration: NAME → MARKET → PAVILION → PHONE → ADD_MORE_PHONES → ADD_LOCATION
Photo Upload: PHOTO_UPLOAD → PHOTO_CONFIRMATION → LOCATION_SELECTION → QUANTITY_INPUT
```

### Data Flow: Product Upload

1. User sends photo → Bot downloads via Telegram API
2. Photo sent to `gemini_service.recognize_product()` → Returns JSON with product info
3. User confirms → Selects location → Enters quantity
4. Product saved to Google Sheets via `google_sheets.save_products()`
5. If AUTO_GENERATE_CONTENT=true → `content_generation_service.enhance_product_content()` runs

### Google Sheets Structure

- **suppliers**: internal_id, telegram_user_id, contact_name, timestamps
- **locations**: location_id, supplier_internal_id, market_name, pavilion_number, phones
- **products**: product_id, supplier_id, location_id, product fields (название, описание, etc.), photo_urls, enhanced_*
- **content_usage**: usage tracking for rate limiting
- **content_limits**: daily limits per user

### Key Patterns

- **Singleton services**: `get_gemini_service()`, `get_content_generation_service()`, `GoogleSheetsManager.get_instance()`
- **Lazy initialization**: Services initialize on first use, not at startup
- **60-second cache**: Google Sheets queries cached to reduce API calls
- **Exponential backoff**: Retry on 429/503 with 2^n second delays
- **Proxy support**: Configurable via USE_PROXY, HTTP_PROXY, HTTPS_PROXY env vars

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `GOOGLE_SHEETS_SPREADSHEET_ID` - Target spreadsheet ID
- `GEMINI_API_KEY` - Google Gemini API key

Optional:
- `GEMINI_RECOGNITION_MODEL` (default: gemini-2.0-flash-exp)
- `GEMINI_CONTENT_GENERATION_MODEL` (default: gemini-2.5-flash-image)
- `USE_PROXY`, `HTTP_PROXY`, `HTTPS_PROXY` - Proxy configuration
- `AUTO_GENERATE_CONTENT` (default: True)
- `DAILY_*_LIMIT` - Rate limits (default: 1/day each)

## Gemini API Integration

Two models are used:
1. **Recognition** (`gemini-2.0-flash-exp`): Analyzes product photos, returns JSON with название, описание, материал, размеры, производство, упаковка
2. **Content Generation** (`gemini-2.5-flash-image`): Enhances product images and generates marketing descriptions

Both use direct HTTP calls via httpx (not the google-generativeai SDK) for better async control.

## Bot Commands (User-facing)

- `/start` - Register as supplier
- `/profile` - View/edit profile and locations
- `/help` - Display help
- `/cancel` - Cancel current operation
- Inline buttons: 📸 ФОТО (upload), 📦 МОИ ТОВАРЫ (view products), ✨ Улучшить контент (enhance)
