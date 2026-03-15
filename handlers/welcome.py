"""
🏠 WELCOME — Xush kelibsiz, qoidalar, pin, sozlamalar, tungi rejim
"""
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MESSAGES
from counter import register_member
from utils.decorators import admin_only, group_only, handle_errors, requires_reply
from utils.helpers import (
    action_logs, add_log, get_name, get_settings, is_admin, is_bot_admin,
    new_member_times, welcome_messages, group_rules, user_warns,
)
from utils.keyboards import settings_keyboard
from handlers.guard import apply_night_mode

import time

logger = logging.getLogger(__name__)

_save_fn = None
def set_save(fn):
    global _save_fn
    _save_fn = fn

def _save():
    if _save_fn:
        _save_fn()


# ── YANGI A'ZO ────────────────────────────────
async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi a'zo qo'shilganda kutib olish."""
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        # Vaqtni saqlash (media cheklovi uchun)
        new_member_times[chat_id][member.id] = time.time()
        # Sanoqchi uchun join sanasini ro'yxatdan o'tkazish
        register_member(chat_id, member.id)
        # Xush kelibsiz xabar
        custom = welcome_messages.get(chat_id)
        if custom:
            text = custom.replace("{name}", f"<b>{get_name(member)}</b>")
        else:
            text = f"👋 Salom, <b>{get_name(member)}</b>! Guruhga xush kelibsiz 🎉"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ── XUSH KELIBSIZ XABAR ───────────────────────
@handle_errors
@group_only
@admin_only
async def cmd_setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setwelcome <matn> — {name} a'zo ismi o'rniga."""
    if not context.args:
        await update.message.reply_text(
            "❌ Foydalanish:\n<code>/setwelcome Salom {name}! Xush kelibsiz 🎉</code>\n\n"
            "💡 <code>{name}</code> — a'zo ismi o'rniga qo'yiladi.",
            parse_mode=ParseMode.HTML,
        )
        return
    text = " ".join(context.args)
    welcome_messages[update.effective_chat.id] = text
    _save()
    preview = text.replace("{name}", "<b>Abdulloh Karimov</b>")
    await update.message.reply_text(
        f"✅ Xush kelibsiz xabar o'rnatildi!\n\n📋 <b>Ko'rinishi:</b>\n\n{preview}",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@admin_only
async def cmd_getwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = welcome_messages.get(update.effective_chat.id)
    if text:
        await update.message.reply_text(
            f"📋 <b>Xush kelibsiz xabar:</b>\n\n{text}", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "ℹ️ Maxsus xabar yo'q. Standart ishlatiladi.\n👉 /setwelcome <matn>"
        )


@handle_errors
@admin_only
async def cmd_delwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_messages.pop(update.effective_chat.id, None)
    _save()
    await update.message.reply_text("✅ Xush kelibsiz xabar o'chirildi. Standart ishlatiladi.")


# ── GURUH QOIDALARI ───────────────────────────
@handle_errors
@group_only
async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = group_rules.get(update.effective_chat.id)
    if rules:
        await update.message.reply_text(
            f"📜 <b>Guruh Qoidalari</b>\n{'━'*22}\n\n{rules}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "ℹ️ Guruh qoidalari o'rnatilmagan.\n👉 Admin: /setrules <matn>"
        )


@handle_errors
@group_only
@admin_only
async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Foydalanish:\n<code>/setrules 1. Hurmat 2. Spam yo'q</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    rules_text = " ".join(context.args)
    group_rules[update.effective_chat.id] = rules_text
    _save()
    await update.message.reply_text(
        f"✅ Guruh qoidalari o'rnatildi!\n\n📜 <b>Qoidalar:</b>\n{rules_text}",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@admin_only
async def cmd_delrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_rules.pop(update.effective_chat.id, None)
    _save()
    await update.message.reply_text("✅ Guruh qoidalari o'chirildi.")


# ── PIN / UNPIN ───────────────────────────────
@handle_errors
@admin_only
@requires_reply
async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pin — xabarni pin qilish. /pin silent — jimgina."""
    chat_id = update.effective_chat.id
    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return
    loud = not (context.args and context.args[0].lower() in ("silent", "jim"))
    await context.bot.pin_chat_message(
        chat_id, update.message.reply_to_message.message_id,
        disable_notification=not loud,
    )
    mode = "🔔 Barcha xabardor qilindi." if loud else "🔕 Jimgina pin qilindi."
    await update.message.reply_text(f"📌 Xabar pin qilindi. {mode}")
    add_log(chat_id, "PIN", "—", get_name(update.effective_user))


@handle_errors
@admin_only
async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return
    if update.message.reply_to_message:
        await context.bot.unpin_chat_message(chat_id, update.message.reply_to_message.message_id)
    else:
        await context.bot.unpin_chat_message(chat_id)
    await update.message.reply_text("📌 Pin olib tashlandi.")
    add_log(chat_id, "UNPIN", "—", get_name(update.effective_user))


@handle_errors
@admin_only
async def cmd_unpinall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return
    await context.bot.unpin_all_chat_messages(chat_id)
    await update.message.reply_text("📌 Barcha pinlar olib tashlandi.")
    add_log(chat_id, "UNPIN_ALL", "—", get_name(update.effective_user))


# ── SOZLAMALAR ────────────────────────────────
@handle_errors
@admin_only
async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚙️ Bu buyruq faqat guruhlarda ishlaydi.")
        return
    s = get_settings(chat_id)
    text = (
        "⚙️ <b>Bot Sozlamalari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 Spam limiti: <b>{s['spam_message_limit']}</b> xabar / "
        f"<b>{s['spam_time_window']}</b> son.\n"
        f"🔹 Mute davomiyligi: <b>{s['mute_duration_minutes']}</b> daqiqa\n"
        f"🔹 Max ogohlantirish: <b>{s['max_warns']}</b>\n"
        f"🔹 Tungi rejim: <b>{s['night_start_hour']}:00 — {s['night_end_hour']}:00</b>\n\n"
        "Tugmalarni bosib sozlamalarni o'zgartiring:"
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(chat_id, s),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sozlamalar tugmalarini boshqarish."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    data    = query.data

    if data == "settings_close":
        await query.message.delete()
        return

    if data == "noop":
        return

    if not await is_admin(update, context, query.from_user.id):
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    if data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        s   = get_settings(chat_id)
        if key in s:
            s[key]  = not s[key]
            state   = "yoqildi ✅" if s[key] else "o'chirildi ❌"
            await query.answer(f"{key}: {state}")
            if key == "night_mode":
                await apply_night_mode(context, chat_id, s[key])
            # Klaviaturani yangilash
            try:
                await query.message.edit_reply_markup(
                    reply_markup=settings_keyboard(chat_id, s)
                )
            except Exception:
                pass


@handle_errors
@admin_only
async def cmd_nightmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)
    s["night_mode"] = not s["night_mode"]
    await apply_night_mode(context, chat_id, s["night_mode"])
