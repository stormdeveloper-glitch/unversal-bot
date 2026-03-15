"""
👥 SANAYDI — Odam yig'ish (referral) moduli
"""
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import ContextTypes

from config import MESSAGES
from utils.decorators import admin_only, group_only, handle_errors, requires_reply
from utils.helpers import add_log, get_name, is_admin, is_bot_admin

logger = logging.getLogger(__name__)

# ── State ─────────────────────────────────────
sanaydi_guruh_mode:   dict[int, bool]        = defaultdict(bool)
sanaydi_kanal_mode:   dict[int, str]         = {}
sanaydi_data:         dict[int, dict]        = defaultdict(dict)
sanaydi_invite_links: dict[int, dict]        = defaultdict(dict)

_save_fn = None
def set_save(fn):
    global _save_fn
    _save_fn = fn
def _save():
    if _save_fn:
        _save_fn()


def get_data(chat_id: int, user_id: int, name: str) -> dict:
    if user_id not in sanaydi_data[chat_id]:
        sanaydi_data[chat_id][user_id] = {"name": name, "count": 0, "bal": 0}
    sanaydi_data[chat_id][user_id]["name"] = name
    return sanaydi_data[chat_id][user_id]


@handle_errors
@group_only
@admin_only
async def cmd_guruh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user    = update.effective_user
    name    = get_name(user)

    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return

    link_obj = await context.bot.create_chat_invite_link(
        chat_id=chat_id, name=f"Sanaydi_{user.id}", creates_join_request=False
    )
    invite_link = link_obj.invite_link
    sanaydi_invite_links[chat_id][invite_link] = user.id
    sanaydi_guruh_mode[chat_id] = True
    get_data(chat_id, user.id, name)

    await update.message.reply_text(
        f"✅ <b>Guruhga odam yig'ish yoqildi!</b>\n\n"
        f"👥 Ulashing:\n🔗 {invite_link}\n\n"
        f"📊 Havola orqali qo'shilganlar hisobingizga yoziladi!\n"
        f"📈 Natija: /meni",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@group_only
@admin_only
async def cmd_guruh_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sanaydi_guruh_mode[update.effective_chat.id] = False
    await update.message.reply_text("❌ <b>Guruhga odam yig'ish o'chirildi!</b>", parse_mode=ParseMode.HTML)


@handle_errors
@group_only
@admin_only
async def cmd_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Foydalanish: /kanal @kanalingiz")
        return

    chat_id        = update.effective_chat.id
    user           = update.effective_user
    kanal_username = context.args[0]
    if not kanal_username.startswith("@"):
        kanal_username = "@" + kanal_username

    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return

    kanal_chat = await context.bot.get_chat(kanal_username)
    link_obj   = await context.bot.create_chat_invite_link(
        chat_id=kanal_chat.id, name=f"Sanaydi_{user.id}", creates_join_request=False
    )
    invite_link = link_obj.invite_link
    sanaydi_invite_links[kanal_chat.id][invite_link] = user.id
    sanaydi_kanal_mode[chat_id] = kanal_username
    get_data(chat_id, user.id, get_name(user))

    await update.message.reply_text(
        f"✅ <b>Kanalga odam yig'ish yoqildi!</b>\n\n"
        f"📣 Kanal: <b>{kanal_username}</b>\n🔗 Havola:\n{invite_link}\n\n"
        f"📈 Natija: /meni",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@admin_only
async def cmd_kanal_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sanaydi_kanal_mode.pop(update.effective_chat.id, None)
    await update.message.reply_text("❌ <b>Kanalga odam yig'ish o'chirildi!</b>", parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
@requires_reply
async def cmd_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /bal <son>")
        return
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Son kiriting!")
        return

    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    name    = get_name(target)
    data    = get_data(chat_id, target.id, name)
    data["bal"]   += amount
    data["count"] += amount
    _save()

    await update.message.reply_text(
        f"🎁 <b>{name}</b> ga <b>+{amount}</b> bal!\n"
        f"📊 Jami: <b>{data['count']}</b> odam | 🎯 Bonus: <b>{data['bal']}</b>",
        parse_mode=ParseMode.HTML,
    )
    add_log(chat_id, "BAL_ADDED", name, get_name(update.effective_user), f"+{amount}")


@handle_errors
@group_only
async def cmd_meni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user    = update.effective_user
    data    = get_data(chat_id, user.id, get_name(user))
    kanal   = sanaydi_kanal_mode.get(chat_id, "—")
    guruh_s = "✅ Yoqiq" if sanaydi_guruh_mode.get(chat_id) else "❌ O'chiq"

    await update.message.reply_text(
        f"📊 <b>{get_name(user)}</b> ning statistikasi:\n\n"
        f"👥 Qo'shgan: <b>{data['count']}</b> odam\n"
        f"🎁 Bonus bal: <b>{data['bal']}</b>\n\n"
        f"⚙️ Guruh: {guruh_s} | 📣 Kanal: <b>{kanal}</b>",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@group_only
@requires_reply
async def cmd_sizni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    data    = get_data(chat_id, target.id, get_name(target))

    await update.message.reply_text(
        f"📈 <b>{get_name(target)}</b>:\n"
        f"👥 Qo'shgan: <b>{data['count']}</b> | 🎁 Bal: <b>{data['bal']}</b>",
        parse_mode=ParseMode.HTML,
    )


@handle_errors
@group_only
async def cmd_sanaydi_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    users   = sanaydi_data.get(chat_id, {})
    if not users:
        await update.message.reply_text("📊 Hozircha hech kim odam qo'shmagan.")
        return

    top = sorted(users.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"]
    lines  = ["🏆 <b>Eng ko'p odam qo'shganlar:</b>\n"]
    for i, (uid, d) in enumerate(top):
        if d["count"] == 0:
            continue
        medal    = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        bal_text = f" (+{d['bal']} bal)" if d["bal"] > 0 else ""
        lines.append(f"  {medal} {d['name']} — <b>{d['count']}</b>{bal_text}")

    if len(lines) == 1:
        await update.message.reply_text("📊 Hozircha hech kim odam qo'shmagan.")
        return

    total = sum(d["count"] for d in users.values())
    lines.append(f"\n📈 Jami: <b>{total}</b> odam")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@handle_errors
@admin_only
@requires_reply
async def cmd_nol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target  = update.message.reply_to_message.from_user
    name    = get_name(target)
    if target.id in sanaydi_data.get(chat_id, {}):
        sanaydi_data[chat_id][target.id].update({"count": 0, "bal": 0})
        _save()
    await update.message.reply_text(f"🪓 <b>{name}</b> — 0 ga tushirildi.", parse_mode=ParseMode.HTML)
    add_log(chat_id, "SANAYDI_NOL", name, get_name(update.effective_user))


@handle_errors
@admin_only
async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    count   = len(sanaydi_data.get(chat_id, {}))
    sanaydi_data[chat_id] = {}
    sanaydi_invite_links[chat_id] = {}
    _save()
    await update.message.reply_text(
        f"🗑 <b>{count}</b> ta foydalanuvchi ma'lumoti tozalandi.", parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "SANAYDI_DEL_ALL", "Hammasi", get_name(update.effective_user))


async def on_chat_member_sanaydi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi a'zo kim taklif qilganini aniqlash."""
    result     = update.chat_member
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    joined = (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, "kicked")
        and new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )
    if not joined:
        return

    chat_id  = result.chat.id
    new_user = result.new_chat_member.user
    if new_user.is_bot:
        return

    if result.invite_link:
        link_str   = result.invite_link.invite_link
        inviter_id = sanaydi_invite_links.get(chat_id, {}).get(link_str)
        if inviter_id:
            try:
                m            = await context.bot.get_chat_member(chat_id, inviter_id)
                inviter_name = get_name(m.user)
            except Exception:
                inviter_name = f"User{inviter_id}"
            data = get_data(chat_id, inviter_id, inviter_name)
            data["count"] += 1
            _save()
            logger.info(f"✅ {inviter_name} +1 odam (jami: {data['count']})")
        return

    if result.from_user and result.from_user.id != new_user.id:
        inviter = result.from_user
        if sanaydi_guruh_mode.get(chat_id):
            data = get_data(chat_id, inviter.id, get_name(inviter))
            data["count"] += 1
            _save()
            logger.info(f"✅ {get_name(inviter)} +1 odam (jami: {data['count']})")
