"""
╔══════════════════════════════════════════════╗
║     UNIVERSAL QOROVUL BOT — KONFIGURATSIYA   ║
╚══════════════════════════════════════════════╝
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Tokenlar ──────────────────────────────────
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

SECRET_OWNER_ID: int   = int(os.environ.get("SECRET_OWNER_ID",   "0"))
SECRET_OWNER_ID_2: int = int(os.environ.get("SECRET_OWNER_ID_2", "0"))
OWNER_IDS: list[int]   = [uid for uid in [SECRET_OWNER_ID, SECRET_OWNER_ID_2] if uid]

ADMIN_IDS: list[int] = []   # /addadmin orqali dinamik to'ldiriladi

# ── Standart guruh sozlamalari ─────────────────
DEFAULT_SETTINGS: dict = {
    # Anti-spam
    "anti_spam":            True,
    "spam_message_limit":   5,
    "spam_time_window":     10,
    "spam_action":          "mute",
    "mute_duration_minutes":15,

    # Himoya
    "anti_link":            True,
    "allowed_domains":      ["t.me", "telegram.me"],
    "anti_forward":         True,
    "bad_words_filter":     True,
    "anti_sticker_spam":    True,
    "sticker_limit":        3,
    "sticker_time_window":  30,
    "anti_arabic":          False,
    "new_member_media_restrict":  True,
    "new_member_restrict_hours":  24,

    # Tungi rejim
    "night_mode":           False,
    "night_start_hour":     23,
    "night_end_hour":       6,

    # Warn tizimi
    "max_warns":            3,

    # Reklama tozalash
    "anti_ad":                  True,
    "anti_channel_username":    True,
    "anti_bot_username":        True,
    "anti_inline_buttons":      True,
    "anti_contact_spam":        True,
    "anti_location_spam":       True,
    "anti_long_forward":        True,
    "long_forward_limit":       3,
    "long_forward_window":      60,
    "anti_ad_patterns":         True,
    "anti_channel_bot":         True,

    # Sanoqchi
    "counter_enabled":      True,
    "top_users_count":      10,
}

# ── Reklama patternlari ────────────────────────
AD_PATTERNS: list[str] = [
    r"(?i)reklama\s*(uchun|narx|bepul|arzon|chegirma)",
    r"(?i)(sotiladi|sotaman|sotamiz|sotiladigan)",
    r"(?i)(pul\s*ishla|daromad|oylik\s*maosh)",
    r"(?i)(qo'shimcha\s*daromad|ish\s*taklif)",
    r"(?i)(kanalga\s*obuna|kanalimizga\s*a'zo)",
    r"(?i)(botimizga\s*start|botga\s*start)",
    r"(?i)(chegirma|aksiya|maxsus\s*taklif)",
    r"(?i)(заработ|доход|реклам|продаж|скидк)",
    r"(?i)(подписыва|канал\s*подпис)",
    r"(?i)(earn\s*money|make\s*money|free\s*bitcoin)",
    r"(?i)(join\s*(my|our)\s*(channel|group))",
    r"(?i)(subscribe\s*(to|my|our))",
    r"(?i)(click\s*(here|link|below))",
    r"(?i)(limited\s*offer|act\s*now|hurry\s*up)",
    r"(?i)(crypto|nft|airdrop|giveaway)\s*(free|earn|win)",
    r"(?i)(dm\s*me|inbox\s*me|message\s*me)\s*(for|to)",
    r"(?i)(?:bit\.ly|tinyurl|goo\.gl|t\.co|short\.link|cutt\.ly|rb\.gy)/",
]

# ── Barcha xabarlar (O'zbek tilida) ───────────
MESSAGES: dict[str, str] = {
    # Guard
    "spam_warn":    "⚠️ <b>{name}</b>, spam qilmang!",
    "spam_muted":   "🔇 <b>{name}</b> — spam. <b>{duration}</b> daqiqa mute.",
    "spam_banned":  "🚫 <b>{name}</b> — spam tufayli ban.",
    "link_deleted": "🔗 <b>{name}</b>, tashqi havolalar taqiqlangan!",
    "forward_deleted":"🔄 <b>{name}</b>, forward taqiqlangan!",
    "bad_word_deleted":"🤬 <b>{name}</b>, nojo'ya so'z taqiqlangan!",
    "sticker_spam": "🎭 <b>{name}</b>, sticker spam taqiqlangan!",

    # Warn
    "warn_given":   "⚠️ <b>{name}</b> — ogohlantirish <b>{count}/{max}</b>\n📝 {reason}",
    "warn_ban":     "🚫 <b>{name}</b> — {max} ogohlantirish. Ban!",

    # Mute / Ban
    "muted":        "🔇 <b>{name}</b> — {duration} daqiqa mute.",
    "unmuted":      "🔊 <b>{name}</b> — mute olib tashlandi.",
    "banned":       "🚫 <b>{name}</b> — guruhdan chiqarildi.",
    "unbanned":     "✅ <b>{name}</b> — blok olib tashlandi.",
    "kicked":       "👢 <b>{name}</b> — chiqarildi (qayta kira oladi).",

    # Tungi rejim
    "night_mode_on":  "🌙 Tungi rejim <b>yoqildi</b>. Faqat adminlar yoza oladi.",
    "night_mode_off": "☀️ Tungi rejim <b>o'chirildi</b>. Barcha yoza oladi.",

    # Reklama
    "ad_deleted":               "📢 <b>{name}</b>, reklama taqiqlangan!",
    "channel_username_deleted": "📢 <b>{name}</b>, kanal/bot usernamelar taqiqlangan!",
    "contact_spam_deleted":     "📇 <b>{name}</b>, kontakt spam taqiqlangan!",
    "inline_ad_deleted":        "🔘 <b>{name}</b>, reklama tugmalari taqiqlangan!",
    "forward_spam_deleted":     "🔄 <b>{name}</b>, ko'p forward taqiqlangan!",
    "ad_pattern_deleted":       "📢 <b>{name}</b>, reklama matni aniqlandi!",

    # Xatoliklar
    "not_admin":            "❌ Siz admin emassiz!",
    "bot_not_admin":        "❌ Bot admin emas! Menga admin bering.",
    "no_reply":             "❌ Buyruqni xabariga <b>reply</b> qilib yuboring.",
    "cant_restrict_admin":  "❌ Adminni cheklab bo'lmaydi!",
    "group_only":           "❌ Bu buyruq faqat <b>guruhlarda</b> ishlaydi.",
}
