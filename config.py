"""App-wide constants. Change look-and-feel or menu structure here only."""
import pytz

APP_TITLE = "EVOL Space"
APP_ICON = "🌙"
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone

# Sidebar navigation: label -> bootstrap icon name (streamlit-option-menu)
MENU_OPTIONS = ["Home", "Login", "Music", "About", "His-tory", "Relax", "Map", "Photobooth", "???"]
MENU_ICONS = ["person-rolodex", "box-arrow-in-right", "music-note-beamed", "lightbulb",
              "menu-button", "bell", "geo-alt", "camera", "door-open"]

# Secret key that unlocks the hidden "???" blog tab
SECRET_KEY = "/Evolut!0n"

# Map marker icon choices: label shown in the UI -> Font Awesome icon name
PLACE_ICON_CHOICES = {
    "📍 Marker": "map-marker",
    "🏠 Home": "home",
    "⭐ Star": "star",
    "❤️ Heart": "heart",
    "☕ Cafe": "coffee",
    "🌳 Park / Nature": "tree",
    "🍽️ Food": "cutlery",
    "🏨 Hotel": "bed",
    "🎓 School": "graduation-cap",
    "🎁 Gift": "gift",
    "🚩 Flag": "flag",
    "🎵 Music": "music",
}
PLACE_ICON_COLORS = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "pink"]

# Photobooth filters (must match keys handled in utils.image_filters.apply_filter)
PHOTO_FILTERS = ["None", "Grayscale", "Sepia", "Invert", "Blur", "Vintage"]
