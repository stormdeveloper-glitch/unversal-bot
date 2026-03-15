"""
🔍 INFO — Foydalanuvchi ma'lumoti, log, statistika, reload
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import ContextTypes

from config import OWNER_IDS, ADMIN_IDS
from utils.decorators import admin_only, handle_errors
from utils.helpers import (
    action_logs, add_log, get_name, get_settings,
    is_admin, pending_captcha, user_warns,
)

logger = logging.getLogger(__name__)

# Lazy import to avoid circular
def _sanaydi():
    from handlers.sanaydi import sanaydi_data
    return sanaydi_data


@handle_errors
async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi haqida to'liq ma'lumot."""
    chat_id       = update.effective_chat.id
    target_user   = None
    target_member = None

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        try:
            target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        except Exception:
            pass
    elif context.args:
        arg = context.args[0]
        try:
            if arg.startswith("@"):
                obj = await context.bot.get_chat(arg)
                target_user = obj
                try:
                    target_member = await context.bot.get_chat_member(chat_id, obj.id)
                except Exception:
                    pass
            else:
                uid = int(arg)
                target_member = await context.bot.get_chat_member(chat_id, uid)
                target_user   = target_member.user
        except Exception as e:
            await update.message.reply_text(f"❌ Topilmadi: {e}")
            return
    else:
        target_user = update.effective_user
        try:
            target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        except Exception:
            pass

    if not target_user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    STATUS_MAP = {
        "creator":      "👑 Guruh egasi",
        "administrator":"⭐️ Admin",
        "member":       "👤 A'zo",
        "restricted":   "🔇 Cheklangan",
        "left":         "🚪 Chiqib ketgan",
        "kicked":       "🚫 Bloklangan",
    }
    status_str = "❓ Noma'lum"
    if target_member:
        status_str = STATUS_MAP.get(target_member.status, target_member.status)

    username_str = f"@{target_user.username}" if getattr(target_user, "username", None) else "—"
    warns_count  = user_warns[chat_id].get(target_user.id, 0)
    s            = get_settings(chat_id)
    sd           = _sanaydi()
    invited      = sd.get(chat_id, {}).get(target_user.id, {}).get("count", 0)
    lang         = getattr(target_user, "language_code", None) or "—"
    is_premium   = "💎 Ha" if getattr(target_user, "is_premium", False) else "—"
    is_bot_u     = "🤖 Ha" if getattr(target_user, "is_bot", False) else "Yo'q"
    full_name    = get_name(target_user)

    warn_bar = "▓" * warns_count + "░" * max(0, s["max_warns"] - warns_count)

    text = (
        f"👤 <b>Foydalanuvchi Ma'lumoti</b>\n"
        f"{'━'*22}\n"
        f"🪪 <b>Ism:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username_str}\n"
        f"🆔 <b>ID:</b> <code>{target_user.id}</code>\n"
        f"🤖 <b>Bot:</b> {is_bot_u} | 💎 <b>Premium:</b> {is_premium}\n"
        f"🌐 <b>Til:</b> {lang}\n"
        f"{'━'*22}\n"
        f"📌 <b>Status:</b> {status_str}\n"
        f"⚠️ <b>Ogohlantirish:</b> <code>{warn_bar}</code> {warns_count}/{s['max_warns']}\n"
        f"👥 <b>Qo'shgan:</b> {invited} odam\n"
        f"{'━'*22}\n"
        f"🔗 <a href='tg://user?id={target_user.id}'>Profilni ochish</a>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi 15 ta harakatni ko'rish."""
    chat_id = update.effective_chat.id
    logs    = action_logs.get(chat_id, [])

    if not logs:
        await update.message.reply_text("📋 Hozircha log yo'q.")
        return

    recent = logs[-15:]
    lines  = ["📋 <b>Oxirgi harakatlar:</b>\n"]
    for entry in reversed(recent):
        line = f"🔸 <b>{entry['action']}</b> — {entry['user']}"
        if entry.get("admin"):
            line += f" <i>(admin: {entry['admin']})</i>"
        if entry.get("reason"):
            line += f"\n    📝 {entry['reason']}"
        line += f"\n    🕐 {entry['time']}"
        lines.append(line)

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot va guruh statistikasi."""
    chat_id   = update.effective_chat.id
    logs      = action_logs.get(chat_id, [])
    s         = get_settings(chat_id)
    stat      = defaultdict(int)
    for entry in logs:
        stat[entry["action"]] += 1

    warns_total = sum(user_warns[chat_id].values())

    text = (
        f"📊 <b>Guruh Statistikasi</b>\n"
        f"{'━'*22}\n"
        f"📋 Jami loglar: <b>{len(logs)}</b>\n"
        f"🔇 Spam mute/ban: <b>{stat['SPAM_MUTE'] + stat['SPAM_BAN']}</b>\n"
        f"🔗 Link o'chirilgan: <b>{stat['LINK_DELETED']}</b>\n"
        f"🔄 Forward bloklangan: <b>{stat['FORWARD_DELETED']}</b>\n"
        f"🤬 Nojo'ya so'z: <b>{stat['BAD_WORD'] + stat['BAD_PATTERN']}</b>\n"
        f"⚠️ Ogohlantirish: <b>{stat['WARN']}</b>\n"
        f"🚫 Ban: <b>{stat['BAN'] + stat['WARN_BAN'] + stat['TEMPBAN']}</b>\n\n"
        f"⚠️ Aktiv ogohlantirish: <b>{warns_total}</b>\n\n"
        f"{'━'*22}\n"
        f"⚙️ Holat:\n"
        f"{'✅' if s['anti_spam'] else '❌'} Anti-Spam  "
        f"{'✅' if s['anti_link'] else '❌'} Anti-Link  "
        f"{'✅' if s['anti_ad'] else '❌'} Anti-Reklama\n"
        f"{'✅' if s['night_mode'] else '❌'} Tungi Rejim  "
        f"{'✅' if s['counter_enabled'] else '❌'} Sanoqchi"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh adminlarini qayta yuklash."""
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    chat_id = update.effective_chat.id
    admins  = await context.bot.get_chat_administrators(chat_id)
    lines   = ["👑 <b>Adminlar ro'yxati yangilandi!</b>\n"]
    count   = 0

    for i, admin in enumerate(admins, 1):
        if admin.user.is_bot:
            continue
        name = get_name(admin.user)
        icon = "👑" if admin.status == ChatMemberStatus.OWNER else "⭐️"
        lines.append(f"  {i}. {icon} <b>{name}</b> — <code>{admin.user.id}</code>")
        count += 1

    lines.append(f"\n📊 Jami: <b>{count}</b> admin")
    lines.append(f"🔄 Yangilandi: <b>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    add_log(chat_id, "RELOAD_ADMINS", "—", get_name(update.effective_user))
