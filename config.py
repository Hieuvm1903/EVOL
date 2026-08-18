"""App-wide constants. Change look-and-feel or menu structure here only."""
import os

import pytz

APP_TITLE = "EVOL Space"
APP_ICON = "🌙"
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone

# Secret key that unlocks the hidden "???" blog tab
SECRET_KEY = "/Evolut!0n"

# --- Google Sheets (replaces the old SQLite data.db) -----------------------
# The ID from your sheet's URL: https://docs.google.com/spreadsheets/d/**THIS**/edit
#
# This constant is only the DEV-mode fallback (see db/sheets_db.py). Once
# deployed, db/sheets_db.py reads st.secrets["sheets"]["spreadsheet_id"]
# instead, so you don't need to change this value before deploying — just
# set the same key in the deployed app's Secrets.
SPREADSHEET_ID = "1T4MJ_HpanXnpo1ZklGMROyQ_bZ_Uc2goOKUA41wgaE4"

# Photos are still cached locally + synced to R2 (see services/photos_service.py
# and services/remote_storage.py) — only the relational data moved to Sheets.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(ROOT_DIR, "assets", "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Map marker icon choices: label shown in the UI -> Font Awesome icon name
# Map marker icon choices: label shown in the UI -> Font Awesome icon name
PLACE_ICON_CHOICES = {
    "📍": "map-marker",
    "🏠": "home",
    "⭐": "star",
    "❤️": "heart",
    "☕": "coffee",
    "🌳": "tree",
    "🍽️": "cutlery",
    "🏨": "bed",
    "🎓": "graduation-cap",
    "🎁": "gift",
    "🚩": "flag",
    "🎵": "music",
    "🎉": "glass",
    "🛍️": "shopping-cart",
    "🎬": "film",
    "📷": "camera-retro",
    "🏛️": "university",
    "🚗": "car",
    "🌊": "tint",
    "🎡": "ticket",
}

# Photobooth filters (must match keys handled in utils.image_filters.apply_filter)
PHOTO_FILTERS = ["None", "Grayscale", "Sepia", "Invert", "Blur", "Vintage"]
MENU_OPTIONS = [
    "Home",
    "Login",
    "Music",
    "About",
    "His-tory",
    "Relax",
    "Map",
    "Photobooth",
    "???",
]
MENU_ICONS = [
    "house",
    "box-arrow-in-right",
    "music-note-list",
    "info-circle",
    "clock-history",
    "flower1",
    "geo-alt",
    "camera",
    "lock",
]