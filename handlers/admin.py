"""
👮 ADMIN — Moderatsiya buyruqlari
warn, mute, unmute, ban, unban, kick, tempban, addadmin, removeadmin, admins
"""
import logging
from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions, Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS, MESSAGES, OWNER_IDS
from utils.decorators import admin_only, handle_errors, requires_reply
from utils.helpers import (
    add_log, get_name, get_settings, is_admin, user_warns,
    parse_duration, fmt_duration,
)
from utils.keyboards import admin_actions_keyboard, confirm_keyboard

logger = logging.getLogger(__name__)

# ── Shared save reference (set from bot.py) ───
_save_fn = None

def set_save(fn):
    global _save_fn
    _save_fn = fn

def _save():
    if _save_fn:
        _save_fn()


# ── WARN ──────────────────────────────────────
@handle_errors
@admin_only
@requires_reply
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchiga ogohlantirish berish."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user

    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    reason  = " ".join(context.args) if context.args else "Sabab ko'rsatilmagan"
    s       = get_settings(chat_id)
    user_warns[chat_id][target.id] += 1
    count   = user_warns[chat_id][target.id]
    name    = get_name(target)
    _save()

    if count >= s["max_warns"]:
        await context.bot.ban_chat_member(chat_id, target.id)
        user_warns[chat_id][target.id] = 0
        _save()
        await update.message.reply_text(
            MESSAGES["warn_ban"].format(name=name, max=s["max_warns"]),
            parse_mode=ParseMode.HTML,
        )
        add_log(chat_id, "WARN_BAN", name, get_name(update.effective_user), reason)
    else:
        await update.message.reply_text(
            MESSAGES["warn_given"].format(
                name=name, count=count, max=s["max_warns"], reason=reason
            ),
            parse_mode=ParseMode.HTML,
        )
        add_log(chat_id, "WARN", name, get_name(update.effective_user), reason)


@handle_errors
@requires_reply
async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ogohlantirish sonini ko'rish."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    count   = user_warns[chat_id].get(target.id, 0)
    s       = get_settings(chat_id)

    bar = "▓" * count + "░" * (s["max_warns"] - count)
    text = (
        f"⚠️ <b>{get_name(target)}</b> ning ogohlantirishlari\n\n"
        f"<code>{bar}</code>  <b>{count}/{s['max_warns']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
@requires_reply
async def cmd_clearwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ogohlantirishlarni tozalash."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    name    = get_name(target)

    user_warns[chat_id][target.id] = 0
    _save()
    await update.message.reply_text(
        f"✅ <b>{name}</b> ning barcha ogohlantirishlari tozalandi.",
        parse_mode=ParseMode.HTML,
    )
    add_log(chat_id, "WARNS_CLEAR", name, get_name(update.effective_user))


# ── MUTE / UNMUTE ─────────────────────────────
@handle_errors
@admin_only
@requires_reply
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini mute qilish."""
    chat_id  = update.effective_chat.id
    target   = update.message.reply_to_message.from_user

    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    duration = int(context.args[0]) if context.args else get_settings(chat_id)["mute_duration_minutes"]
    until    = datetime.now(timezone.utc) + timedelta(minutes=duration)
    name     = get_name(target)

    await context.bot.restrict_chat_member(
        chat_id, target.id, ChatPermissions(can_send_messages=False), until_date=until
    )
    await update.message.reply_text(
        MESSAGES["muted"].format(name=name, duration=duration), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "MUTE", name, get_name(update.effective_user), f"{duration} daqiqa")


@handle_errors
@admin_only
@requires_reply
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini unmute qilish."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    name    = get_name(target)

    await context.bot.restrict_chat_member(
        chat_id, target.id,
        ChatPermissions(
            can_send_messages=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_send_polls=True, can_invite_users=True,
        ),
    )
    await update.message.reply_text(
        MESSAGES["unmuted"].format(name=name), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "UNMUTE", name, get_name(update.effective_user))


# ── BAN / UNBAN / KICK ────────────────────────
@handle_errors
@admin_only
@requires_reply
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Doimiy ban."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user

    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    name   = get_name(target)
    reason = " ".join(context.args) if context.args else ""

    await context.bot.ban_chat_member(chat_id, target.id)
    await update.message.reply_text(
        MESSAGES["banned"].format(name=name), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "BAN", name, get_name(update.effective_user), reason)


@handle_errors
@admin_only
@requires_reply
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Banni olib tashlash."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    name    = get_name(target)

    await context.bot.unban_chat_member(chat_id, target.id)
    await update.message.reply_text(
        MESSAGES["unbanned"].format(name=name), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "UNBAN", name, get_name(update.effective_user))


@handle_errors
@admin_only
@requires_reply
async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiqarish (qayta kirishi mumkin)."""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user

    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    name = get_name(target)
    await context.bot.ban_chat_member(chat_id, target.id)
    await context.bot.unban_chat_member(chat_id, target.id)
    await update.message.reply_text(
        MESSAGES["kicked"].format(name=name), parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "KICK", name, get_name(update.effective_user))


# ── TEMPBAN ───────────────────────────────────
@handle_errors
@admin_only
@requires_reply
async def cmd_tempban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vaqtinchalik ban. /tempban 30m | 2h | 1d [sabab]"""
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user

    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    args          = context.args or []
    duration_sec  = 3600
    reason        = "Sabab ko'rsatilmagan"

    if args:
        parsed = parse_duration(args[0])
        if parsed:
            duration_sec = parsed
            reason = " ".join(args[1:]) if len(args) > 1 else reason
        else:
            reason = " ".join(args)

    name    = get_name(target)
    until   = datetime.now(timezone.utc) + timedelta(seconds=duration_sec)
    dur_str = fmt_duration(duration_sec)

    await context.bot.ban_chat_member(chat_id, target.id, until_date=until)
    text = (
        f"⏱ <b>{name}</b> — <b>{dur_str}</b> muddatga ban!\n"
        f"📝 Sabab: {reason}\n"
        f"🕐 Tugaydi: <b>{until.strftime('%d.%m.%Y %H:%M')} UTC</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    add_log(chat_id, "TEMPBAN", name, get_name(update.effective_user), f"{dur_str} | {reason}")


# ── ADMIN BOSHQARUVI ──────────────────────────
@handle_errors
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin qo'shish."""
    caller_id = update.effective_user.id
    if caller_id not in OWNER_IDS and caller_id not in ADMIN_IDS:
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    target_id   = None
    target_name = None

    if update.message.reply_to_message:
        target_id   = update.message.reply_to_message.from_user.id
        target_name = get_name(update.message.reply_to_message.from_user)
    elif context.args:
        try:
            target_id   = int(context.args[0])
            target_name = str(target_id)
        except ValueError:
            await update.message.reply_text("❌ /addadmin <ID> yoki reply qiling.")
            return
    else:
        await update.message.reply_text("❌ /addadmin <ID> yoki reply qiling.")
        return

    if target_id in ADMIN_IDS:
        await update.message.reply_text(
            f"ℹ️ <b>{target_name}</b> allaqachon admin.", parse_mode=ParseMode.HTML
        )
        return

    ADMIN_IDS.append(target_id)
    _save()
    await update.message.reply_text(
        f"✅ <b>{target_name}</b> (<code>{target_id}</code>) admin qilindi!\n"
        f"👑 Jami adminlar: <b>{len(ADMIN_IDS)}</b>",
        parse_mode=ParseMode.HTML,
    )
    add_log(update.effective_chat.id, "ADD_ADMIN", target_name, get_name(update.effective_user))


@handle_errors
async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminni olib tashlash."""
    caller_id = update.effective_user.id
    if caller_id not in OWNER_IDS and caller_id not in ADMIN_IDS:
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    target_id   = None
    target_name = None

    if update.message.reply_to_message:
        target_id   = update.message.reply_to_message.from_user.id
        target_name = get_name(update.message.reply_to_message.from_user)
    elif context.args:
        try:
            target_id   = int(context.args[0])
            target_name = str(target_id)
        except ValueError:
            await update.message.reply_text("❌ /removeadmin <ID> yoki reply qiling.")
            return
    else:
        await update.message.reply_text("❌ /removeadmin <ID> yoki reply qiling.")
        return

    if target_id == caller_id:
        await update.message.reply_text("❌ O'zingizni olib tashlay olmaysiz!")
        return

    if target_id not in ADMIN_IDS:
        await update.message.reply_text(
            f"❌ <b>{target_name}</b> admin emas.", parse_mode=ParseMode.HTML
        )
        return

    ADMIN_IDS.remove(target_id)
    _save()
    await update.message.reply_text(
        f"✅ <b>{target_name}</b> (<code>{target_id}</code>) admin ro'yxatidan olib tashlandi.",
        parse_mode=ParseMode.HTML,
    )
    add_log(update.effective_chat.id, "REMOVE_ADMIN", target_name, get_name(update.effective_user))


@handle_errors
async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ro'yxatini ko'rsatish."""
    if not ADMIN_IDS:
        await update.message.reply_text("ℹ️ Hozircha tayinlangan admin yo'q.")
        return

    lines = ["👑 <b>Bot adminlari:</b>\n"]
    for i, aid in enumerate(ADMIN_IDS, 1):
        if aid in OWNER_IDS:
            continue
        try:
            m    = await context.bot.get_chat(aid)
            name = m.first_name or m.username or str(aid)
        except Exception:
            name = str(aid)
        lines.append(f"  {i}. <b>{name}</b> — <code>{aid}</code>")

    lines.append(f"\n📊 Jami: <b>{len(ADMIN_IDS)}</b> admin")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ── BAD WORDS BOSHQARUVI ──────────────────────
@handle_errors
@admin_only
async def cmd_addword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.guard import bad_words_list, save_bad_words, bad_patterns as bp
    if not context.args:
        await update.message.reply_text("❌ /addword <so'z>")
        return
    word = " ".join(context.args).lower()
    if word not in bad_words_list:
        bad_words_list.append(word)
        save_bad_words(bad_words_list, bp)
        await update.message.reply_text(
            f"✅ <b>'{word}'</b> taqiqlangan so'zlar ro'yxatiga qo'shildi.", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"ℹ️ <b>'{word}'</b> allaqachon ro'yxatda.", parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
async def cmd_delword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.guard import bad_words_list, save_bad_words, bad_patterns as bp
    if not context.args:
        await update.message.reply_text("❌ /delword <so'z>")
        return
    word = " ".join(context.args).lower()
    if word in bad_words_list:
        bad_words_list.remove(word)
        save_bad_words(bad_words_list, bp)
        await update.message.reply_text(
            f"✅ <b>'{word}'</b> ro'yxatdan o'chirildi.", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"❌ <b>'{word}'</b> topilmadi.", parse_mode=ParseMode.HTML)
