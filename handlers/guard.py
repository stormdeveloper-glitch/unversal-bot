"""
🛡️ GUARD — Himoya filtrlari moduli
Spam, link, forward, bad words, arabic, sticker, night mode
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MESSAGES
from utils.helpers import (
    action_logs, add_log, get_name, get_settings,
    message_timestamps, new_member_times, sticker_timestamps,
)

logger = logging.getLogger(__name__)

# ── Bad words ──────────────────────────────────
_BAD_WORDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bad_words.json")


def load_bad_words() -> tuple[list, list]:
    try:
        with open(_BAD_WORDS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("words", []), d.get("patterns", [])
    except FileNotFoundError:
        return [], []


def save_bad_words(words: list, patterns: list) -> None:
    with open(_BAD_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"words": words, "patterns": patterns}, f, ensure_ascii=False, indent=4)


bad_words_list, bad_patterns = load_bad_words()

# ── Regex patternlar ───────────────────────────
_URL_RE = re.compile(
    r"(?:https?://|www\.)[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
    r"|(?:[a-zA-Z0-9\-]+\.)+(?:com|org|net|ru|uz|me|io|info|xyz|co|uk|de)",
    re.IGNORECASE,
)
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]{5,}")


async def _delete(msg) -> None:
    """Xabarni o'chirishga urinish (xatolikni yutib yuboradi)."""
    try:
        await msg.delete()
    except Exception:
        pass


async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Flood/spam tekshiruvi."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s.get("anti_spam"):
        return False

    now = time.time()
    ts = message_timestamps[chat_id][user_id]
    ts.append(now)
    cutoff = now - s["spam_time_window"]
    message_timestamps[chat_id][user_id] = [t for t in ts if t > cutoff]

    if len(message_timestamps[chat_id][user_id]) <= s["spam_message_limit"]:
        return False

    name     = get_name(update.effective_user)
    action   = s.get("spam_action", "mute")
    duration = s.get("mute_duration_minutes", 15)

    await _delete(update.message)
    message_timestamps[chat_id][user_id] = []

    if action == "ban":
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.send_message(
            chat_id, MESSAGES["spam_banned"].format(name=name), parse_mode=ParseMode.HTML
        )
        add_log(chat_id, "SPAM_BAN", name, "Bot")
    else:
        until = datetime.now(timezone.utc) + timedelta(minutes=duration)
        await context.bot.restrict_chat_member(
            chat_id, user_id, ChatPermissions(can_send_messages=False), until_date=until
        )
        await context.bot.send_message(
            chat_id, MESSAGES["spam_muted"].format(name=name, duration=duration),
            parse_mode=ParseMode.HTML
        )
        add_log(chat_id, "SPAM_MUTE", name, "Bot")
    return True


async def check_sticker_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sticker/GIF spam tekshiruvi."""
    if not (update.message.sticker or update.message.animation):
        return False
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s.get("anti_sticker_spam"):
        return False

    now = time.time()
    ts  = sticker_timestamps[chat_id][user_id]
    ts.append(now)
    cutoff = now - s["sticker_time_window"]
    sticker_timestamps[chat_id][user_id] = [t for t in ts if t > cutoff]

    if len(sticker_timestamps[chat_id][user_id]) <= s["sticker_limit"]:
        return False

    name = get_name(update.effective_user)
    await _delete(update.message)
    await context.bot.send_message(
        chat_id, MESSAGES["sticker_spam"].format(name=name), parse_mode=ParseMode.HTML
    )
    sticker_timestamps[chat_id][user_id] = []
    add_log(chat_id, "STICKER_SPAM", name, "Bot")
    return True


async def check_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Tashqi havola tekshiruvi."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["anti_link"]:
        return False

    text    = update.message.text or update.message.caption or ""
    matches = _URL_RE.findall(text)
    if not matches:
        return False

    allowed = s["allowed_domains"]
    for url in matches:
        if not any(d in url for d in allowed):
            await _delete(update.message)
            name = get_name(update.effective_user)
            await context.bot.send_message(
                chat_id, MESSAGES["link_deleted"].format(name=name), parse_mode=ParseMode.HTML
            )
            add_log(chat_id, "LINK_DELETED", name, "Bot")
            return True
    return False


async def check_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Forward xabar tekshiruvi."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["anti_forward"]:
        return False

    msg = update.message
    if not (msg.forward_date or msg.forward_from or msg.forward_from_chat):
        return False

    await _delete(msg)
    name = get_name(update.effective_user)
    await context.bot.send_message(
        chat_id, MESSAGES["forward_deleted"].format(name=name), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "FORWARD_DELETED", name, "Bot")
    return True


async def check_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Nojo'ya so'zlar tekshiruvi."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["bad_words_filter"]:
        return False

    text = (update.message.text or update.message.caption or "").lower()

    for word in bad_words_list:
        if word.lower() in text:
            await _delete(update.message)
            name = get_name(update.effective_user)
            await context.bot.send_message(
                chat_id, MESSAGES["bad_word_deleted"].format(name=name), parse_mode=ParseMode.HTML
            )
            add_log(chat_id, "BAD_WORD", name, "Bot", f"So'z: {word}")
            return True

    for pattern in bad_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            await _delete(update.message)
            name = get_name(update.effective_user)
            await context.bot.send_message(
                chat_id, MESSAGES["bad_word_deleted"].format(name=name), parse_mode=ParseMode.HTML
            )
            add_log(chat_id, "BAD_PATTERN", name, "Bot")
            return True

    return False


async def check_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Arab yozuvi tekshiruvi."""
    s = get_settings(update.effective_chat.id)
    if not s.get("anti_arabic"):
        return False
    text = update.message.text or ""
    if _ARABIC_RE.search(text):
        await _delete(update.message)
        return True
    return False


async def check_new_member_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Yangi a'zo media cheklovi."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s.get("new_member_media_restrict"):
        return False

    join_time = new_member_times.get(chat_id, {}).get(user_id)
    if not join_time:
        return False

    restrict_hours = s["new_member_restrict_hours"]
    if (time.time() - join_time) / 3600 > restrict_hours:
        return False

    msg = update.message
    if msg.photo or msg.video or msg.document or msg.voice or msg.video_note or msg.animation:
        await _delete(msg)
        name = get_name(update.effective_user)
        text = (
            f"🚫 <b>{name}</b>, yangi a'zolarga <b>{restrict_hours} soat</b> "
            f"davomida media yuborish taqiqlangan!"
        )
        await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        return True
    return False


async def check_night_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Tungi rejim tekshiruvi."""
    s = get_settings(update.effective_chat.id)
    if not s["night_mode"]:
        return False

    h = datetime.now().hour
    start, end = s["night_start_hour"], s["night_end_hour"]
    is_night = (h >= start or h < end) if start > end else (start <= h < end)

    if is_night:
        await _delete(update.message)
        return True
    return False


async def apply_night_mode(context: ContextTypes.DEFAULT_TYPE, chat_id: int, enable: bool) -> None:
    """Tungi rejimni chat permissionlariga qo'llash."""
    if enable:
        await context.bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
        await context.bot.send_message(chat_id, MESSAGES["night_mode_on"], parse_mode=ParseMode.HTML)
    else:
        await context.bot.set_chat_permissions(chat_id, ChatPermissions(
            can_send_messages=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True,
        ))
        await context.bot.send_message(chat_id, MESSAGES["night_mode_off"], parse_mode=ParseMode.HTML)
