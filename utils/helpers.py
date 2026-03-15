"""
🛠️ HELPERS — Umumiy yordamchi funksiyalar
"""
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from config import OWNER_IDS, ADMIN_IDS

logger = logging.getLogger(__name__)

# ── In-memory state ────────────────────────────
group_settings:      dict[int, dict]                = {}
user_warns:          dict[int, dict[int, int]]      = defaultdict(lambda: defaultdict(int))
action_logs:         dict[int, list]                = defaultdict(list)
new_member_times:    dict[int, dict[int, float]]    = defaultdict(dict)
pending_captcha:     dict[int, dict]                = defaultdict(dict)
welcome_messages:    dict[int, str]                 = {}
group_rules:         dict[int, str]                 = {}
message_timestamps:  dict[int, dict[int, list]]     = defaultdict(lambda: defaultdict(list))
sticker_timestamps:  dict[int, dict[int, list]]     = defaultdict(lambda: defaultdict(list))


def get_name(user) -> str:
    """Foydalanuvchi to'liq ismini olish."""
    if user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or "Foydalanuvchi"


def fmt_duration(seconds: int) -> str:
    """Soniyani o'qilishi oson formatga o'tkazish."""
    if seconds < 3600:
        return f"{seconds // 60} daqiqa"
    if seconds < 86400:
        return f"{seconds // 3600} soat"
    return f"{seconds // 86400} kun"


def parse_duration(text: str) -> Optional[int]:
    """'30m', '2h', '1d' → soniya. Noto'g'ri format → None."""
    import re
    m = re.match(r"^(\d+)([mhd])$", text.strip().lower())
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2)
    return val * {"m": 60, "h": 3600, "d": 86400}[unit]


def add_log(chat_id: int, action: str,
            user_name: str, admin_name: str = "", reason: str = "") -> None:
    """Harakat logini yozish (oxirgi 200 ta saqlanadi)."""
    action_logs[chat_id].append({
        "action": action,
        "user":   user_name,
        "admin":  admin_name,
        "reason": reason,
        "time":   datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
    })
    if len(action_logs[chat_id]) > 200:
        action_logs[chat_id] = action_logs[chat_id][-200:]


async def is_admin(update: Update,
                   context: ContextTypes.DEFAULT_TYPE,
                   user_id: int = None) -> bool:
    """Foydalanuvchi admin yoki yo'qligini tekshirish."""
    uid = user_id or update.effective_user.id
    if uid in OWNER_IDS or uid in ADMIN_IDS:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def is_bot_admin(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Bot admin yoki yo'qligini tekshirish."""
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        return m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


def get_settings(chat_id: int) -> dict:
    """Guruh sozlamalarini olish (default qiymatlar bilan)."""
    from config import DEFAULT_SETTINGS
    if chat_id not in group_settings:
        group_settings[chat_id] = DEFAULT_SETTINGS.copy()
    return group_settings[chat_id]

