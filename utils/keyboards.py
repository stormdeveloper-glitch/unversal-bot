"""
⌨️ KEYBOARDS — Barcha inline klaviaturalar bir joyda
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def settings_keyboard(chat_id: int, settings: dict) -> InlineKeyboardMarkup:
    """Sozlamalar paneli inline klaviaturasi."""
    def btn(label: str, key: str) -> InlineKeyboardButton:
        icon = "✅" if settings.get(key) else "❌"
        return InlineKeyboardButton(f"{icon} {label}", callback_data=f"toggle_{key}")

    return InlineKeyboardMarkup([
        [btn("Anti-Spam",    "anti_spam"),      btn("Anti-Link",    "anti_link")],
        [btn("Anti-Forward", "anti_forward"),   btn("So'z filtri",  "bad_words_filter")],
        [btn("Anti-Sticker", "anti_sticker_spam"), btn("Anti-Arab", "anti_arabic")],
        [btn("Anti-Reklama", "anti_ad"),        btn("Sanoqchi",     "counter_enabled")],
        [btn("Anti-@kanal",  "anti_channel_username"), btn("Anti-Pattern", "anti_ad_patterns")],
        [btn("Yangi a'zo Media", "new_member_media_restrict")],
        [btn("🌙 Tungi Rejim", "night_mode")],
        [InlineKeyboardButton("🔒 Yopish", callback_data="settings_close")],
    ])


def confirm_keyboard(action: str, target_id: int) -> InlineKeyboardMarkup:
    """Tasdiqlash so'rovi klaviaturasi (ban, del kabi xavfli amallar uchun)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha",  callback_data=f"confirm_{action}_{target_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data="cancel_action"),
    ]])


def start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Start xabari uchun klaviatura."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Web Ilova",
                              web_app=WebAppInfo(url="https://unversal-qorovul-bot.netlify.app"))],
        [InlineKeyboardButton("➕ Guruhga Qo'shish",
                              url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("📋 Buyruqlar", callback_data="show_menu")],
    ])


def admin_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Foydalanuvchi ustida tezkor admin amallar."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ Warn",  callback_data=f"quick_warn_{user_id}"),
            InlineKeyboardButton("🔇 Mute",  callback_data=f"quick_mute_{user_id}"),
        ],
        [
            InlineKeyboardButton("👢 Kick",  callback_data=f"quick_kick_{user_id}"),
            InlineKeyboardButton("🚫 Ban",   callback_data=f"quick_ban_{user_id}"),
        ],
    ])


def top_nav_keyboard(page: int, total_pages: int, kind: str) -> InlineKeyboardMarkup:
    """Top ro'yxati sahifalash tugmalari."""
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("◀️", callback_data=f"top_{kind}_{page-1}"))
    buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("▶️", callback_data=f"top_{kind}_{page+1}"))
    return InlineKeyboardMarkup([buttons])
