"""
📢 REKLAMA TOZALASH (AD CLEANER) MODULI
Kanal, bot, inline tugma, kontakt, pattern aniqlash
"""
import re
import time
from collections import defaultdict
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from config import AD_PATTERNS, MESSAGES

# Forward spam kuzatuvi: { chat_id: { user_id: [timestamps] } }
forward_timestamps: dict[int, dict[int, list]] = defaultdict(lambda: defaultdict(list))

# Kanal/bot username pattern
CHANNEL_USERNAME_PATTERN = re.compile(r"@[a-zA-Z][a-zA-Z0-9_]{3,30}")
BOT_USERNAME_PATTERN = re.compile(r"@[a-zA-Z][a-zA-Z0-9_]*[Bb][Oo][Tt]\b")

# Compiled ad patterns
_compiled_ad_patterns = [re.compile(p) for p in AD_PATTERNS]


async def check_ad_comprehensive(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: dict, add_log_func, get_name_func) -> bool:
    """Kompleks reklama tekshiruvi. True = reklama aniqlandi."""
    if not settings.get("anti_ad"):
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    msg = update.message
    name = get_name_func(update.effective_user)

    # 1. Kanal username tekshiruvi (@channel_name)
    if settings.get("anti_channel_username"):
        text = msg.text or msg.caption or ""
        # Bot usernameni alohida tekshirish
        if settings.get("anti_bot_username"):
            bot_matches = BOT_USERNAME_PATTERN.findall(text)
            bot_self = f"@{context.bot.username}".lower() if context.bot.username else ""
            for m in bot_matches:
                if m.lower() != bot_self:
                    try: await msg.delete()
                    except: pass
                    await context.bot.send_message(chat_id, MESSAGES["channel_username_deleted"].format(name=name), parse_mode=ParseMode.HTML)
                    add_log_func(chat_id, "BOT_USERNAME", name, "Bot")
                    return True

        # Kanal username
        ch_matches = CHANNEL_USERNAME_PATTERN.findall(text)
        bot_self = f"@{context.bot.username}".lower() if context.bot.username else ""
        for m in ch_matches:
            if m.lower() == bot_self:
                continue
            # O'z guruh usernamelari bo'lsa ruxsat
            try:
                chat = update.effective_chat
                if chat.username and m.lower() == f"@{chat.username}".lower():
                    continue
            except: pass
            try: await msg.delete()
            except: pass
            await context.bot.send_message(chat_id, MESSAGES["channel_username_deleted"].format(name=name), parse_mode=ParseMode.HTML)
            add_log_func(chat_id, "CHANNEL_USERNAME", name, "Bot")
            return True

    # 2. Inline tugmalar tekshiruvi (reklama)
    if settings.get("anti_inline_buttons") and msg.reply_markup:
        if hasattr(msg.reply_markup, "inline_keyboard") and msg.reply_markup.inline_keyboard:
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if btn.url:
                        try: await msg.delete()
                        except: pass
                        await context.bot.send_message(chat_id, MESSAGES["inline_ad_deleted"].format(name=name), parse_mode=ParseMode.HTML)
                        add_log_func(chat_id, "INLINE_AD", name, "Bot")
                        return True

    # 3. Kontakt spam
    if settings.get("anti_contact_spam") and msg.contact:
        if msg.contact.user_id != user_id:
            try: await msg.delete()
            except: pass
            await context.bot.send_message(chat_id, MESSAGES["contact_spam_deleted"].format(name=name), parse_mode=ParseMode.HTML)
            add_log_func(chat_id, "CONTACT_SPAM", name, "Bot")
            return True

    # 4. Joylashuv spam
    if settings.get("anti_location_spam") and (msg.location or msg.venue):
        try: await msg.delete()
        except: pass
        add_log_func(chat_id, "LOCATION_SPAM", name, "Bot")
        return True

    # 5. Ko'p forward tekshiruvi
    if settings.get("anti_long_forward"):
        if msg.forward_date or msg.forward_from or msg.forward_from_chat:
            now = time.time()
            forward_timestamps[chat_id][user_id].append(now)
            cutoff = now - settings.get("long_forward_window", 60)
            forward_timestamps[chat_id][user_id] = [t for t in forward_timestamps[chat_id][user_id] if t > cutoff]
            if len(forward_timestamps[chat_id][user_id]) > settings.get("long_forward_limit", 3):
                try: await msg.delete()
                except: pass
                await context.bot.send_message(chat_id, MESSAGES["forward_spam_deleted"].format(name=name), parse_mode=ParseMode.HTML)
                forward_timestamps[chat_id][user_id] = []
                add_log_func(chat_id, "FORWARD_SPAM", name, "Bot")
                return True

    # 6. Kanaldan yozuvchi bot tekshiruvi
    if settings.get("anti_channel_bot"):
        if msg.sender_chat and msg.sender_chat.id != chat_id:
            try: await msg.delete()
            except: pass
            add_log_func(chat_id, "CHANNEL_BOT", msg.sender_chat.title or "Kanal", "Bot")
            return True

    # 7. Reklama pattern tekshiruvi
    if settings.get("anti_ad_patterns"):
        text = (msg.text or msg.caption or "")
        if len(text) > 10:
            for pattern in _compiled_ad_patterns:
                if pattern.search(text):
                    try: await msg.delete()
                    except: pass
                    await context.bot.send_message(chat_id, MESSAGES["ad_pattern_deleted"].format(name=name), parse_mode=ParseMode.HTML)
                    add_log_func(chat_id, "AD_PATTERN", name, "Bot")
                    return True

    return False
