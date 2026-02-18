# ============================================================
#  TELEGRAM UNIVERSAL BOT — KONFIGURATSIYA
#  Qorovul + Sanoqchi + Reklama Tozalagich
# ============================================================
import os

# 🔑 Token va Owner ID environment variable'lardan o'qiladi
# Railway'da yoki .env faylda sozlang
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# 👑 YASHIRIN BOT EGASI — hech kimga ko'rinmaydi!
SECRET_OWNER_ID = int(os.environ.get("SECRET_OWNER_ID", "0"))

# 🛡️ Oddiy adminlar ro'yxati (bot orqali qo'shiladi)
ADMIN_IDS = [
    # Bu ro'yxatga /addadmin buyrug'i orqali qo'shiladi
]

# ───────────── Default Sozlamalar ─────────────
DEFAULT_SETTINGS = {
    # ═══ QOROVUL (GUARD) ═══
    # Anti-spam
    "anti_spam": True,
    "spam_message_limit": 5,          # X ta xabar ...
    "spam_time_window": 10,           # ... Y soniya ichida = spam
    "spam_action": "mute",            # "mute" yoki "ban"
    "mute_duration_minutes": 15,      # Mute davomiyligi (daqiqa)

    # Link himoyasi
    "anti_link": True,
    "allowed_domains": ["t.me", "telegram.me"],

    # Forward himoyasi
    "anti_forward": True,

    # Bad words filtri
    "bad_words_filter": True,

    # Captcha — yangi a'zo tekshiruvi
    "captcha_enabled": True,
    "captcha_timeout": 120,

    # Tungi rejim
    "night_mode": False,
    "night_start_hour": 23,
    "night_end_hour": 6,

    # Warn tizimi
    "max_warns": 3,

    # Sticker/GIF limiti
    "anti_sticker_spam": True,
    "sticker_limit": 3,
    "sticker_time_window": 30,

    # Arab/maxsus belgilar himoyasi
    "anti_arabic": False,

    # Yangi a'zolar media cheklovi
    "new_member_media_restrict": True,
    "new_member_restrict_hours": 24,

    # ═══ REKLAMA TOZALASH (AD CLEANER) ═══
    "anti_ad": True,                   # Reklama himoyasi umumiy
    "anti_channel_username": True,     # @kanal_nomi bloklash
    "anti_bot_username": True,         # @bot_nomi bloklash
    "anti_inline_buttons": True,       # Reklama inline tugmalarni bloklash
    "anti_contact_spam": True,         # Kontakt spam bloklash
    "anti_location_spam": True,        # Joylashuv spam bloklash
    "anti_long_forward": True,         # Katta hajmli forward
    "long_forward_limit": 3,          # X ta forward = spam
    "long_forward_window": 60,        # ... Y soniya ichida
    "anti_ad_patterns": True,          # Reklama pattern aniqlash
    "anti_channel_bot": True,          # Kanaldan xabar yuboruvchi botlar

    # ═══ SANOQCHI (COUNTER) ═══
    "counter_enabled": True,           # Xabar sanoqchisi
    "top_users_count": 10,             # Top foydalanuvchilar soni
}

# ───────────── Reklama Patternlari ─────────────
AD_PATTERNS = [
    # O'zbek tilidagi reklama
    r"(?i)reklama\s*(uchun|narx|bepul|arzon|chegirma)",
    r"(?i)(sotiladi|sotaman|sotamiz|sotiladigan)",
    r"(?i)(pul\s*ishla|daromad|oylik\s*maosh)",
    r"(?i)(qo'shimcha\s*daromad|ish\s*taklif)",
    r"(?i)(kanalga\s*obuna|kanalimizga\s*a'zo)",
    r"(?i)(botimizga\s*start|botga\s*start)",
    r"(?i)(chegirma|aksiya|maxsus\s*taklif)",

    # Rus tilidagi reklama
    r"(?i)(заработ|доход|реклам|продаж|скидк)",
    r"(?i)(подписыва|канал\s*подпис)",

    # Ingliz tilidagi reklama
    r"(?i)(earn\s*money|make\s*money|free\s*bitcoin)",
    r"(?i)(join\s*(my|our)\s*(channel|group))",
    r"(?i)(subscribe\s*(to|my|our))",
    r"(?i)(click\s*(here|link|below))",
    r"(?i)(limited\s*offer|act\s*now|hurry\s*up)",
    r"(?i)(crypto|nft|airdrop|giveaway)\s*(free|earn|win)",
    r"(?i)(dm\s*me|inbox\s*me|message\s*me)\s*(for|to)",

    # Shortlink / spam URL
    r"(?i)(?:bit\.ly|tinyurl|goo\.gl|t\.co|short\.link|cutt\.ly|rb\.gy)/",
]

# ───────────── Xabarlar (O'zbek tilida) ─────────────
MESSAGES = {
    "welcome": (
        "👋 Salom, <b>{name}</b>!\n\n"
        "Guruhga xush kelibsiz! Siz haqiqiy odam ekanligingizni tasdiqlash uchun "
        "quyidagi savolga javob bering:\n\n"
        "🧮 <b>{question}</b> = ?\n\n"
        "⏳ Javob berish uchun {timeout} soniya vaqtingiz bor."
    ),
    "captcha_success": "✅ <b>{name}</b>, tekshiruvdan muvaffaqiyatli o'tdingiz! Yoqimli suhbat!",
    "captcha_fail": "❌ <b>{name}</b>, vaqt tugadi. Siz guruhdan chiqarildingiz. Qayta qo'shilishingiz mumkin.",
    "captcha_wrong": "❌ Noto'g'ri javob! Qaytadan urinib ko'ring.",

    "spam_warn": "⚠️ <b>{name}</b>, spam qilmang! Ogohlantirish berildi.",
    "spam_muted": "🔇 <b>{name}</b> spam tufayli {duration} daqiqaga ovozi o'chirildi.",
    "spam_banned": "🚫 <b>{name}</b> spam tufayli guruhdan chiqarildi.",

    "link_deleted": "🔗 <b>{name}</b>, guruhda tashqi havolalar taqiqlangan!",
    "forward_deleted": "🔄 <b>{name}</b>, boshqa kanallardan forward qilish taqiqlangan!",
    "bad_word_deleted": "🤬 <b>{name}</b>, nojo'ya so'z ishlatish taqiqlangan!",

    "warn_given": "⚠️ <b>{name}</b> ga ogohlantirish berildi. ({count}/{max})\nSabab: {reason}",
    "warn_ban": "🚫 <b>{name}</b> {max} ta ogohlantirishdan so'ng guruhdan chiqarildi!",

    "muted": "🔇 <b>{name}</b> ning ovozi {duration} daqiqaga o'chirildi.",
    "unmuted": "🔊 <b>{name}</b> ning ovozi yoqildi.",
    "banned": "🚫 <b>{name}</b> guruhdan chiqarildi.",
    "unbanned": "✅ <b>{name}</b> ning bloki olib tashlandi.",
    "kicked": "👢 <b>{name}</b> guruhdan chiqarildi (qayta qo'shilishi mumkin).",

    "night_mode_on": "🌙 Tungi rejim yoqildi. Faqat adminlar yoza oladi.",
    "night_mode_off": "☀️ Tungi rejim o'chirildi. Barcha a'zolar yoza oladi.",

    "not_admin": "❌ Siz admin emassiz!",
    "bot_not_admin": "❌ Bot admin emas! Botni guruh admini qiling.",
    "no_reply": "❌ Bu buyruqni foydalanuvchi xabariga javob (reply) sifatida yuboring.",
    "cant_restrict_admin": "❌ Adminni cheklash mumkin emas!",

    "sticker_spam": "🎭 <b>{name}</b>, sticker spam qilmang!",
    "night_restricted": "🌙 Tungi rejim yoqilgan. Hozir faqat adminlar yoza oladi.",

    # Reklama tozalash xabarlari
    "ad_deleted": "📢 <b>{name}</b>, guruhda reklama qilish taqiqlangan!",
    "channel_username_deleted": "📢 <b>{name}</b>, kanal/bot usernamelari taqiqlangan!",
    "contact_spam_deleted": "📇 <b>{name}</b>, kontakt spam taqiqlangan!",
    "inline_ad_deleted": "🔘 <b>{name}</b>, reklama tugmalari taqiqlangan!",
    "forward_spam_deleted": "🔄 <b>{name}</b>, ko'p forward qilish taqiqlangan!",
    "ad_pattern_deleted": "📢 <b>{name}</b>, reklama matni aniqlandi va o'chirildi!",
}
