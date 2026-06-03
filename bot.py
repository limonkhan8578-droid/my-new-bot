import asyncio
import io
import re
import json
import html
import os
import httpx
import pyotp
import random
import string
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

# ==================== CONFIG SECTION ====================

BOT_TOKEN = "8985209386:AAHyfXdTLEM_u_SawzBelJylOrGsZZzKp4A"
API_KEY = "MURAD_40D9DD648330B6DE30BA69C4"  # আপনার নতুন এপিআই কি
BASE_URL = "http://voltxlite.com"           # আপনার নতুন এপিআই ডোমেন
USER_DATA_FILE = "users.json"
PAID_SMS_FILE = "paid_sms.json"
STATS_FILE = "user_stats.json"
REFERRAL_DATA_FILE = "referral_data.json"
BANNED_USERS_FILE = "banned_users.json"
WITHDRAW_DATA_FILE = "withdraw_requests.json"
ACTIVITY_LOGS_FILE = "activity_logs.json"
DATA_RANGE_FILE = "datarange.json"

# ==================== MULTIPLE ADMINS CONFIGURATION ====================
ADMINS = [7087989353]  


OTP_GROUP_ID = -1003880345384

# ==================== WELCOME MESSAGE CONFIGURATION ====================
WELCOME_MESSAGE = """✨ **WELCOME TO MAAMARJAN** ✨
━━━━━━━━━━━━━━━━━━━━━━
🚀 **START EARNING NOW!** 🚀"""

# ==================== OTP RATE CONFIGURATION ====================
OTP_RATE = 0.00  # প্রতিটা OTP এর জন্য ইউজার কত টাকা পাবে (BDT)

# ==================== FORCE JOIN CHANNELS CONFIGURATION ====================
FORCE_JOIN_CHANNELS = {
    "MAIN_CHANNEL": "https://t.me/kalamking32900",
    "BACKUP_CHANNEL": "https://t.me/becup3290",
    "OTP_GROUP": "https://t.me/kalamifxvvv223"
}

# ==================== USER JOIN STATUS TRACKING ====================
user_joined_status = set()

# Referral price configuration
REFERRAL_PRICE = 0

# Withdraw limits
MIN_WITHDRAW = 50
MAX_WITHDRAW = 10000

request_queue = asyncio.Queue() 
MAX_WORKERS = 5000 

# এপিআই কি সরাসরি হেডারে সেট করা হলো যা কানেকশন সুপারফাস্ট রাখবে
client_async = httpx.AsyncClient(
    timeout=10.0, 
    headers={"X-API-Key": API_KEY},
    limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200)
)

active_numbers = {}
last_range = {}
CHECK_INTERVAL = 1.5  # ১.৫ সেকেন্ড পর পর অতি দ্রুত ওটিপি স্ক্যান করবে

# ==================== CHECK IF USER IS ADMIN ====================

def is_admin(user_id):
    return user_id in ADMINS

# ==================== WITHDRAW DATA FUNCTIONS ====================

def load_withdraw_requests():
    if not os.path.exists(WITHDRAW_DATA_FILE):
        with open(WITHDRAW_DATA_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(WITHDRAW_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_withdraw_requests(data):
    with open(WITHDRAW_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_payment_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

# ==================== BANNED USERS FUNCTIONS ====================

def load_banned_users():
    if not os.path.exists(BANNED_USERS_FILE):
        with open(BANNED_USERS_FILE, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(BANNED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_banned_users(banned_list):
    with open(BANNED_USERS_FILE, "w") as f:
        json.dump(banned_list, f, indent=4)

def is_user_banned(uid):
    banned_list = load_banned_users()
    return str(uid) in banned_list

def ban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str not in banned_list:
        banned_list.append(uid_str)
        save_banned_users(banned_list)
        return True
    return False

def unban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str in banned_list:
        banned_list.remove(uid_str)
        save_banned_users(banned_list)
        return True
    return False

# ==================== REFERRAL DATA FUNCTIONS ====================

def load_referral_data():
    if not os.path.exists(REFERRAL_DATA_FILE):
        with open(REFERRAL_DATA_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(REFERRAL_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_referral_data(data):
    with open(REFERRAL_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_referral_count(uid, count):
    referral_data = load_referral_data()
    uid_str = str(uid)
    if uid_str not in referral_data:
        referral_data[uid_str] = {"referral_count": 0}
    referral_data[uid_str]["referral_count"] = count
    save_referral_data(referral_data)

def get_referral_count(uid):
    referral_data = load_referral_data()
    uid_str = str(uid)
    return referral_data.get(uid_str, {}).get("referral_count", 0)

# ==================== DATA RANGE FILE ====================

def load_range_db():
    if not os.path.exists(DATA_RANGE_FILE):
        return {}
    try:
        with open(DATA_RANGE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_range_db(data):
    with open(DATA_RANGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_number_range_info(uid, number, range_text):
    db = load_range_db()
    flag, name = get_country_info(number)
    db[normalize_number(number)] = {
        "user_id": str(uid),
        "number": f"+{normalize_number(number)}",
        "range": range_text,
        "country": f"{flag} {name}"
    }
    save_range_db(db)

# ==================== COUNTRY MAPPING SECTION ====================

def get_country_info(number):
    number = str(number).strip()
    
    country_map = {
        "2376": ("🇨🇲", "Cameroon"),
        "2250": ("🇨🇮", "Ivory Coast"),
        "2613": ("🇲🇬", "Madagascar"),
        "4077": ("🇷🇴", "Romania"),
        "237": ("🇨🇲", "Cameroon"),
        "225": ("🇨🇮", "Ivory Coast"),
        "261": ("🇲🇬", "Madagascar"),
        "20": ("🇪🇬", "Egypt"),
        "27": ("🇿🇦", "South Africa"),
        "234": ("🇳🇬", "Nigeria"),
        "254": ("🇰🇪", "Kenya"),
        "233": ("🇬🇭", "Ghana"),
        "212": ("🇲🇦", "Morocco"),
        "213": ("🇩🇿", "Algeria"),
        "216": ("🇹🇳", "Tunisia"),
        "218": ("🇱🇾", "Libya"),
        "249": ("🇸🇩", "Sudan"),
        "251": ("🇪🇹", "Ethiopia"),
        "252": ("🇸🇴", "Somalia"),
        "253": ("🇩🇯", "Djibouti"),
        "255": ("🇹🇿", "Tanzania"),
        "256": ("🇺🇬", "Uganda"),
        "257": ("🇧🇮", "Burundi"),
        "258": ("🇲🇿", "Mozambique"),
        "260": ("🇿🇲", "Zambia"),
        "263": ("🇿🇼", "Zimbabwe"),
        "264": ("🇳🇦", "Namibia"),
        "265": ("🇲🇼", "Malawi"),
        "266": ("🇱🇸", "Lesotho"),
        "267": ("🇧🇼", "Botswana"),
        "268": ("🇸🇿", "Swaziland"),
        "269": ("🇰🇲", "Comoros"),
        "220": ("🇬🇲", "Gambia"),
        "221": ("🇸🇳", "Senegal"),
        "222": ("🇲🇷", "Mauritania"),
        "223": ("🇲🇱", "Mali"),
        "224": ("🇬🇳", "Guinea"),
        "226": ("🇧🇫", "Burkina Faso"),
        "227": ("🇳🇪", "Niger"),
        "228": ("🇹🇬", "Togo"),
        "229": ("🇧🇯", "Benin"),
        "230": ("🇲🇺", "Mauritius"),
        "231": ("🇱🇷", "Liberia"),
        "232": ("🇸🇱", "Sierra Leone"),
        "235": ("🇹🇩", "Chad"),
        "236": ("🇨🇫", "Central African Republic"),
        "238": ("🇨🇻", "Cape Verde"),
        "239": ("🇸🇹", "Sao Tome and Principe"),
        "240": ("🇬🇶", "Equatorial Guinea"),
        "241": ("🇬🇦", "Gabon"),
        "242": ("🇨🇬", "Congo"),
        "243": ("🇨🇩", "DR Congo"),
        "244": ("🇦🇴", "Angola"),
        "245": ("🇬🇼", "Guinea-Bissau"),
        "247": ("🇸🇭", "Saint Helena"),
        "248": ("🇸🇨", "Seychelles"),
        "250": ("🇷🇼", "Rwanda"),
        "290": ("🇸🇭", "Saint Helena"),
        "291": ("🇪🇷", "Eritrea"),
        "40": ("🇷🇴", "Romania"),
        "44": ("🇬🇧", "United Kingdom"),
        "33": ("🇫🇷", "France"),
        "49": ("🇩🇪", "Germany"),
        "39": ("🇮🇹", "Italy"),
        "34": ("🇪🇸", "Spain"),
        "31": ("🇳🇱", "Netherlands"),
        "32": ("🇧🇪", "Belgium"),
        "41": ("🇨🇭", "Switzerland"),
        "43": ("🇦🇹", "Austria"),
        "46": ("🇸🇪", "Sweden"),
        "47": ("🇳🇴", "Norway"),
        "45": ("🇩🇰", "Denmark"),
        "358": ("🇫🇮", "Finland"),
        "351": ("🇵🇹", "Portugal"),
        "353": ("🇮🇪", "Ireland"),
        "36": ("🇭🇺", "Hungary"),
        "48": ("🇵🇱", "Poland"),
        "380": ("🇺🇦", "Ukraine"),
        "370": ("🇱🇹", "Lithuania"),
        "371": ("🇱🇻", "Latvia"),
        "372": ("🇪🇪", "Estonia"),
        "373": ("🇲🇩", "Moldova"),
        "374": ("🇦🇲", "Armenia"),
        "375": ("🇧🇾", "Belarus"),
        "376": ("🇦🇩", "Andorra"),
        "377": ("🇲🇨", "Monaco"),
        "378": ("🇸🇲", "San Marino"),
        "379": ("🇻🇦", "Vatican City"),
        "381": ("🇷🇸", "Serbia"),
        "382": ("🇲🇪", "Montenegro"),
        "383": ("🇽尋", "Kosovo"),
        "385": ("🇭🇷", "Croatia"),
        "386": ("🇸🇮", "Slovenia"),
        "387": ("🇧🇦", "Bosnia and Herzegovina"),
        "389": ("🇲🇰", "North Macedonia"),
        "350": ("🇬🇮", "Gibraltar"),
        "352": ("🇱🇺", "Luxembourg"),
        "354": ("🇮🇸", "Iceland"),
        "355": ("🇦🇱", "Albania"),
        "356": ("🇲🇹", "Malta"),
        "357": ("🇨🇾", "Cyprus"),
        "359": ("🇧🇬", "Bulgaria"),
        "421": ("🇸🇰", "Slovakia"),
        "420": ("🇨🇿", "Czech Republic"),
        "298": ("🇫🇴", "Faroe Islands"),
        "299": ("🇬🇱", "Greenland"),
        "1": ("🇺🇸", "United States"),
        "7": ("🇷🇺", "Russia"),
        "91": ("🇮🇳", "India"),
        "92": ("🇵🇰", "Pakistan"),
        "880": ("🇧🇩", "Bangladesh"),
        "86": ("🇨🇳", "China"),
        "81": ("🇯🇵", "Japan"),
        "82": ("🇰🇷", "South Korea"),
        "84": ("🇻🇳", "Vietnam"),
        "66": ("🇹🇭", "Thailand"),
        "62": ("🇮🇩", "Indonesia"),
        "60": ("🇲🇾", "Malaysia"),
        "65": ("🇸🇬", "Singapore"),
        "63": ("🇵🇭", "Philippines"),
        "95": ("🇲🇲", "Myanmar"),
        "94": ("🇱🇰", "Sri Lanka"),
        "977": ("🇳🇵", "Nepal"),
        "93": ("🇦🇫", "Afghanistan"),
        "98": ("🇮🇷", "Iran"),
        "90": ("🇹🇷", "Turkey"),
        "964": ("🇮🇶", "Iraq"),
        "963": ("🇸🇾", "Syria"),
        "961": ("🇱🇧", "Lebanon"),
        "962": ("🇯🇴", "Jordan"),
        "965": ("🇰🇼", "Kuwait"),
        "966": ("🇸🇦", "Saudi Arabia"),
        "967": ("🇾🇪", "Yemen"),
        "968": ("🇴🇲", "Oman"),
        "971": ("🇦🇪", "United Arab Emirates"),
        "972": ("🇮🇱", "Israel"),
        "973": ("🇧🇭", "Bahrain"),
        "974": ("🇶🇦", "Qatar"),
        "994": ("🇦🇿", "Azerbaijan"),
        "995": ("🇬🇪", "Georgia"),
        "996": ("🇰🇬", "Kyrgyzstan"),
        "992": ("🇹🇯", "Tajikistan"),
        "993": ("🇹🇲", "Turkmenistan"),
        "998": ("🇺🇿", "Uzbekistan"),
        "855": ("🇰🇭", "Cambodia"),
        "856": ("🇱🇦", "Laos"),
        "976": ("🇲🇳", "Mongolia"),
        "850": ("🇰🇵", "North Korea"),
        "55": ("🇧🇷", "Brazil"),
        "52": ("🇲🇽", "Mexico"),
        "54": ("🇦🇷", "Argentina"),
        "57": ("🇨🇴", "Colombia"),
        "51": ("🇵🇪", "Peru"),
        "58": ("🇻🇪", "Venezuela"),
        "56": ("🇨🇱", "Chile"),
        "593": ("🇪🇨", "Ecuador"),
        "591": ("🇧🇴", "Bolivia"),
        "595": ("🇵🇾", "Paraguay"),
        "598": ("🇺🇾", "Uruguay"),
        "502": ("🇬🇹", "Guatemala"),
        "503": ("🇸🇻", "El Salvador"),
        "504": ("🇭🇳", "Honduras"),
        "505": ("🇳ิค", "Nicaragua"),
        "506": ("🇨🇷", "Costa Rica"),
        "507": ("🇵🇦", "Panama"),
        "509": ("🇭🇹", "Haiti"),
        "501": ("🇧🇿", "Belize"),
        "61": ("🇦🇺", "Australia"),
        "64": ("🇳🇿", "New Zealand"),
        "675": ("🇵🇬", "Papua New Guinea"),
        "679": ("🇫🇯", "Fiji"),
        "685": ("🇼🇸", "Samoa"),
        "686": ("🇰🇮", "Kiribati"),
        "691": ("🇫🇲", "Micronesia"),
        "692": ("🇲🇭", "Marshall Islands"),
        "297": ("🇦🇼", "Aruba"),
        "1246": ("🇧🇧", "Barbados"),
        "1441": ("🇧🇲", "Bermuda"),
        "1345": ("🇰🇾", "Cayman Islands"),
        "53": ("🇨🇺", "Cuba"),
        "1473": ("🇬🇩", "Grenada"),
        "592": ("🇬🇾", "Guyana"),
        "1876": ("🇯🇲", "Jamaica"),
        "1758": ("🇱🇨", "Saint Lucia"),
        "1784": ("🇻🇨", "Saint Vincent"),
        "1868": ("🇹🇹", "Trinidad and Tobago"),
    }
    
    clean_num = str(number).replace('+', '').replace(' ', '').replace('-', '').strip()
    sorted_prefixes = sorted(country_map.keys(), key=len, reverse=True)
    
    for prefix in sorted_prefixes:
        if clean_num.startswith(prefix):
            return country_map[prefix]
    
    return ("🇨🇮", "IVORY COAST")

# ==================== SERVICE DETECTION SECTION ====================

def detect_service(full_sms):
    if not full_sms:
        return "SMS SERVICE"
    
    sms_lower = full_sms.lower()
    
    service_keywords = {
        "facebook": "FACEBOOK",
        "fb": "FACEBOOK",
        "instagram": "INSTAGRAM",
        "insta": "INSTAGRAM",
        "tiktok": "TIKTOK",
        "twitter": "TWITTER",
        "x.com": "TWITTER",
        "snapchat": "SNAPCHAT",
        "snap": "SNAPCHAT",
        "whatsapp": "WHATSAPP",
        "whats app": "WHATSAPP",
        "telegram": "TELEGRAM",
        "tg": "TELEGRAM",
        "discord": "DISCORD",
        "messenger": "MESSENGER",
        "linkedin": "LINKEDIN",
        "pinterest": "PINTEREST",
        "reddit": "REDDIT",
        "youtube": "YOUTUBE",
        "google": "GOOGLE",
        "gmail": "GOOGLE",
        "line": "LINE",
        "wechat": "WECHAT",
        "viber": "VIBER",
        "skype": "SKYPE",
        "signal": "SIGNAL",
        "imo": "IMO",
        "tumblr": "TUMBLR",
        "flickr": "FLICKR",
        "quora": "QUORA",
        "vk": "VK",
        "ok.ru": "OK",
        "odnoklassniki": "OK",
        "pubg": "PUBG",
        "free fire": "FREE FIRE",
        "freefire": "FREE FIRE",
        "call of duty": "CALL OF DUTY",
        "cod": "CALL OF DUTY",
        "fortnite": "FORTNITE",
        "minecraft": "MINECRAFT",
        "roblox": "ROBLOX",
        "genshin": "GENSHIN IMPACT",
        "clash of clans": "CLASH OF CLANS",
        "clash royale": "CLASH ROYALE",
        "brawl stars": "BRAWL STARS",
        "among us": "AMONG US",
        "valorant": "VALORANT",
        "apex legends": "APEX LEGENDS",
        "league of legends": "LEAGUE OF LEGENDS",
        "lol": "LEAGUE OF LEGENDS",
        "dota": "DOTA",
        "csgo": "CSGO",
        "counter strike": "CSGO",
        "apple": "APPLE",
        "icloud": "APPLE",
        "samsung": "SAMSUNG",
        "xiaomi": "XIAOMI",
        "huawei": "HUAWEI",
        "oppo": "OPPO",
        "vivo": "VIVO",
        "oneplus": "ONEPLUS",
        "realme": "REALME",
        "nokia": "NOKIA",
        "motorola": "MOTOROLA",
        "sony": "SONY",
        "lg": "LG",
        "amazon": "AMAZON",
        "microsoft": "MICROSOFT",
        "outlook": "MICROSOFT",
        "hotmail": "MICROSOFT",
        "yahoo": "YAHOO",
        "dropbox": "DROPBOX",
        "spotify": "SPOTIFY",
        "netflix": "NETFLIX",
        "zoom": "ZOOM",
        "slack": "SLACK",
        "trello": "TRELLO",
        "github": "GITHUB",
        "gitlab": "GITLAB",
        "bitbucket": "BITBUCKET",
        "docker": "DOCKER",
        "paypal": "PAYPAL",
        "payoneer": "PAYONEER",
        "wise": "WISE",
        "transferwise": "WISE",
        "skrill": "SKRILL",
        "neteller": "NETELLER",
        "binance": "BINANCE",
        "coinbase": "COINBASE",
        "blockchain": "BLOCKCHAIN",
        "bkash": "BKASH",
        "nagad": "NAGAD",
        "rocket": "ROCKET",
        "upay": "UPAY",
        "visa": "VISA",
        "mastercard": "MASTERCARD",
        "stripe": "STRIPE",
        "uber": "UBER",
        "pathao": "PATHAO",
        "foodpanda": "FOODPANDA",
        "hungrynaki": "HUNGRYNAKI",
        "daraz": "DARAZ",
        "aliexpress": "ALIEXPRESS",
        "ebay": "EBAY",
        "shopify": "SHOPIFY",
        "airbnb": "AIRBNB",
        "booking.com": "BOOKING",
        "booking": "BOOKING",
        "agoda": "AGODA",
        "expedia": "EXPEDIA",
        "tinder": "TINDER",
        "badoo": "BADOO",
        "bumble": "BUMBLE",
        "happn": "HAPPN",
        "duolingo": "DUOLINGO",
        "canva": "CANVA",
        "adobe": "ADOBE",
        "wordpress": "WORDPRESS",
        "wix": "WIX",
        "godaddy": "GODADDY",
        "namecheap": "NAMECHEAP",
        "cloudflare": "CLOUDFLARE",
        "digitalocean": "DIGITALOCEAN",
        "heroku": "HEROKU",
        "firebase": "FIREBASE",
        "aws": "AWS",
        "azure": "AZURE",
    }
    
    for keyword, service_name in sorted(service_keywords.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in sms_lower:
            return service_name
    
    return "SMS SERVICE"

# ==================== KEYBOARDS SECTION ====================

def main_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📞 GET NUMBER", style="success"), KeyboardButton("📞 GET 10 NUMBER", style="success")],
        [KeyboardButton("🔍 SEARCH OTP", style="primary"), KeyboardButton("💰 BALANCE", style="primary")],
        [KeyboardButton("👥 REFER AND EARN", style="primary"), KeyboardButton("👤 PROFILE", style="primary")],
        [KeyboardButton("📶 VIEW RANGE", style="success"), KeyboardButton("⚡ GET 2FA", style="success")],
        [KeyboardButton("💬 SUPPORT", style="primary")]
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("⚙️ ADMIN PANEL ⚙️", style="success")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    keyboard = [[KeyboardButton("❌ CANCEL", style="danger")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== ADMIN PANEL KEYBOARDS ====================

def admin_main_keyboard():
    keyboard = [
        [KeyboardButton("👥 USER MANAGEMENT", style="success")],
        [KeyboardButton("⚙️ SYSTEM CONFIGURATION", style="success")],
        [KeyboardButton("🔙 BACK TO MAIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def user_management_keyboard():
    keyboard = [
        [KeyboardButton("📢 SEND MESSAGE TO ALL USERS", style="success")],
        [KeyboardButton("🆔 ALL USER ID", style="primary")],
        [KeyboardButton("📜 BAN USER LIST", style="primary")],
        [KeyboardButton("💰 ALL USER BALANCE", style="primary")],
        [KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def system_config_keyboard():
    keyboard = [
        [KeyboardButton("📈 TODAY ALL STATUS", style="success"), KeyboardButton("👤 USER STATUS CHECK", style="success")],
        [KeyboardButton("⛔ BAN USER", style="danger"), KeyboardButton("🔓 UNBAN USER", style="primary")],
        [KeyboardButton("📜 BAN USER LIST", style="primary")],
        [KeyboardButton("➖ REMOVE BALANCE", style="danger"), KeyboardButton("➕ ADD BALANCE", style="success")],
        [KeyboardButton("🔙 BACK TO ADMIN", style="danger")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def withdraw_method_keyboard():
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📱 BKASH", style="success"), KeyboardButton("💵 NAGAD", style="success")],
        [KeyboardButton("🚀 ROCKET", style="primary"), KeyboardButton("🏦 BINANCE", style="primary")],
        [KeyboardButton("❌ CANCEL", style="danger")]
    ], resize_keyboard=True)
    return keyboard

def force_join_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 MAIN CHANNEL", url=FORCE_JOIN_CHANNELS["MAIN_CHANNEL"], style="primary")],
        [InlineKeyboardButton("📢 BACKUP CHANNEL", url=FORCE_JOIN_CHANNELS["BACKUP_CHANNEL"], style="primary")],
        [InlineKeyboardButton("👥 OTP GROUP", url=FORCE_JOIN_CHANNELS["OTP_GROUP"], style="primary")],
        [InlineKeyboardButton("✅ I AM JOIN", callback_data="force_join_confirm", style="success")]
    ])
    return keyboard

# ==================== HELPER FUNCTIONS SECTION ====================

def format_balance(balance):
    return f"{balance:.2f}"

def extract_otp(text):
    if not text or text == "No Content": return "N/A"
    spaced_otp = re.search(r'\b(\d{3}\s\d{3})\b', text)
    if spaced_otp: return spaced_otp.group(1).replace(" ", "")
    match = re.search(r'\b(\d{4,8})\b', text)
    return match.group(1) if match else "N/A"

def normalize_number(num):
    return re.sub(r'\D', '', str(num))

def mask_number(num):
    if len(num) > 6:
        return f"{num[:4]}****{num[-6:]}"
    return num

def get_date_reset_time():
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day, 0, 0, 0)
    return today_midnight

def is_valid_bangladesh_number(number):
    number = re.sub(r'\D', '', str(number))
    return len(number) == 11 and number.startswith('01')

def is_range_request(param):
    if 'X' in param.upper():
        return True
    return False

def is_referral_request(param):
    if param.isdigit():
        return True
    return False

def is_user_joined_channels(user_id):
    return user_id in user_joined_status

# ==================== DATABASE FUNCTIONS SECTION ====================

def load_data(filename=USER_DATA_FILE):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data, filename=USER_DATA_FILE):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def get_user(uid):
    uid = str(uid)
    data = load_data()
    if uid not in data:
        data[uid] = {"user_id": uid, "balance": 0.0, "total_numbers": 0, "referral_count": 0}
        save_data(data)
    return data[uid]

async def update_db_balance(uid, amount):
    uid = str(uid)
    data = load_data()
    if uid in data:
        data[uid]["balance"] = round(data[uid].get("balance", 0.0) + amount, 2)
        save_data(data)
        return data[uid]["balance"]
    return 0.0

def get_all_users():
    data = load_data(USER_DATA_FILE)
    return list(data.keys()) if data else []

def user_exists(uid):
    data = load_data(USER_DATA_FILE)
    return str(uid) in data

# ==================== STATS FUNCTIONS SECTION ====================

def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def add_number_taken(uid, count=1):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    for _ in range(count):
        stats[uid]["numbers_taken"].append(now)
    log_global_activity(uid, "NUMBER_TAKEN", {"count": count})
    save_stats(stats)

def add_otp_received(uid):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    stats[uid]["otps_received"].append(now)
    save_stats(stats)

def get_user_stats(uid):
    uid = str(uid)
    stats = load_stats()
    user_stats = stats.get(uid, {"numbers_taken": [], "otps_received": []})
    
    now = datetime.now()
    today_midnight = get_date_reset_time()
    
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    numbers_taken = user_stats.get("numbers_taken", [])
    otps_received = user_stats.get("otps_received", [])
    
    today_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) >= today_midnight)
    today_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) >= today_midnight)
    
    last24h_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) > last_24h)
    last24h_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_24h)
    
    last7d_numbers = sum(1 for t in numbers_taken if datetime.fromisoformat(t) > last_7d)
    last7d_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_7d)
    
    total_numbers = len(numbers_taken)
    total_otps = len(otps_received)
    
    return {
        "total_numbers": total_numbers,
        "total_otps": total_otps,
        "today_numbers": today_numbers,
        "today_otps": today_otps,
        "last24h_numbers": last24h_numbers,
        "last24h_otps": last24h_otps,
        "last7d_numbers": last7d_numbers,
        "last7d_otps": last7d_otps
    }

def log_global_activity(uid, action, details):
    if not os.path.exists(ACTIVITY_LOGS_FILE):
        with open(ACTIVITY_LOGS_FILE, "w") as f:
            json.dump([], f)
    try:
        with open(ACTIVITY_LOGS_FILE, "r") as f:
            logs = json.load(f)
    except:
        logs = []
    now = datetime.now()
    log_entry = {
        "uid": str(uid),
        "action": action,
        "details": details,
        "timestamp": now.isoformat(),
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S")
    }
    logs.append(log_entry)
    with open(ACTIVITY_LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def get_global_system_stats():
    stats = load_stats()
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day)
    last_7d = now - timedelta(days=7)
    total_n, total_o = 0, 0
    today_n, today_o = 0, 0
    seven_n, seven_o = 0, 0
    for uid in stats:
        u_stats = stats[uid]
        n_list = u_stats.get("numbers_taken", [])
        o_list = u_stats.get("otps_received", [])
        total_n += len(n_list)
        total_o += len(o_list)
        for t in n_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight: today_n += 1
            if dt >= last_7d: seven_n += 1
        for t in o_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight: today_o += 1
            if dt >= last_7d: seven_o += 1
    return today_n, today_o, seven_n, seven_o, total_n, total_o

# ==================== 2FA CODE GENERATOR SECTION ====================

def generate_2fa_code(secret_key):
    try:
        clean_secret = secret_key.replace(" ", "").strip()
        totp = pyotp.TOTP(clean_secret)
        otp = totp.now()
        return otp, clean_secret
    except:
        return None, None

async def get_2fa_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return
    
    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return
    
    context.user_data["mode"] = "get_2fa"
    await update.message.reply_text(
        "⚡ <b>GET 2FA CODE</b> ⚡\n\n"
        "<blockquote>🔑 ENTER YOUR 2FA SECRET KEY:</blockquote>",
        parse_mode="HTML"
    )

async def process_2fa_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    secret_key = update.message.text.strip()
    context.user_data["mode"] = None
    
    otp_code, clean_key = generate_2fa_code(secret_key)
    
    if otp_code is None:
        await update.message.reply_text(
            "❌ **INVALID 2FA SECRET KEY** ❌\n\n"
            "⚠️ PLEASE SEND A VALID 2FA SECRET KEY!",
            parse_mode="Markdown",
            reply_markup=main_keyboard(uid)
        )
        return
    
    now = datetime.now()
    date_str = now.strftime("%d %B, %Y")
    time_str = now.strftime("%I:%M %p")
    
    final_msg = (
        "✅ <b>2FA CODE GENERATED !</b>\n\n"
        f"<blockquote>🔑 KEY: <code>{clean_key}</code></blockquote>\n"
        f"<blockquote>🔢 CODE: <code>{otp_code}</code></blockquote>\n"
        f"<blockquote>⏳ EXPIRES IN: 30 SECONDS</blockquote>\n"
        f"📅 DATE: {date_str} | TIME: {time_str}"
    )
    
    await update.message.reply_text(
        final_msg,
        parse_mode="HTML"
    )

# ==================== AUTO OTP MONITOR SECTION ====================

async def monitor_loop(app):
    """AUTO OTP RECEIVE SYSTEM - API MONITOR LOOP"""
    while True:
        try:
            # আপনার নতুন প্যানেলের ওটিপি এপিআই কল করা হচ্ছে
            r = await client_async.get(f"{BASE_URL}/api/otps")
            res = r.json()
            if "data" in res and "otps" in res["data"]:
                otps = res["data"]["otps"]
                paid_data = load_data(PAID_SMS_FILE)
                
                # রেঞ্জ ডাটাবেস লোড করা হচ্ছে
                range_db = load_data(DATA_RANGE_FILE)
                
                # 🆕 FIX: DUPLICATE OTP - ফাস্ট চেক করার জন্য সেট তৈরি
                paid_keys_set = set(paid_data.keys())
                
                # 🆕 NEW FIX: প্রসেস করা OTP গুলো এই সেশনে ট্র্যাক করতে সেট
                processed_in_session = set()

                for otp in otps:
                    num = normalize_number(otp.get("number", ""))
                    full_sms = otp.get('message') or otp.get('otp') or otp.get('sms') or "No SMS Content"
                    otp_code = extract_otp(full_sms)
                    otp_id = str(otp.get("otp_id", ""))
                    
                    # ইউনিক ওটিপি আইডি দিয়ে ডুপ্লিকেশন ব্লক করা হলো
                    sms_key = otp_id if otp_id else f"{num}_{full_sms}"

                    # 🆕 FIX: ডুপ্লিকেট চেক - paid_data, paid_keys_set এবং session সেট দিয়ে
                    if (num in active_numbers and 
                        sms_key not in paid_keys_set and 
                        sms_key not in processed_in_session):
                        
                        details = active_numbers[num]
                        
                        # 🆕 সাথে সাথে ব্লক করে দিন - paid_data, set এবং session সব জায়গায়
                        paid_keys_set.add(sms_key)
                        processed_in_session.add(sms_key)
                        paid_data[sms_key] = {"uid": details["uid"], "otp": otp_code}
                        
                        await update_db_balance(details["uid"], OTP_RATE)
                        add_otp_received(details["uid"])
                        log_global_activity(details["uid"], "OTP_RECEIVED", {"number": num, "otp": otp_code, "sms": full_sms})

                        # ডাটাবেস থেকে এই নাম্বারের রেঞ্জ খুঁজে বের করা
                        num_range_info = range_db.get(num, {}).get("range", "UNKNOWN")

                        # DYNAMIC COUNTRY & SERVICE DETECTION
                        country_flag, country_name = get_country_info(num)
                        service_name = detect_service(full_sms)
                        
                        # FIX: DOUBLE PLUS - নাম্বার থেকে + রিমুভ করে একটা যোগ
                        clean_num = num.replace('+', '').strip()
                        full_number = f"+{clean_num}"
                        masked_number = f"+{mask_number(clean_num)}"
                        
                        # HTML এররের হাত থেকে বাঁচতে টেক্সটগুলোকে ফিল্টার করা হলো
                        safe_full_sms = html.escape(str(full_sms))
                        safe_otp_code = html.escape(str(otp_code))
                        
                        # ⭐ USER MESSAGE - PRIVATE CHAT এ পাঠানোর জন্য (FULL NUMBER)
                        user_msg = (
                            f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                            f"<blockquote>📶 RANGE: <code>{num_range_info}</code></blockquote>\n"
                            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                            f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                            f"<blockquote>📞 NUMBER: <code>{full_number}</code></blockquote>\n"
                            f"<blockquote>🔑 OTP: <code>{safe_otp_code}</code></blockquote>\n\n"
                            f"<blockquote>📩 FULL SMS:\n"
                            f"<code>{safe_full_sms}</code></blockquote>\n\n"
                            f"<b>💵 ADD BALANCE FOR {OTP_RATE:.2f} BDT</b>"
                        )
                        
                        # ⭐ GROUP MESSAGE - গ্রুপে পাঠানোর জন্য (MASKED NUMBER)
                        group_msg = (
                            f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                            f"<blockquote>📶 RANGE: <code>{num_range_info}</code></blockquote>\n"
                            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                            f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                            f"<blockquote>📞 NUMBER: <code>{masked_number}</code></blockquote>\n"
                            f"<blockquote>🔑 OTP: <code>{safe_otp_code}</code></blockquote>\n\n"
                            f"<blockquote>📩 FULL SMS:\n"
                            f"<code>{safe_full_sms}</code></blockquote>"
                        )
                        
                        # 🆕 GROUP BUTTONS - পাশাপাশি ২টি বাটন এবং কালার সেট করা হয়েছে
                        group_buttons = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("‼️ PANEL", url="https://t.me/maamrjan_bot?start=6952815629", style="danger"),
                                InlineKeyboardButton("📢 CHANNEL", url="https://t.me/kalamking32900", style="primary")
                            ]
                        ])
                        
                        # ⭐ STEP 1: ইউজারকে প্রাইভেট মেসেজ পাঠান
                        try:
                            await app.bot.send_message(details["uid"], user_msg, parse_mode="HTML")
                        except Exception as e:
                            print(f"❌ User Message Send Fail: {e}")
                        
                        # ⭐ STEP 2: গ্রুপে মেসেজ পাঠান
                        try:
                            await app.bot.send_message(OTP_GROUP_ID, group_msg, parse_mode="HTML", reply_markup=group_buttons)
                        except Exception as e:
                            print(f"❌ Group Send Fail: {e}")
                        
                        # 🆕 FIX: প্রতিটা OTP প্রসেস করার পর সাথে সাথে ফাইল সেভ
                        save_data(paid_data, PAID_SMS_FILE)

                # 🆕 পুরোনো active_numbers ক্লিনআপ (1 ঘন্টার পুরোনো এন্ট্রি রিমুভ)
                current_time = datetime.now()
                expired_nums = []
                for num_key in list(active_numbers.keys()):
                    if hasattr(active_numbers[num_key], 'timestamp'):
                        if (current_time - active_numbers[num_key]['timestamp']).seconds > 3600:
                            expired_nums.append(num_key)
                    else:
                        active_numbers[num_key]['timestamp'] = current_time
                
                for num in expired_nums:
                    del active_numbers[num]
                    
        except Exception as e:
            print(f"Monitor Error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ==================== WORKER & API SECTION ====================

async def fetch_number_async(range_str):
    try:
        # আপনার নতুন প্যানেলের গেট নম্বর এপিআই কল হচ্ছে
        r = await client_async.post(
            f"{BASE_URL}/api/getnum",
            json={"range": range_str, "is_national": True}
        )
        data = r.json()
        if "data" in data and "full_number" in data["data"]:
            return data["data"]["full_number"]
    except Exception as e: 
        print(f"Fetch number error: {e}")
    return None

async def worker():
    while True:
        task = await request_queue.get()
        try:
            if task['type'] == 'process_numbers':
                await process_numbers(task['update'], task['context'], task['range_text'], task['count'])
            elif task['type'] == 'search_otp':
                await perform_otp_search(task['update'], task['context'], task['target_num'])
            elif task['type'] == 'auto_number':
                await process_auto_number(task['update'], task['context'], task['range_text'])
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            request_queue.task_done()

# ==================== AUTO NUMBER FROM LINK SECTION ====================

async def process_auto_number(update, context, range_text):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_user_banned(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await context.bot.send_message(chat_id=chat_id, text=force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING...")

    try:
        result = await fetch_number_async(range_text)
        generated_num = normalize_number(result) if result else None
        
        if not generated_num:
            await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
            return
        
        add_number_taken(uid, 1)
        last_range[uid] = range_text
        active_numbers[generated_num] = {"uid": uid, "range": range_text}
        save_number_range_info(uid, generated_num, range_text)
        
        country_flag, country_name = get_country_info(generated_num)
        
        final_text = (
            f"✅ <b>YOUR NUMBER DETAILS</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n\n"
            f"<blockquote>📞 NUMBER: <code>+{generated_num}</code></blockquote>\n\n"
            f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 SAME RANGE", callback_data="same_range", style="success")],
            [InlineKeyboardButton("📢 OTP GROUP", url=FORCE_JOIN_CHANNELS["OTP_GROUP"], style="primary")]
        ]
        
        await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        print(f"Auto Number Error: {e}")
        await status_msg.edit_text(f"❌ Error occurred: {str(e)}")

# ==================== USER PANEL SECTION ====================

async def process_numbers(update_or_query, context, range_text, count):
    if isinstance(update_or_query, Update) and update_or_query.callback_query:
        uid = update_or_query.callback_query.from_user.id
        chat_id = update_or_query.callback_query.message.chat_id
    else:
        uid = update_or_query.effective_user.id
        chat_id = update_or_query.effective_chat.id

    if is_user_banned(uid):
        await context.bot.send_message(chat_id=chat_id, text="🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**"
        await context.bot.send_message(chat_id=chat_id, text=force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return

    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING . . .")  

    try:
        add_number_taken(uid, count)
        last_range[uid] = range_text   

        tasks = [fetch_number_async(range_text) for _ in range(count)]  
        results = await asyncio.gather(*tasks)  
        generated_nums = [normalize_number(n) for n in results if n]  

        if not generated_nums:  
            await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")  
            return  

        for clean_num in generated_nums:  
            active_numbers[clean_num] = {"uid": uid, "range": range_text}
            save_number_range_info(uid, clean_num, range_text)

        country_flag, country_name = get_country_info(generated_nums[0])
        
        num_list_text = "\n".join([f"<blockquote>📞 NUMBER: <code>+{n}</code></blockquote>" for n in generated_nums])
        
        final_text = (  
            f"✅ <b>YOUR NUMBER DETAILS</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n\n"
            f"{num_list_text}\n\n"
            f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
        )  

        keyboard = []
        if count == 1:
            keyboard.append([InlineKeyboardButton("🔄 SAME RANGE", callback_data="same_range", style="success")])
        keyboard.append([InlineKeyboardButton("📢 OTP GROUP", url=FORCE_JOIN_CHANNELS["OTP_GROUP"], style="primary")])

        await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        if count == 10:
            file_content = "\n".join([f"+{n}" for n in generated_nums])  
            file = io.BytesIO(file_content.encode())
            
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            file.name = f"NUM_{random_suffix}.txt"  
            
            await context.bot.send_document(chat_id=chat_id, document=file, caption="✅ Your Numbers File (Auto Generated)")
            
    except Exception as e:
        print(f"Process Number Error: {e}")
        await status_msg.edit_text(f"❌ System Error: {str(e)}")

async def perform_otp_search(update, context, target_num):
    uid = str(update.effective_user.id)

    if is_user_banned(int(uid)):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(int(uid)))
        return

    if not is_admin(int(uid)) and not is_user_joined_channels(int(uid)):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return

    status_msg = await update.message.reply_text("🔍 SEARCHING IN SERVER... ")  

    try:  
        r = await client_async.get(f"{BASE_URL}/api/otps")  
        res = r.json()  
        
        if "data" in res and "otps" in res["data"]:  
            all_otps = res["data"]["otps"]  
            found_otps = [o for o in all_otps if normalize_number(o.get("number", "")) == target_num]  

            if not found_otps:
                error_msg = ("━━━━━━━━━━━━━━━━━━\n❌ NO OTP FOUND\n━━━━━━━━━━━━━━━━━━\n\n"
                             f"📞 NUMBER:\n`+{target_num}`\n\n⏳ PLEASE TRY AGAIN LATER\n━━━━━━━━━━━━━━━━━━")
                await status_msg.edit_text(error_msg, parse_mode="Markdown")
                await update.message.reply_text("🔙 RETURNING TO MAIN MENU...", reply_markup=main_keyboard(int(uid)))
            else:  
                await status_msg.delete()  
                paid_data = load_data(PAID_SMS_FILE)

                for o in found_otps:  
                    full_sms = o.get('message') or o.get('otp') or o.get('sms') or "No Content Found"  
                    otp_code = extract_otp(full_sms)  
                    otp_id = str(o.get("otp_id", ""))
                    sms_key = otp_id if otp_id else f"{target_num}_{full_sms}"

                    if sms_key in paid_data:
                        payment_status = "❌ NOT BALANCE ADD ALREADY PAID"
                    else:
                        await update_db_balance(uid, OTP_RATE)
                        add_otp_received(uid)
                        paid_data[sms_key] = {"uid": uid, "otp": otp_code}
                        payment_status = f"💵 ADD BALANCE FOR {OTP_RATE:.2f} BDT"
                    
                    country_flag, country_name = get_country_info(target_num)
                    service_name = detect_service(full_sms)

                    safe_full_sms = html.escape(str(full_sms))
                    safe_otp_code = html.escape(str(otp_code))

                    msg = (
                        f"✅ <b>SEARCH OTP COMPLETED</b> ✅\n\n"
                        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                        f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                        f"<blockquote>📞 NUMBER: <code>+{target_num}</code></blockquote>\n"
                        f"<blockquote>🔑 OTP: <code>{safe_otp_code}</code></blockquote>\n\n"
                        f"<blockquote>📩 FULL SMS:\n"
                        f"<code>{safe_full_sms}</code></blockquote>\n\n"
                        f"<b>{payment_status}</b>"
                    )
                    
                    await update.message.reply_text(msg, parse_mode="HTML")
                
                save_data(paid_data, PAID_SMS_FILE)
                await update.message.reply_text("✅ ALL FOUND MESSAGES DISPLAYED ABOVE.", reply_markup=main_keyboard(int(uid)))
        else:
            await status_msg.edit_text("❌ SERVER RETURNED AN ERROR.")
            await update.message.reply_text("🔙 Returning to Main Menu...", reply_markup=main_keyboard(int(uid)))
            
    except Exception as e: 
        try:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
        except:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            
        await update.message.reply_text("🔙 Returning to Main Menu...", reply_markup=main_keyboard(int(uid)))

# ==================== REFER AND EARN SECTION ====================

async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return
    
    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return
    
    user_data = get_user(uid)
    bot_info = await context.bot.get_me()
    
    referral_link = f"https://t.me/{bot_info.username}?start={uid}"
    successful_refers = get_referral_count(uid)
    total_reward = float(successful_refers) * REFERRAL_PRICE
    
    refer_msg = (
        f"🎁 <b>REFER AND EARN SYSTEM</b> 🎁\n\n"
        f"<blockquote>🚀 INVITE FRIENDS & EARN {int(REFERRAL_PRICE)} BDT EACH! 💸</blockquote>\n\n"
        f"<b>🔗 YOUR REFERRAL LINK:</b>\n"
        f"<blockquote><code>{referral_link}</code></blockquote>\n\n"
        f"<b>📊 YOUR STATS:</b>\n"
        f"<blockquote>👥 TOTAL REFERS: {successful_refers}\n"
        f"💰 TOTAL EARNED: {format_balance(total_reward)} BDT</blockquote>\n\n"
        f"✨ <b>SHARE LINK & EARN MONEY!</b> ✨"
    )
    
    refer_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 YOUR REFERRAL", callback_data=f"my_ref_{uid}", style="primary")]
    ])
    
    await update.message.reply_text(
        refer_msg, 
        parse_mode="HTML", 
        disable_web_page_preview=True, 
        reply_markup=refer_keyboard
    )

# ==================== VIEW RANGE SECTION ====================

async def view_range_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return
    
    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return
    
    msg = "🔥 CLICK THE 📶 VIEW RANGE BUTTON BELOW TO CHECK THE ACTIVE RANGE !"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📶 VIEW RANGE", url="https://t.me/rangbot32900", style="primary")
    ]])
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")

# ==================== JOIN METHOD GROUP SECTION ====================

async def join_method_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return
    
    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return
    
    msg = "🔗 JOIN METHOD GROUP FOR ALL UPDATE METHODS 🔗"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("👥 JOIN METHOD GROUP", url="https://t.me/kalamking32900", style="primary")
    ]])
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")

# ==================== WITHDRAW FUNCTIONS ====================

async def withdraw_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠", reply_markup=main_keyboard(uid))
        return
    
    method_map = {
        "📱 BKASH": "BKASH",
        "💵 NAGAD": "NAGAD", 
        "🚀 ROCKET": "ROCKET",
        "🏦 BINANCE": "BINANCE"
    }
    
    if text in method_map:
        balance = get_user(uid)['balance']
        context.user_data["withdraw_method"] = method_map[text]
        context.user_data["withdraw_mode"] = "amount"
        msg = (
            f"<blockquote>💸 SEND YOUR AMOUNT !\n"
            f"💵 TOTAL BALANCE: {format_balance(balance)} BDT</blockquote>\n\n"
            f"<blockquote>📉 MINIMUM WITHDRAW 50 BDT</blockquote>"
        )
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())
    else:
        await update.message.reply_text("⚠️ PLEASE SELECT A VALID PAYMENT METHOD!", reply_markup=withdraw_method_keyboard())

async def withdraw_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠", reply_markup=main_keyboard(uid))
        return
    
    try:
        amount = float(text)
    except:
        await update.message.reply_text("⚠️ PLEASE SEND A VALID AMOUNT!", reply_markup=cancel_keyboard())
        return
    
    balance = get_user(uid)['balance']
    
    if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
        await update.message.reply_text(f"📉 MINIMUM WITHDRAW {MIN_WITHDRAW} BDT\n\n📈 MAX WITHDRAWAL {MAX_WITHDRAW} BDT", reply_markup=cancel_keyboard())
        return
    
    if amount > balance:
        await update.message.reply_text("🚫 YOU DO NOT HAVE ENOUGH BALANCE !", reply_markup=cancel_keyboard())
        return
    
    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_mode"] = "number"
    msg = (
        f"📞 PLEASE SEND YOUR PAYMENT NUMBER !\n\n"
        f"<blockquote>🔢 EXAMPLE: 017XXXXXXXX</blockquote>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())

async def withdraw_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        context.user_data["withdraw_amount"] = None
        await update.message.reply_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠", reply_markup=main_keyboard(uid))
        return
    
    if not is_valid_bangladesh_number(text):
        await update.message.reply_text("⚠️ PLEASE SEND VALID NUMBER !\n\n🔢 EXAMPLE: 017XXXXXXXX", reply_markup=cancel_keyboard())
        return
    
    method = context.user_data.get("withdraw_method")
    amount = context.user_data.get("withdraw_amount")
    payment_number = text
    payment_id = generate_payment_id()
    
    user_payment_msg = (
        "✨ <b>YOUR PAYMENT DETAILS!</b> ✨\n\n"
        f"<blockquote>📝 PAYMENT METHOD: {method}\n"
        f"📞 YOUR PAYMENT NUMBER: {payment_number}\n\n"
        f"✅ IF PAYMENT DETAILS ARE CORRECT, CLICK THE CONFIRM BUTTON\n"
        f"❌ OR IF PAYMENT DETAILS ARE WRONG, CLICK THE CANCEL BUTTON</blockquote>"
    )
    
    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ CANCEL", callback_data="withdraw_cancel", style="danger"),
            InlineKeyboardButton("✅ CONFIRM", callback_data="withdraw_confirm", style="success")
        ]
    ])
    
    context.user_data["temp_withdraw"] = {
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id
    }
    
    await update.message.reply_text(
        user_payment_msg,
        parse_mode="HTML",
        reply_markup=confirm_keyboard
    )

async def process_withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    temp_data = context.user_data.get("temp_withdraw")
    if not temp_data:
        await query.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.", reply_markup=main_keyboard(uid))
        return
    
    method = temp_data["method"]
    amount = temp_data["amount"]
    payment_number = temp_data["number"]
    payment_id = temp_data["payment_id"]
    
    new_balance = await update_db_balance(uid, -amount)
    
    withdraw_requests = load_withdraw_requests()
    withdraw_requests[str(payment_id)] = {
        "user_id": uid,
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    save_withdraw_requests(withdraw_requests)
    
    user_confirm_msg = (
        f"✅ <b>WITHDRAWAL REQUEST SUBMITTED</b> ✅\n\n"
        f"<blockquote>💰 আপনার উইথড্র রিকোয়েস্টটি এডমিনের কাছে পাঠানো হয়েছে।\n"
        f"⏳ অনুগ্রহ করে এডমিন এপ্রুভ করা পর্যন্ত অপেক্ষা করুন।</blockquote>\n\n"
        f"<blockquote>✨ WITHDRAW DETAILS:\n"
        f"📝 METHOD: <code>{method}</code>\n"
        f"📞 NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)} BDT</code>\n"
        f"🆔 PAYMENT ID: <code>{payment_id}</code></blockquote>"
    )
    await query.message.edit_text(user_confirm_msg, parse_mode="HTML")

    success_back_msg = (
        "🎉 <b>WITHDRAW REQUEST SUBMIT SUCCESSFUL</b> 🎉\n\n"
        "🏠 <b>BACK TO MENU</b> 🏠"
    )
    await context.bot.send_message(
        chat_id=uid,
        text=success_back_msg,
        parse_mode="HTML",
        reply_markup=main_keyboard(uid)
    )

    admin_msg = (
        f"✅ <b>NEW WITHDRAWAL REQUEST RECEIVED</b> ✅\n\n"
        f"<blockquote>🆔 USER ID : <code>{uid}</code>\n"
        f"✨ YOUR PAYMENT DETAILS!\n"
        f"📝 PAYMENT METHOD: <code>{method}</code>\n"
        f"📞 YOUR PAYMENT NUMBER: <code>{payment_number}</code>\n"
        f"🆔 PAYMENT ID : <code>{payment_id}</code></blockquote>\n\n"
        f"<blockquote>💰 AMOUNT: <code>{format_balance(amount)} BDT</code></blockquote>"
    )
    
    admin_decision_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ CANCEL", callback_data=f"admin_reject_{payment_id}", style="danger"),
            InlineKeyboardButton("✅ CONFIRM", callback_data=f"admin_approve_{payment_id}", style="success")
        ]
    ])
    
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                admin_id, 
                admin_msg, 
                parse_mode="HTML", 
                reply_markup=admin_decision_keyboard
            )
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")
    
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    context.user_data["withdraw_method"] = None
    context.user_data["withdraw_amount"] = None

async def process_withdraw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    context.user_data["withdraw_method"] = None
    context.user_data["withdraw_amount"] = None
    
    await query.message.edit_text("❌ WITHDRAW CANCELLED ❌\n\n🏠 BACK TO MENU 🏠")
    await context.bot.send_message(uid, "🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

# ==================== ADMIN PANEL - WITHDRAW APPROVAL ====================

async def admin_approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    query = update.callback_query
    await query.answer()
    
    withdraw_requests = load_withdraw_requests()
    if payment_id not in withdraw_requests:
        await query.message.reply_text("⚠️ WITHDRAW REQUEST NOT FOUND!")
        return
    
    request_data = withdraw_requests[payment_id]
    uid = request_data["user_id"]
    method = request_data["method"]
    amount = request_data["amount"]
    payment_number = request_data["number"]
    
    withdraw_requests[payment_id]["status"] = "approved"
    save_withdraw_requests(withdraw_requests)
    
    user_final_msg = (
        "🎉 <b>WITHDRAWAL SUCCESSFUL</b> 🎉\n\n"
        "<blockquote>💰 আপনার উইথড্র রিকোয়েস্টটি এডমিন এপ্রুভ করেছে এবং পেমেন্ট সফলভাবে পাঠানো হয়েছে !</blockquote>\n\n"
        "<blockquote>📱 WHAT TO DO NEXT:\n"
        "📥 আপনি যেই মেথড এবং নাম্বারে উইথড্র দিয়েছিলেন, অনুগ্রহ করে সেই নাম্বারটি চেক করুন।\n"
        "⏳ আশা করা যায় আপনার অ্যাকাউন্টে টাকা চলে গিয়েছে।\n"
        "⚠️ NOTE: যদি কোনো কারণে এখনো পেমেন্ট না পেয়ে থাকেন, তাহলে দ্রুত আমাদের Support Team-এর সাথে যোগাযোগ করুন।</blockquote>\n\n"
        "<blockquote>✨ ধন্যবাদ আমাদের সাথে থাকার জন্য! ✨\n"
        "🚀 Quick Number | SECURE & TRUSTED ⚡</blockquote>\n\n"
        f"<blockquote>✨ YOUR PAYMENT DETAILS:\n"
        f"📝 PAYMENT METHOD: <code>{method}</code>\n"
        f"📞 PAYMENT NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)} BDT</code>\n"
        f"🆔 PAYMENT ID: <code>{payment_id}</code></blockquote>"
    )
    
    try:
        await context.bot.send_message(uid, user_final_msg, parse_mode="HTML")
    except:
        pass
    
    await query.message.edit_text(
        f"✅ **WITHDRAW REQUEST CONFIRMED SUCCESSFULLY** ✅\n\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"👤 User ID: `{uid}`\n"
        f"💰 Amount: `{format_balance(amount)} BDT`\n\n"
        f"🎉 Payment has been approved and user has been notified!",
        parse_mode="Markdown"
    )

async def admin_reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    query = update.callback_query
    await query.answer()
    
    withdraw_requests = load_withdraw_requests()
    if payment_id not in withdraw_requests:
        await query.message.reply_text("⚠️ WITHDRAW REQUEST NOT FOUND!")
        return
    
    request_data = withdraw_requests[payment_id]
    uid = request_data["user_id"]
    method = request_data["method"]
    amount = request_data["amount"]
    payment_number = request_data["number"]
    
    withdraw_requests[payment_id]["status"] = "rejected"
    save_withdraw_requests(withdraw_requests)
    
    user_reject_msg = (
        "❌ **WITHDRAWAL REQUEST REJECTED** ❌\n\n"
        "⚠️ SORRY, THE ADMIN HAS NOT APPROVED AND PAID YOUR WITHDRAWAL REQUEST.\n\n"
        "🚫 **REASON:** > YOU MAY HAVE VIOLATED OUR TERMS OF SERVICE BY ENGAGING IN UNETHICAL, SUSPICIOUS, OR FRAUDULENT ACTIVITIES THAT GO AGAINST OUR RULES AND POLICY.\n\n"
        "🛑 **CONSEQUENCES:**\n"
        "* 🔴 YOUR PAYMENT HAS BEEN CANCELLED.\n"
        "* 🔴 THE AMOUNT HAS BEEN DEDUCTED FROM YOUR BALANCE.\n"
        "* 🔴 NO PAYMENT WILL BE ISSUED TO THIS ACCOUNT.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ **Quick Number | SECURE SYSTEM** ⚡\n\n"
        "✨ **WITHDRAW DETAILS:**\n"
        f"📝 METHOD: `{method}`\n"
        f"📞 NUMBER: `{payment_number}`\n"
        f"💰 AMOUNT: `{format_balance(amount)} BDT`\n"
        f"🆔 ID: `{payment_id}`"
    )
    
    try:
        await context.bot.send_message(uid, user_reject_msg, parse_mode="Markdown")
    except:
        pass
    
    await query.message.edit_text(
        f"❌ **WITHDRAW REQUEST CANCELLED SUCCESSFULLY** ❌\n\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"👤 User ID: `{uid}`\n"
        f"💰 Amount: `{format_balance(amount)} BDT`\n\n"
        f"🔴 This payment has been rejected and user has been notified!",
        parse_mode="Markdown"
    )

# ==================== ADMIN PANEL - BALANCE MANAGEMENT ====================

async def admin_add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_balance_mode"] = True
    context.user_data["remove_balance_mode"] = False
    await update.message.reply_text("💰 **SEND USER ID TO ADD BALANCE FOR USER!** 💰\n\n📝 PLEASE SEND THE TELEGRAM USER ID:", parse_mode="Markdown")

async def admin_remove_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["remove_balance_mode"] = True
    context.user_data["add_balance_mode"] = False
    await update.message.reply_text("💸 **SEND USER ID TO REMOVE BALANCE FROM USER!** 💸\n\n📝 PLEASE SEND THE TELEGRAM USER ID:", parse_mode="Markdown")

async def process_add_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_add = update.message.text.strip()
    
    if not uid_to_add.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! PLEASE SEND A VALID NUMERIC TELEGRAM ID.")
        return
    
    uid_to_add_int = int(uid_to_add)
    
    if not user_exists(uid_to_add_int):
        await update.message.reply_text("❌ USER NOT FOUND! THIS USER HAS NEVER STARTED THE BOT.")
        context.user_data["add_balance_mode"] = False
        return
    
    context.user_data["pending_add_user"] = uid_to_add_int
    await update.message.reply_text("💵 **SEND AMOUNT TO ADD BALANCE:**\n\n💰 ENTER AMOUNT IN BDT:", parse_mode="Markdown")

async def process_remove_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_remove = update.message.text.strip()
    
    if not uid_to_remove.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! PLEASE SEND A VALID NUMERIC TELEGRAM ID.")
        return
    
    uid_to_remove_int = int(uid_to_remove)
    
    if not user_exists(uid_to_remove_int):
        await update.message.reply_text("❌ USER NOT FOUND! THIS USER HAS NEVER STARTED THE BOT.")
        context.user_data["remove_balance_mode"] = False
        return
    
    context.user_data["pending_remove_user"] = uid_to_remove_int
    await update.message.reply_text("💸 **SEND AMOUNT TO REMOVE BALANCE:**\n\n💰 ENTER AMOUNT IN BDT:", parse_mode="Markdown")

async def process_add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A POSITIVE NUMBER.")
            return
    except:
        await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A VALID NUMBER.")
        return
    
    uid = context.user_data.get("pending_add_user")
    if not uid:
        context.user_data["add_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.")
        return
    
    user_data = get_user(uid)
    old_balance = user_data.get("balance", 0)
    new_balance = await update_db_balance(uid, amount)
    
    admin_msg = (
        "✅ **ADD BALANCE SUCCESSFUL** ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 USER ID : `{uid}`\n"
        f"💰 ADD BALANCE AMOUNT : `{format_balance(amount)} BDT`\n"
        f"📊 PREVIOUS BALANCE : `{format_balance(old_balance)} BDT`\n"
        f"📈 NEW BALANCE : `{format_balance(new_balance)} BDT`\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 COPY USER ID", callback_data=f"copy_id_{uid}")]
    ])
    
    await update.message.reply_text(admin_msg, parse_mode="Markdown", reply_markup=admin_keyboard)
    
    user_msg = (
        "🎉 **THE ADMIN HAS ADDED MONEY TO YOUR ACCOUNT** 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **AMOUNT OF MONEY :** `{format_balance(amount)} BDT`\n"
        f"📊 **YOUR NEW BALANCE :** `{format_balance(new_balance)} BDT`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💫 THANK YOU FOR USING OUR SERVICE!"
    )
    
    try:
        await context.bot.send_message(uid, user_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ COULD NOT NOTIFY USER. BUT BALANCE ADDED SUCCESSFULLY.")
    
    context.user_data["add_balance_mode"] = False
    context.user_data["pending_add_user"] = None

async def process_remove_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A POSITIVE NUMBER.")
            return
    except:
        await update.message.reply_text("❌ INVALID AMOUNT! PLEASE SEND A VALID NUMBER.")
        return
    
    uid = context.user_data.get("pending_remove_user")
    if not uid:
        context.user_data["remove_balance_mode"] = False
        await update.message.reply_text("⚠️ SESSION EXPIRED. PLEASE TRY AGAIN.")
        return
    
    user_data = get_user(uid)
    old_balance = user_data.get("balance", 0)
    
    if amount > old_balance:
        error_msg = (
            "❌ **INSUFFICIENT BALANCE!** ❌\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 USER ID : `{uid}`\n"
            f"💰 CURRENT BALANCE : `{format_balance(old_balance)} BDT`\n"
            f"💸 REQUESTED REMOVE : `{format_balance(amount)} BDT`\n\n"
            "⚠️ **PLEASE SEND A VALID REMOVE BALANCE AMOUNT!**\n"
            "⚠️ AMOUNT CANNOT EXCEED CURRENT BALANCE!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(error_msg, parse_mode="Markdown")
        context.user_data["remove_balance_mode"] = False
        context.user_data["pending_remove_user"] = None
        return
    
    new_balance = await update_db_balance(uid, -amount)
    
    admin_msg = (
        "✅ **REMOVE BALANCE SUCCESSFUL** ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 USER ID : `{uid}`\n"
        f"💸 REMOVE BALANCE AMOUNT : `{format_balance(amount)} BDT`\n"
        f"📊 PREVIOUS BALANCE : `{format_balance(old_balance)} BDT`\n"
        f"📉 NEW BALANCE : `{format_balance(new_balance)} BDT`\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 COPY USER ID", callback_data=f"copy_id_{uid}")]
    ])
    
    await update.message.reply_text(admin_msg, parse_mode="Markdown", reply_markup=admin_keyboard)
    
    user_msg = (
        "⚠️ **ADMIN HAS REMOVED MONEY FROM YOUR ACCOUNT** ⚠️\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💸 **AMOUNT REMOVED :** `{format_balance(amount)} BDT`\n"
        f"📊 **YOUR NEW BALANCE :** `{format_balance(new_balance)} BDT`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📞 CONTACT SUPPORT IF YOU HAVE ANY QUESTIONS!"
    )
    
    try:
        await context.bot.send_message(uid, user_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ COULD NOT NOTIFY USER. BUT BALANCE REMOVED SUCCESSFULLY.")
    
    context.user_data["remove_balance_mode"] = False
    context.user_data["pending_remove_user"] = None

# ==================== ADMIN PANEL - BAN/UNBAN ====================

async def admin_ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_ban_mode"] = True
    context.user_data["admin_unban_mode"] = False
    await update.message.reply_text("🚫 SENT TELEGRAM ID TO BAN USER 🚫\n\n📝 Please send the Telegram User ID you want to ban:")

async def admin_unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_unban_mode"] = True
    context.user_data["admin_ban_mode"] = False
    await update.message.reply_text("🔓 SENT UNBAN USER ID 🔓\n\n📝 Please send the Telegram User ID you want to unban:")

async def process_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_ban = update.message.text.strip()
    
    if not uid_to_ban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! Please send a valid numeric Telegram ID.")
        return
    
    uid_to_ban_int = int(uid_to_ban)
    
    if not user_exists(uid_to_ban_int):
        await update.message.reply_text("❌ THIS USER NOT FOUND FOR YOUR TELEGRAM BOT ❌\n\n⚠️ This user has never started the bot or doesn't exist in our database.")
        context.user_data["admin_ban_mode"] = False
        return
    
    if is_user_banned(uid_to_ban_int):
        await update.message.reply_text("⚠️ USER IS ALREADY BANNED ⚠️\n\nThis user has already been banned from the bot.")
        context.user_data["admin_ban_mode"] = False
        return
    
    ban_user(uid_to_ban_int)
    
    try:
        await context.bot.send_message(
            uid_to_ban_int,
            "🚫 **YOU HAVE BEEN BANNED** 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n"
            "📞 CONTACT SUPPORT FOR MORE INFORMATION.\n\n"
            "💬 SUPPORT: @abraher32900",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ USER BAN SUCCESSFUL ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚫 Banned User ID: `{uid_to_ban}`\n"
        f"📊 Status: User can no longer use any bot features.\n\n"
        f"🔓 To unban this user, use the UNBAN USER option.",
        parse_mode="Markdown",
        reply_markup=system_config_keyboard()
    )
    context.user_data["admin_ban_mode"] = False

async def process_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_to_unban = update.message.text.strip()
    
    if not uid_to_unban.isdigit():
        await update.message.reply_text("❌ INVALID USER ID! Please send a valid numeric Telegram ID.")
        return
    
    uid_to_unban_int = int(uid_to_unban)
    
    if not is_user_banned(uid_to_unban_int):
        await update.message.reply_text("⚠️ THIS USER IS NOT BANNED ⚠️\n\n📝 Please send a banned user ID to unban.")
        context.user_data["admin_unban_mode"] = False
        return
    
    unban_user(uid_to_unban_int)
    
    try:
        await context.bot.send_message(
            uid_to_unban_int,
            "✅ **YOU HAVE BEEN UNBANNED** ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎉 CONGRATULATIONS! YOU HAVE BEEN UNBANNED.\n"
            "✨ YOU CAN NOW USE ALL BOT FEATURES AGAIN.\n\n"
            "📞 USE /start TO BEGIN USING THE BOT.",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text(
        f"✅ USER UNBAN SUCCESSFUL ✅\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔓 Unbanned User ID: `{uid_to_unban}`\n"
        f"📊 Status: User can now use all bot features again.",
        parse_mode="Markdown",
        reply_markup=system_config_keyboard()
    )
    context.user_data["admin_unban_mode"] = False

async def show_banned_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banned_list = load_banned_users()
    
    if not banned_list:
        await update.message.reply_text("📜 **BANNED USER LIST** 📜\n━━━━━━━━━━━━━━━━━━━━\n\n✅ No users are currently banned.", parse_mode="Markdown", reply_markup=system_config_keyboard())
        return
    
    banned_text = "📜 **BANNED USER LIST** 📜\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, uid in enumerate(banned_list, 1):
        banned_text += f"{i}. User ID: `{uid}`\n"
    
    banned_text += f"\n📊 Total Banned Users: {len(banned_list)}"
    
    await update.message.reply_text(banned_text, parse_mode="Markdown", reply_markup=system_config_keyboard())

# ==================== MESSAGE HANDLER SECTION ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    text = update.message.text.strip()

    if context.user_data.get("withdraw_mode") == "select_method":
        await withdraw_method_selected(update, context)
        return
    
    if context.user_data.get("withdraw_mode") == "amount":
        await withdraw_amount_received(update, context)
        return
    
    if context.user_data.get("withdraw_mode") == "number":
        await withdraw_number_received(update, context)
        return

    if context.user_data.get("add_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_add_user"):
            await process_add_balance_amount(update, context)
        else:
            await process_add_balance_user(update, context)
        return
    
    if context.user_data.get("remove_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_remove_user"):
            await process_remove_balance_amount(update, context)
        else:
            await process_remove_balance_user(update, context)
        return

    if context.user_data.get("admin_ban_mode") and is_admin(uid):
        await process_ban_user(update, context)
        return
    
    if context.user_data.get("admin_unban_mode") and is_admin(uid):
        await process_unban_user(update, context)
        return

    if not is_admin(uid) and is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown", reply_markup=main_keyboard(uid))
        return

    if text == "❌ CANCEL":
        context.user_data["mode"] = None
        context.user_data["broadcast_mode"] = False
        context.user_data["admin_ban_mode"] = False
        context.user_data["admin_unban_mode"] = False
        context.user_data["add_balance_mode"] = False
        context.user_data["remove_balance_mode"] = False
        context.user_data["withdraw_mode"] = None
        context.user_data["withdraw_method"] = None
        context.user_data["withdraw_amount"] = None
        context.user_data["pending_add_user"] = None
        context.user_data["pending_remove_user"] = None
        await update.message.reply_text("❌ CANCELLED", reply_markup=main_keyboard(uid))
        return

    if text == "➕ ADD BALANCE" and context.user_data.get("system_config_mode") == "main" and is_admin(uid):
        await admin_add_balance_start(update, context)
        return

    if text == "➖ REMOVE BALANCE" and context.user_data.get("system_config_mode") == "main" and is_admin(uid):
        await admin_remove_balance_start(update, context)
        return

    if text == "👤 PROFILE":
        user_data = get_user(uid)
        stats = get_user_stats(uid)
        
        user = update.effective_user
        full_name = html.escape(user.full_name)
        username = html.escape(user.username or "No username")
        user_id = uid
        balance = user_data.get("balance", 0)
        
        profile_text = (
            f"👤 <b>YOUR PROFILE ALL DETAILS</b> 👤\n\n"
            f"<blockquote>🏷️ YOUR NAME : <b>{full_name}</b></blockquote>\n"
            f"<blockquote>🆔 YOUR USERNAME : <b>@{username}</b></blockquote>\n"
            f"<blockquote>🗝️ YOUR TELEGRAM ID : <code>{user_id}</code></blockquote>\n\n"
            f"<blockquote>💵 CURRENT BALANCE : <b>{format_balance(balance)} BDT 💰</b></blockquote>\n\n"
            f"✨ <b>TODAY ({datetime.now().strftime('%d/%m/%Y')})</b>\n"
            f"<blockquote>📱 NUMBERS TAKEN : {stats['today_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['today_otps']} ⚡️</blockquote>\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n"
            f"<blockquote>📱 NUMBERS TAKEN : {stats['last7d_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['last7d_otps']} 🚀</blockquote>\n\n"
            f"🌐 <b>ALL TIME RECORD</b>\n"
            f"<blockquote>📱 TOTAL NUMBERS : {stats['total_numbers']}\n"
            f"🔑 TOTAL OTPS : {stats['total_otps']} 💎</blockquote>"
        )
        await update.message.reply_text(profile_text, parse_mode="HTML")
        return

    if text == "💰 BALANCE":
        balance = get_user(uid)['balance']
        balance_text = (
            f"💰 <b>YOUR CURRENT BALANCE</b> 💰\n\n"
            f"<blockquote>💵 TOTAL BALANCE: <b>{format_balance(balance)} BDT</b></blockquote>"
        )

        withdraw_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw_start", style="primary")]
        ])

        await update.message.reply_text(
            balance_text,
            parse_mode="HTML",
            reply_markup=withdraw_keyboard
        )
        return
    if text == "👥 REFER AND EARN":
        await refer_command(update, context)
        return

    if text == "📶 VIEW RANGE":
        await view_range_command(update, context)
        return
    if text == "⚡ GET 2FA":
        await get_2fa_code(update, context)
        return

    if text == "👥 JOIN METHOD GROUP":
        await join_method_group_command(update, context)
        return

    if text == "💬 SUPPORT":
        support_text = "💬 SUPPORT 🎧\n\nCLICK THE BUTTON BELOW TO CONTACT SUPPORT 📩"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 SUPPORT", url="https://t.me/Sanra03263", style="primary")],
            [InlineKeyboardButton("👨💻 OWNER BY", url="https://t.me/abraher32900", style="primary")]
        ])
        await update.message.reply_text(support_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    if text == "🔍 SEARCH OTP":
        context.user_data["mode"] = "search_otp"
        await update.message.reply_text("🔍 **ENTER THE NUMBER TO SEARCH OTP:**", parse_mode="Markdown")
        return

    if context.user_data.get("mode") == "search_otp":
        context.user_data["mode"] = None
        await request_queue.put({'type': 'search_otp', 'update': update, 'context': context, 'target_num': normalize_number(text)})
        return

    if text == "📞 GET NUMBER":
        context.user_data["mode"] = "range_1"
        await update.message.reply_text("📶 ENTER RANGE ID ( 1 NUMBER ) :")
        return

    if text == "📞 GET 10 NUMBER":
        context.user_data["mode"] = "range_10"
        await update.message.reply_text("📶 ENTER RANGE ID ( 10 NUMBER ) :")
        return

    if context.user_data.get("mode") in ["range_1", "range_10"]:
        if "X" in text.upper() or text.isdigit():
            count = 1 if context.user_data["mode"] == "range_1" else 10
            context.user_data["mode"] = None
            await request_queue.put({'type': 'process_numbers', 'update': update, 'context': context, 'range_text': text, 'count': count})
        return
    if context.user_data.get("mode") == "get_2fa":
        await process_2fa_key(update, context)
        return
    
    # ==================== ADMIN PANEL - MAIN HANDLERS ====================

    if text == "⚙️ ADMIN PANEL ⚙️" and is_admin(uid):
        context.user_data["admin_mode"] = "main"
        admin_welcome = ("⌬━━━━━━━━━━━━━━━━━━━━⌬\n       WELCOME ADMIN PANEL\n⌬━━━━━━━━━━━━━━━━━━━━⌬")
        await update.message.reply_text(admin_welcome, reply_markup=admin_main_keyboard(), parse_mode="Markdown")
        return

    if text == "🔙 BACK TO MAIN" and context.user_data.get("admin_mode"):
        context.user_data["admin_mode"] = None
        context.user_data["user_management_mode"] = None
        context.user_data["system_config_mode"] = None
        await update.message.reply_text("🔙 Back to main menu.", reply_markup=main_keyboard(uid))
        return

    if text == "🔙 BACK TO ADMIN" and (context.user_data.get("user_management_mode") or context.user_data.get("system_config_mode")):
        context.user_data["user_management_mode"] = None
        context.user_data["system_config_mode"] = None
        context.user_data["admin_mode"] = "main"
        await update.message.reply_text("🔙 Back to admin panel.", reply_markup=admin_main_keyboard())
        return

    if text == "👥 USER MANAGEMENT" and context.user_data.get("admin_mode") == "main" and is_admin(uid):
        context.user_data["user_management_mode"] = "main"
        await update.message.reply_text("👥 User Management Panel:", reply_markup=user_management_keyboard())
        return

    if text == "⚙️ SYSTEM CONFIGURATION" and context.user_data.get("admin_mode") == "main" and is_admin(uid):
        context.user_data["system_config_mode"] = "main"
        await update.message.reply_text("⚙️ System Configuration Panel:", reply_markup=system_config_keyboard())
        return
    
    if text == "📈 TODAY ALL STATUS" and context.user_data.get("system_config_mode") == "main" and is_admin(uid):
        t_n, t_o, s_n, s_o, tot_n, tot_o = get_global_system_stats()
        status_msg = (
            f"📊 <b>ALL EARNINGS & SYSTEM STATUS</b> 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ <b>TODAY ({datetime.now().strftime('%d/%m/%Y')})</b>\n"
            f"📱 NUMBERS TAKEN : {t_n}\n"
            f"🔑 OTPS RECEIVED : {t_o} ⚡\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n"
            f"📱 NUMBERS TAKEN : {s_n}\n"
            f"🔑 OTPS RECEIVED : {s_o} 🚀\n\n"
            f"🌐 <b>ALL TIME RECORD</b>\n"
            f"📱 TOTAL NUMBERS : {tot_n}\n"
            f"🔑 TOTAL OTPS : {tot_o} 💎\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 <b>Quick Number | LIVE REAL-TIME DATA</b> ⚡"
        )
        await update.message.reply_text(status_msg, parse_mode="HTML")
        return
    
    if text == "👤 USER STATUS CHECK" and is_admin(uid):
        context.user_data["mode"] = "input_user_id"
        msg = (
            "<blockquote>🔍 <b>ENTER TELEGRAM ID</b> 🔍</blockquote>\n\n"
            "<blockquote>💬 PLEASE ENTER THE TELEGRAM ID OF THE USER YOU WANT TO SEARCH FOR :</blockquote>"
        )
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    if context.user_data.get("mode") == "input_user_id" and is_admin(uid):
        target_uid = text.strip()
        if not target_uid.isdigit():
            await update.message.reply_text("❌ INVALID ID! PLEASE SEND A NUMERIC TELEGRAM ID.")
            return
        
        context.user_data["mode"] = None
        stats = get_user_stats(target_uid)
        
        status_msg = (
            f"👤 <b>USER STATUS CHECK</b> 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ <b>TODAY ({datetime.now().strftime('%d/%m/%Y')})</b>\n"
            f"📱 NUMBERS TAKEN : {stats['today_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['today_otps']} ⚡\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n"
            f"📱 NUMBERS TAKEN : {stats['last7d_numbers']}\n"
            f"🔑 OTPS RECEIVED : {stats['last7d_otps']} 🚀\n\n"
            f"🌐 <b>ALL TIME RECORD</b>\n"
            f"📱 TOTAL NUMBERS : {stats['total_numbers']}\n"
            f"🔑 TOTAL OTPS : {stats['total_otps']} 💎\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 <b>Quick Number | LIVE REAL-TIME DATA</b> ⚡"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 CHECK ALL DATA 📂", callback_data=f"full_logs_{target_uid}")]
        ])
        
        await update.message.reply_text(status_msg, parse_mode="HTML", reply_markup=keyboard)
        return

# ==================== ADMIN PANEL - ALL USER ID ====================

    if text == "🆔 ALL USER ID" and context.user_data.get("user_management_mode") == "main" and is_admin(uid):
        users = get_all_users()
        if users:
            total_users = len(users)
            file_lines = []
            for i, user_id in enumerate(users, 1):
                file_lines.append(f"{i}️⃣ {user_id}")
            
            file_content = "\n".join(file_lines)
            file = io.BytesIO(file_content.encode("utf-8"))
            file.name = f"ALL_USERS_{total_users}.txt"
            
            caption = f"📋 **ALL USER LIST** 📋\n\n👥 Total Users: {total_users}"
            await update.message.reply_document(
                document=file,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=user_management_keyboard()
            )
        else:
            await update.message.reply_text("No users found.", reply_markup=user_management_keyboard())
        return

    if text == "💰 ALL USER BALANCE" and context.user_data.get("user_management_mode") == "main" and is_admin(uid):
        user_db = load_data(USER_DATA_FILE)
        if user_db:
            total_users = len(user_db)
            total_system_balance = 0.0
            balance_lines = []
            
            for i, (user_id, info) in enumerate(user_db.items(), 1):
                u_bal = info.get("balance", 0.0)
                total_system_balance += u_bal
                balance_lines.append(f"{i}. ID: {user_id} | Balance: {u_bal:.2f} BDT")
            
            file_content = "💰 ALL USER BALANCE REPORT 💰\n"
            file_content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            file_content += f"👥 Total Users: {total_users}\n"
            file_content += f"💵 Total System Balance: {total_system_balance:.2f} BDT\n"
            file_content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            file_content += "\n".join(balance_lines)
            
            file_io = io.BytesIO(file_content.encode("utf-8"))
            file_io.name = f"{total_system_balance:.2f}bdt.txt"
            
            report_msg = (
                "💰 <b>ALL USER BALANCE REPORT</b> 💰\n\n"
                f"<blockquote>👥 Total Users: {total_users}</blockquote>\n"
                f"<blockquote>💵 Total System Balance: {total_system_balance:.2f} BDT</blockquote>"
            )
            
            await update.message.reply_document(
                document=file_io,
                caption=report_msg,
                parse_mode="HTML",
                reply_markup=user_management_keyboard()
            )
        else:
            await update.message.reply_text("❌ No user data found.")
        return

    if text == "📜 BAN USER LIST" and (context.user_data.get("user_management_mode") == "main" or context.user_data.get("system_config_mode") == "main") and is_admin(uid):
        await show_banned_users_list(update, context)
        return

    if text == "⛔ BAN USER" and context.user_data.get("system_config_mode") == "main" and is_admin(uid):
        await admin_ban_user_start(update, context)
        return

    if text == "🔓 UNBAN USER" and context.user_data.get("system_config_mode") == "main" and is_admin(uid):
        await admin_unban_user_start(update, context)
        return

    if text == "📢 SEND MESSAGE TO ALL USERS" and is_admin(uid):
        context.user_data["broadcast_mode"] = True
        await update.message.reply_text(
            "📢 <b>ADMIN BROADCAST SYSTEM (PRO)</b>\n\n"
            "💬 আপনি এখন যা পাঠাবেন (Text, PNG, Photo, Video, File, Forward) তা সকল ইউজারের কাছে প্রফেশনাল হেডারসহ চলে যাবে।\n\n"
            "✨ রেঞ্জ (যেমন: 237XXX) থাকলে তা অটোমেটিক ক্লিক-টু-কপি হয়ে যাবে।", 
            parse_mode="HTML", 
            reply_markup=cancel_keyboard()
        )
        return

    if context.user_data.get("broadcast_mode") and is_admin(uid):
        context.user_data["broadcast_mode"] = False
        
        user_db = load_data(USER_DATA_FILE)
        all_uids = list(user_db.keys())
        
        if not all_uids:
            await update.message.reply_text("❌ পাঠানোর জন্য কোনো ইউজার পাওয়া যায়নি!")
            return

        success_ids, fail_ids = [], []
        status_msg = await update.message.reply_text(f"🚀 <b>ব্রডকাস্ট শুরু হয়েছে...</b>\n🎯 টার্গেট: {len(all_uids)} জন ইউজার।", parse_mode="HTML")

        def format_broadcast_msg(text_content):
            if not text_content: return "<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>"
            formatted = re.sub(r'(\d{3,}[xX]{3,})', r'<code>\1</code>', str(text_content))
            return f"<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>\n\n{formatted}"

        for user_id_str in all_uids:
            try:
                target_id = int(user_id_str)
                
                if update.message.text:
                    await context.bot.send_message(chat_id=target_id, text=format_broadcast_msg(update.message.text), parse_mode="HTML")
                else:
                    new_caption = format_broadcast_msg(update.message.caption) if update.message.caption else "<blockquote>📢 <b>ADMIN NOTICE :</b></blockquote>"
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=update.message.chat_id,
                        message_id=update.message.message_id,
                        caption=new_caption,
                        parse_mode="HTML"
                    )
                
                success_ids.append(user_id_str)
            except:
                fail_ids.append(user_id_str)
            
            await asyncio.sleep(0.05)

        report_text = (
            f"✅ <b>ADMIN NOTICE COMPLETE !</b>\n\n"
            f"📊 <b>BROADCAST REPORT:</b>\n\n"
            f"<blockquote>✅ SUCCESSFULLY SENT: {len(success_ids)} USERS !</blockquote>\n"
            f"<blockquote>❌ FAILED TO SEND: {len(fail_ids)} USERS !</blockquote>"
        )
        
        await status_msg.delete()
        await context.bot.send_message(chat_id=uid, text=report_text, parse_mode="HTML", reply_markup=main_keyboard(uid))

        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if success_ids:
            s_file = io.BytesIO(("\n".join(success_ids)).encode()); s_file.name = f"SUCCESS_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=s_file, caption="✅ Success User List")
        if fail_ids:
            f_file = io.BytesIO(("\n".join(fail_ids)).encode()); f_file.name = f"FAILED_{random_suffix}.txt"
            await context.bot.send_document(chat_id=uid, document=f_file, caption="❌ Failed User List")
        
        return

    else:
        await update.message.reply_text("🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

# ==================== COMMAND HANDLERS SECTION ====================

async def get1number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    context.user_data["mode"] = "range_1"
    await update.message.reply_text("📶 ENTER RANGE ID ( 1 NUMBER ) :")

async def get10number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    context.user_data["mode"] = "range_10"
    await update.message.reply_text("📶 ENTER RANGE ID ( 10 NUMBER ) :")

async def searchotp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    context.user_data["mode"] = "search_otp"
    await update.message.reply_text("🔍 **ENTER THE NUMBER TO SEARCH OTP:**", parse_mode="Markdown")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    balance = get_user(uid)['balance']
    await update.message.reply_text(f"💰 YOUR CURRENT BALANCE: `{format_balance(balance)} BDT`", parse_mode="Markdown", reply_markup=main_keyboard(uid))

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    
    user_data = get_user(uid)
    stats = get_user_stats(uid)
    
    user = update.effective_user
    full_name = user.full_name
    username = user.username or "No username"
    user_id = uid
    balance = user_data.get("balance", 0)
    
    profile_text = (
        f"👤 YOUR PROFILE ALL DETAILS 👤\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ YOUR NAME : `{full_name}`\n"
        f"🆔 YOUR USERNAME : @{username}\n"
        f"🗝️ YOUR TELEGRAM ID : `{user_id}`\n\n"
        f"💵 CURRENT BALANCE : {format_balance(balance)} BDT 💰\n\n"
        f"✨ TODAY ({datetime.now().strftime('%d/%m/%Y')})\n"
        f"📱 NUMBERS TAKEN : {stats['today_numbers']}\n"
        f"🔑 OTPS RECEIVED : {stats['today_otps']} ⚡\n\n"
        "🔥 LAST 7 DAYS\n"
        f"📱 NUMBERS TAKEN : {stats['last7d_numbers']}\n"
        f"🔑 OTPS RECEIVED : {stats['last7d_otps']} 🚀\n\n"
        "🌐 ALL TIME RECORD\n"
        f"📱 TOTAL NUMBERS : {stats['total_numbers']}\n"
        f"🔑 TOTAL OTPS : {stats['total_otps']} 💎\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(profile_text, parse_mode="Markdown")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    support_text = "💬 SUPPORT 🎧\n\nCLICK THE BUTTON BELOW TO CONTACT SUPPORT 📩"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 SUPPORT", url="https://t.me/abraher32900", style="primary")],
        [InlineKeyboardButton("👨💻 OWNER BY", url="https://t.me/abraher32900", style="primary")]
    ])
    await update.message.reply_text(support_text, reply_markup=keyboard, parse_mode="Markdown")

async def refer_command_slash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    await refer_command(update, context)

async def viewrange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return
    await view_range_command(update, context)

# ==================== START & CALLBACK SECTION ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)
    
    existing_data = load_data(USER_DATA_FILE)
    is_new_user = uid_str not in existing_data
    
    if is_new_user:
        get_user(uid)
    
    args = context.args
    if args:
        param = args[0]
        
        if is_range_request(param):
            range_text = param
            print(f"🎯 Range request detected: {param}")
            await request_queue.put({
                'type': 'auto_number', 
                'update': update, 
                'context': context, 
                'range_text': range_text
            })
            return
        elif is_referral_request(param) and is_new_user:
            try:
                referrer_id = param
                if str(referrer_id) != str(uid):
                    referrer_id_int = int(referrer_id)
                    
                    if str(referrer_id_int) in existing_data:
                        current_count = get_referral_count(referrer_id_int)
                        new_count = current_count + 1
                        update_referral_count(referrer_id_int, new_count)
                        
                        await update_db_balance(referrer_id_int, REFERRAL_PRICE)

                        log_global_activity(referrer_id_int, "REFERRAL_JOINED", {"referred_user": uid})
                        
                        referrer_msg = (
                            f"🎉 <b>NEW REFERRAL!</b> 🎉\n\n"
                            f"<blockquote>🚀 SOMEONE HAS JUST JOINED USING YOUR UNIQUE LINK !</blockquote>\n\n"
                            f"<blockquote>🗝️ TELEGRAM ID : <code>{uid}</code>\n"
                            f"💰 REWARD ADDED: {format_balance(REFERRAL_PRICE)} BDT 💵\n"
                            f"✨ STATUS: CREDITED TO YOUR WALLET ✅</blockquote>\n\n"
                            f"📊 <b>YOUR UPDATED REFERRAL STATS:</b>\n\n"
                            f"<blockquote>👥 TOTAL REFERRALS: {new_count} USER\n"
                            f"💵 TOTAL EARNED: {format_balance(new_count * REFERRAL_PRICE)} BDT 💎</blockquote>"
                        )
                        
                        await context.bot.send_message(
                            referrer_id_int,
                            referrer_msg,
                            parse_mode="HTML"
                        )
            except Exception as e:
                print(f"Referral error: {e}")
    
    context.user_data.clear()
    
    if not is_admin(uid) and not is_user_joined_channels(uid):
        force_join_msg = "📢 **TO USE THIS BOT, YOU MUST JOIN THESE CHANNELS.**\n\nTHESE ARE OUR OFFICIAL CHANNELS. YOU CAN STAY HERE SECURELY WITHOUT ANY ISSUES !"
        await update.message.reply_text(force_join_msg, parse_mode="Markdown", reply_markup=force_join_keyboard())
        return
    
    start_msg = WELCOME_MESSAGE
    
    await update.message.reply_text(start_msg, parse_mode="Markdown")
    await update.message.reply_text("🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()
    
    if not is_admin(uid) and is_user_banned(uid):
        await query.edit_message_text("🚫 YOU ARE BANNED 🚫\n━━━━━━━━━━━━━━━━━━━━\n\n❌ YOU HAVE BEEN BANNED FROM USING THIS BOT.\n📞 CONTACT SUPPORT FOR MORE INFORMATION.", parse_mode="Markdown")
        return
    
    if data == "force_join_confirm":
        user_joined_status.add(uid)
        start_msg = WELCOME_MESSAGE
        await query.message.edit_text(start_msg, parse_mode="Markdown")
        await context.bot.send_message(chat_id=uid, text="🔹 PLEASE USE THE BUTTONS BELOW :", reply_markup=main_keyboard(uid))
        return
    
    if data == "withdraw_start":
        balance = get_user(uid)['balance']
        if balance < MIN_WITHDRAW:
            msg = (
                f"<blockquote>💵 TOTAL BALANCE: {format_balance(balance)} BDT\n\n"
                f"📉 MINIMUM WITHDRAW 50 BDT\n\n"
                f"📈 MAX WITHDRAWAL 10000 BDT</blockquote>"
            )
            await query.message.reply_text(msg, parse_mode="HTML")
            return

        context.user_data["withdraw_mode"] = "select_method"
        await query.message.reply_text("💳 SELECT YOUR PAYMENT METHOD !", reply_markup=withdraw_method_keyboard())
        return
    
    if data == "withdraw_confirm":
        await process_withdraw_confirm(update, context)
        return
    
    if data == "withdraw_cancel":
        await process_withdraw_cancel(update, context)
        return
    
    if data.startswith("pre_approve_"):
        pid = data.replace("pre_approve_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 NO, BACK", callback_data=f"back_admin_{pid}"),
                InlineKeyboardButton("✅ YES, CONFIRM", callback_data=f"admin_approve_{pid}")
            ]
        ])
        await query.message.edit_text("❓ **Are you sure? You want to CONFIRM this payment?**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("pre_reject_"):
        pid = data.replace("pre_reject_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 NO, BACK", callback_data=f"back_admin_{pid}"),
                InlineKeyboardButton("❌ YES, REJECT", callback_data=f"admin_reject_{pid}")
            ]
        ])
        await query.message.edit_text("❓ **Are you sure? You want to REJECT this payment?**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("back_admin_"):
        pid = data.replace("back_admin_", "")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ CANCEL", callback_data=f"pre_reject_{pid}"),
                InlineKeyboardButton("✅ CONFIRM", callback_data=f"pre_approve_{pid}")
            ]
        ])
        await query.message.edit_text("⚠️ **Action Cancelled. Decision again:**", reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("admin_approve_"):
        payment_id = data.replace("admin_approve_", "")
        await admin_approve_withdraw(update, context, payment_id)
        return
    
    if data.startswith("admin_reject_"):
        payment_id = data.replace("admin_reject_", "")
        await admin_reject_withdraw(update, context, payment_id)
        return

    if data == "same_range":
        r_text = last_range.get(uid)
        if r_text:
            try:
                new_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 OTP GROUP", url=FORCE_JOIN_CHANNELS["OTP_GROUP"])]
                ])
                if query.message.reply_markup != new_keyboard:
                    await query.message.edit_reply_markup(reply_markup=new_keyboard)
            except Exception:
                pass
            
            await process_numbers(update, context, r_text, 1)
    
    elif data.startswith("copy_name_"):
        name_to_copy = data.replace("copy_name_", "")
        await query.answer(f"✅ Copied: {name_to_copy}", show_alert=True)
    
    elif data.startswith("copy_id_"):
        id_to_copy = data.replace("copy_id_", "")
        await query.answer(f"✅ Copied ID: {id_to_copy}", show_alert=True)
    
    elif data.startswith("copy_text_"):
        text_to_copy = data.replace("copy_text_", "")
        await query.answer(f"✅ Copied: {text_to_copy}", show_alert=True)
        
    elif data.startswith("copykey_"):
        key_to_copy = data.replace("copykey_", "")
        await query.message.reply_text(f"🔑 **KEY:** `{key_to_copy}`\n\n✅ SUCCESSFULLY COPIED!", parse_mode="Markdown")
        await query.answer("✅ KEY COPIED SUCCESSFULLY!", show_alert=True)
    
    elif data.startswith("copycode_"):
        code_to_copy = data.replace("copycode_", "")
        await query.message.reply_text(f"🔢 **CODE:** `{code_to_copy}`\n\n✅ SUCCESSFULLY COPIED!", parse_mode="Markdown")
        await query.answer("✅ CODE COPIED SUCCESSFULLY!", show_alert=True)

    elif data.startswith("my_ref_"):
        target_uid = data.replace("my_ref_", "")
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        user_data_db = load_data(USER_DATA_FILE)
        user_info = user_data_db.get(str(target_uid), {})
        
        my_referrals = [log for log in all_logs if str(log.get('uid')) == str(target_uid) and log.get('action') == "REFERRAL_JOINED"]
        
        content = f"👥 YOUR REFERRAL REPORT 👥\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"🆔 YOUR TELEGRAM ID : {target_uid}\n"
        content += f"📊 TOTAL REFERRALS : {len(my_referrals)} USER\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"📜 LIST OF ALL REFERRAL IDS (12H FORMAT):\n\n"
        
        if not my_referrals:
            content += "❌ NO REFERRAL DATA FOUND.\n"
        else:
            for i, log in enumerate(my_referrals, 1):
                try:
                    dt_obj = datetime.fromisoformat(log['timestamp'])
                    formatted_time = dt_obj.strftime("%I:%M:%S %p")
                    date_str = dt_obj.strftime("%d/%m/%Y")
                    details = log.get('details', {})
                    ref_id = details.get('referred_user', 'N/A')
                    content += f"{i}. ID: {ref_id} | DATE: {date_str} | TIME: {formatted_time}\n"
                except: continue

        content += f"\n\n🚀 GENERATED BY MA AMAR JAN SYSTEM"
        
        random_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        file = io.BytesIO(content.encode("utf-8"))
        file.name = f"REF_{random_name}.txt"
        
        await context.bot.send_document(
            chat_id=uid,
            document=file,
            caption=f"✅ **YOUR FULL REFERRAL DATA REPORT**",
            parse_mode="Markdown"
        )

    elif data.startswith("full_logs_"):
        target_uid = data.replace("full_logs_", "")
        stats = get_user_stats(target_uid)
        
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        user_data_db = load_data(USER_DATA_FILE)
        user_info = user_data_db.get(str(target_uid), {})
        
        user_otps = [log for log in all_logs if str(log.get('uid')) == str(target_uid) and log.get('action') == "OTP_RECEIVED"]
        
        content = f"📊 USER FULL DATA REPORT 📊\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"🆔 USER TELEGRAM ID : {target_uid}\n"
        content += f"🏷️ USER NAME : {str(user_info.get('full_name', 'N/A')).upper()}\n"
        content += f"🆔 TELEGRAM USERNAME : @{str(user_info.get('username', 'NO_USERNAME')).upper()}\n"
        content += f"💰 CURRENT BALANCE : {user_info.get('balance', 0.0)} BDT\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"📈 SYSTEM STATUS SUMMARY:\n"
        content += f"✨ TODAY NUMBERS TAKEN : {stats['today_numbers']}\n"
        content += f"✨ TODAY OTPS RECEIVED : {stats['today_otps']}\n"
        content += f"🔥 LAST 7 DAYS NUMBERS : {stats['last7d_numbers']}\n"
        content += f"🔥 LAST 7 DAYS OTPS : {stats['last7d_otps']}\n"
        content += f"🌐 LIFETIME NUMBERS : {stats['total_numbers']}\n"
        content += f"🌐 LIFETIME OTPS : {stats['total_otps']}\n"
        content += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += f"📜 DETAILED OTP LOGS (TIME FORMAT: 12H):\n\n"
        
        if not user_otps:
            content += "❌ NO OTP DATA FOUND FOR THIS USER.\n"
        else:
            for i, log in enumerate(user_otps, 1):
                try:
                    dt_obj = datetime.fromisoformat(log['timestamp'])
                    formatted_time = dt_obj.strftime("%I:%M:%S %p")
                    date_str = dt_obj.strftime("%d/%m/%Y")
                    details = log.get('details', {})
                    content += f"{i}. DATE: {date_str} | TIME: {formatted_time}\n"
                    content += f"   📞 NUMBER: {details.get('number', 'N/A')}\n"
                    content += f"   🔑 OTP: {details.get('otp', 'N/A')}\n"
                    content += f"   📩 SMS: {details.get('sms', 'N/A')}\n"
                    content += f"   -----------------------------------\n"
                except: continue

        content += f"\n\n🚀 GENERATED BY MA AMARJAN SYSTEM ⚡"
        
        file = io.BytesIO(content.encode("utf-8"))
        file.name = f"USER_{target_uid}_FULL_DATA.txt"
        
        await context.bot.send_document(
            chat_id=uid,
            document=file,
            caption=f"✅ <b>ALL DATA FOR USER:</b> <code>{target_uid}</code>",
            parse_mode="HTML"
        )

# ==================== MAIN & POST INIT SECTION ====================

async def post_init(application): 
    for _ in range(20):
        asyncio.create_task(worker())
    asyncio.create_task(monitor_loop(application))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get1number", get1number_command))
    app.add_handler(CommandHandler("get10number", get10number_command))
    app.add_handler(CommandHandler("searchotp", searchotp_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("refer", refer_command_slash))
    app.add_handler(CommandHandler("viewrange", viewrange_command))
    app.add_handler(CommandHandler("joinmethodgroup", join_method_group_command))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 BOT RUNNING...")  
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()