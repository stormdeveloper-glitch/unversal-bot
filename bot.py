"""
╔══════════════════════════════════════════════════════════════╗
║       🛡️  TELEGRAM UNIVERSAL BOT — QOROVUL BOT  🛡️         ║
║   Qorovul + Sanoqchi + Reklama Tozalagich — Har tomonlama   ║
╚══════════════════════════════════════════════════════════════╝

Arxitektura:
  bot.py              — asosiy ishga tushirish nuqtasi
  config.py           — sozlamalar va konstantalar
  data_manager.py     — JSON saqlash/yuklash
  ad_cleaner.py       — reklama tozalash
  counter.py          — xabar sanoqchisi
  handlers/
    admin.py          — warn/mute/ban/kick/tempban/addadmin
    guard.py          — spam/link/forward/badwords/arabic/sticker
    info.py           — info/reload/log/stats
    sanaydi.py        — odam yig'ish (referral)
    welcome.py        — welcome/rules/pin/settings/nightmode
  utils/
    decorators.py     — admin_only, group_only, handle_errors
    helpers.py        — umumiy yordamchi funksiyalar
    keyboards.py      — barcha inline klaviaturalar
    logger_setup.py   — fayl + konsol loglash
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS, BOT_TOKEN, OWNER_IDS
from data_manager import load_data, save_data
from utils.logger_setup import setup_logging
from utils.helpers import (
    action_logs, group_settings,
    user_warns, welcome_messages, group_rules,
    is_admin, is_bot_admin, get_name, get_settings, add_log,
)

# ── Handlers ──────────────────────────────────
from ad_cleaner import check_ad_comprehensive
from handlers.admin import (
    cmd_warn, cmd_warns, cmd_clearwarns,
    cmd_mute, cmd_unmute, cmd_ban, cmd_unban, cmd_kick, cmd_tempban,
    cmd_addadmin, cmd_removeadmin, cmd_admins,
    cmd_addword, cmd_delword,
)
from handlers.guard import (
    check_spam, check_sticker_spam, check_link, check_forward,
    check_bad_words, check_arabic, check_new_member_media,
    check_night_mode, apply_night_mode,
)
from handlers.info import cmd_info, cmd_log, cmd_reload, cmd_stats
from handlers.sanaydi import (
    cmd_guruh, cmd_guruh_off, cmd_kanal, cmd_kanal_off,
    cmd_bal, cmd_meni, cmd_sizni, cmd_sanaydi_top, cmd_nol, cmd_del,
    on_chat_member_sanaydi, sanaydi_data as _sd,
)
from handlers.welcome import (
    on_new_member,
    cmd_setwelcome, cmd_getwelcome, cmd_delwelcome,
    cmd_rules, cmd_setrules, cmd_delrules,
    cmd_pin, cmd_unpin, cmd_unpinall,
    cmd_settings, settings_callback, cmd_nightmode,
)
from counter import (
    count_message, cmd_count, cmd_top, cmd_toptoday, cmd_topweek, cmd_me, cmd_groupstats,
)

setup_logging()
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
#  MA'LUMOTLARNI YUKLASH VA SAQLASH
# ════════════════════════════════════════════════════════════
def _build_state() -> dict:
    return {
        "group_settings":   group_settings,
        "user_warns":       user_warns,
        "sanaydi_data":     _sd,       # handlers.sanaydi.sanaydi_data
        "welcome_messages": welcome_messages,
        "group_rules":      group_rules,
        "admin_ids":        ADMIN_IDS,
    }


def _save():
    save_data(_build_state())


def _load():
    data = load_data()
    if not data:
        return
    group_settings.update(data.get("group_settings", {}))
    for cid, warns in data.get("user_warns", {}).items():
        user_warns[cid].update(warns)
    for cid, users in data.get("sanaydi_data", {}).items():
        _sd[cid].update(users)
    welcome_messages.update(data.get("welcome_messages", {}))
    group_rules.update(data.get("group_rules", {}))
    for aid in data.get("admin_ids", []):
        if aid not in ADMIN_IDS:
            ADMIN_IDS.append(aid)


# ── Save injeksiyasi ───────────────────────────
import handlers.admin as _hadmin
import handlers.sanaydi as _hsanaydi
import handlers.welcome as _hwelcome
_hadmin.set_save(_save)
_hsanaydi.set_save(_save)
_hwelcome.set_save(_save)


# ════════════════════════════════════════════════════════════
#  START VA MENU
# ════════════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛡️ <b>Universal Qorovul Bot</b>\n\n"
        "Men guruhingizni har tomonlama himoya qilaman:\n\n"
        "<b>🔰 Qorovul:</b>\n"
        "├ Anti-spam va flood himoyasi\n"
        "├ Havola bloklash\n"
        "├ Nojo'ya so'zlar filtri\n"
        "├ Tungi rejim\n"
        "└ Warn / Mute / Ban / TempBan\n\n"
        "<b>📢 Reklama Tozalash:</b>\n"
        "├ Kanal/bot username bloklash\n"
        "├ Inline reklama tugmalar\n"
        "├ Kontakt va joylashuv spam\n"
        "└ Reklama matn pattern\n\n"
        "<b>📊 Sanoqchi:</b>\n"
        "├ Xabar statistikasi\n"
        "├ Top faol a'zolar\n"
        "└ Kunlik/haftalik/umumiy\n\n"
        "<b>📌 Yangi:</b>\n"
        "├ Xush kelibsiz xabar sozlash\n"
        "├ Guruh qoidalari tizimi\n"
        "└ Vaqtli ban va pin buyruqlari\n\n"
        "📌 Meni guruhga qo'shing va <b>admin</b> qiling!\n"
        "⚙️ Sozlamalar: /settings | 📋 Buyruqlar: /menu"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Web Ilova",
                              web_app=WebAppInfo(url="https://unversal-qorovul-bot.netlify.app"))],
        [InlineKeyboardButton("➕ Guruhga Qo'shish",
                              url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("📋 Barcha Buyruqlar", callback_data="show_menu")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛡️ <b>UNIVERSAL QOROVUL BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "👮 <b>MODERATSIYA</b>\n"
        "┌ /warn — ⚠️ Ogohlantirish\n"
        "├ /warns — 📋 Ko'rish\n"
        "├ /clearwarns — 🧹 Tozalash\n"
        "├ /mute [min] — 🔇 Mute\n"
        "├ /unmute — 🔊 Unmute\n"
        "├ /ban — 🚫 Ban\n"
        "├ /unban — ✅ Unban\n"
        "├ /kick — 👢 Kick\n"
        "└ /tempban [30m/2h/1d] — ⏱ Vaqtli ban\n\n"

        "👑 <b>ADMIN BOSHQARUVI</b>\n"
        "┌ /addadmin — ➕ Qo'shish\n"
        "├ /removeadmin — ➖ Olish\n"
        "└ /admins — 📋 Ro'yxat\n\n"

        "📌 <b>PIN</b>\n"
        "┌ /pin [silent] — 📌 Pin\n"
        "├ /unpin — Pinni olish\n"
        "└ /unpinall — Hammasini olish\n\n"

        "📝 <b>XUSH KELIBSIZ</b>\n"
        "┌ /setwelcome <matn> — {name} ismi\n"
        "├ /getwelcome — Ko'rish\n"
        "└ /delwelcome — O'chirish\n\n"

        "📜 <b>QOIDALAR</b>\n"
        "┌ /rules — Ko'rish\n"
        "├ /setrules <matn> — O'rnatish\n"
        "└ /delrules — O'chirish\n\n"

        "📊 <b>SANOQCHI</b>\n"
        "┌ /count — 🔢 Xabar soni\n"
        "├ /me — 👤 Mening statistikam\n"
        "├ /top [son] — 🏆 Top\n"
        "├ /toptoday — 📅 Bugun\n"
        "├ /topweek — 📆 Hafta\n"
        "└ /groupstats — 📈 Guruh\n\n"

        "⚙️ <b>SOZLAMALAR</b>\n"
        "┌ /settings — 🎛 Panel\n"
        "├ /nightmode — 🌙 Tungi rejim\n"
        "├ /addword — ➕ So'z qo'shish\n"
        "└ /delword — ➖ So'z o'chirish\n\n"

        "🔍 <b>INFO</b>\n"
        "┌ /info — 🔍 Ma'lumot\n"
        "├ /reload — 🔄 Adminlarni yangilash\n"
        "├ /log — 📜 Oxirgi harakatlar\n"
        "└ /stats — 📊 Statistika\n\n"

        "👥 <b>SANAYDI</b>\n"
        "┌ /guruh — 👥 Guruhga yig'ish\n"
        "├ /guruh_off — ❌ O'chirish\n"
        "├ /kanal @kanal — 📣 Kanal\n"
        "├ /kanal_off — ❌ O'chirish\n"
        "├ /bal <son> — 🎁 Bal\n"
        "├ /meni — 📊 Statistikam\n"
        "├ /sizni — 📈 Boshqasining (reply)\n"
        "├ /sanaydi_top — 🏆 Top 10\n"
        "├ /nol — 🪓 0 ga tushirish\n"
        "└ /del — 🗑 Tozalash\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ <i>Qorovul</i> • 📢 <i>Reklama</i> • 📊 <i>Sanoqchi</i> • 👥 <i>Sanaydi</i>"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
#  BOT GURUHGA QO'SHILGANDA
# ════════════════════════════════════════════════════════════
async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result     = update.my_chat_member
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    chat       = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        return

    from telegram.constants import ChatMemberStatus
    bot_joined = (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, "kicked")
        and new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )
    bot_promoted = (
        old_status == ChatMemberStatus.MEMBER
        and new_status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )
    if not (bot_joined or bot_promoted):
        return

    text = (
        "Salom 👋\n\n"
        "Men guruhingizni <b>24 soat</b> davomida himoya qilaman:\n"
        "✅ Reklama va spam bloklash\n"
        "✅ Havola filtri\n"
        "✅ Nojo'ya so'zlar\n"
        "✅ Yangi a'zo tekshiruvi\n\n"
        "To'liq ishlashim uchun menga <b>ADMIN</b> bering! 😄\n\n"
        "/menu — barcha buyruqlar\n"
        "/settings — sozlamalar paneli"
    )
    try:
        await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning(f"Bot qo'shildi xabari yuborilmadi: {e}")


# ════════════════════════════════════════════════════════════
#  ASOSIY XABAR HANDLER
# ════════════════════════════════════════════════════════════
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    if update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    s       = get_settings(chat_id)

    # Sanoqchi (adminlar ham)
    if s.get("counter_enabled", True):
        count_message(chat_id, update.effective_user.id,
                      get_name(update.effective_user), update.message)

    # Admin xabarlarini filtrdan o'tkazmaymiz
    try:
        if await is_admin(update, context):
            return
    except Exception:
        return

    if not await is_bot_admin(update, context):
        return

    # Filtrlar ketma-ketligi
    checks = [
        check_night_mode,
        lambda u, c: check_ad_comprehensive(u, c, get_settings(u.effective_chat.id), add_log, get_name),
        check_forward,
        check_link,
        check_bad_words,
        check_arabic,
        check_new_member_media,
        check_sticker_spam,
        check_spam,
    ]
    for check in checks:
        try:
            if await check(update, context):
                return
        except Exception as e:
            logger.warning(f"Filter xatoligi [{check.__name__}]: {e}")


# ════════════════════════════════════════════════════════════
#  PERIODIC SAVE
# ════════════════════════════════════════════════════════════
async def periodic_save(context) -> None:
    _save()
    logger.debug("💾 Avtomatik saqlash bajarildi.")


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def main():
    if not BOT_TOKEN:
        print("=" * 50)
        print("❌ BOT_TOKEN topilmadi!")
        print("Railway da BOT_TOKEN ni sozlang.")
        print("=" * 50)
        return

    _load()
    logger.info("🛡️ Universal Qorovul Bot ishga tushmoqda...")

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Moderatsiya ───────────────────────────
    app.add_handler(CommandHandler("warn",        cmd_warn))
    app.add_handler(CommandHandler("warns",       cmd_warns))
    app.add_handler(CommandHandler("clearwarns",  cmd_clearwarns))
    app.add_handler(CommandHandler("mute",        cmd_mute))
    app.add_handler(CommandHandler("unmute",      cmd_unmute))
    app.add_handler(CommandHandler("ban",         cmd_ban))
    app.add_handler(CommandHandler("unban",       cmd_unban))
    app.add_handler(CommandHandler("kick",        cmd_kick))
    app.add_handler(CommandHandler("tempban",     cmd_tempban))

    # ── Admin boshqaruvi ──────────────────────
    app.add_handler(CommandHandler("addadmin",    cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("admins",      cmd_admins))
    app.add_handler(CommandHandler("addword",     cmd_addword))
    app.add_handler(CommandHandler("delword",     cmd_delword))

    # ── Sozlamalar ────────────────────────────
    app.add_handler(CommandHandler("settings",   cmd_settings))
    app.add_handler(CommandHandler("config",     cmd_settings))
    app.add_handler(CommandHandler("nightmode",  cmd_nightmode))

    # ── Xush kelibsiz xabar ───────────────────
    app.add_handler(CommandHandler("setwelcome", cmd_setwelcome))
    app.add_handler(CommandHandler("getwelcome", cmd_getwelcome))
    app.add_handler(CommandHandler("delwelcome", cmd_delwelcome))

    # ── Guruh qoidalari ───────────────────────
    app.add_handler(CommandHandler("rules",      cmd_rules))
    app.add_handler(CommandHandler("setrules",   cmd_setrules))
    app.add_handler(CommandHandler("delrules",   cmd_delrules))

    # ── Pin / Unpin ───────────────────────────
    app.add_handler(CommandHandler("pin",        cmd_pin))
    app.add_handler(CommandHandler("unpin",      cmd_unpin))
    app.add_handler(CommandHandler("unpinall",   cmd_unpinall))

    # ── Info ──────────────────────────────────
    app.add_handler(CommandHandler("info",       cmd_info))
    app.add_handler(CommandHandler("reload",     cmd_reload))
    app.add_handler(CommandHandler("log",        cmd_log))
    app.add_handler(CommandHandler("stats",      cmd_stats))

    # ── Sanoqchi ──────────────────────────────
    app.add_handler(CommandHandler("count",      cmd_count))
    app.add_handler(CommandHandler("me",         cmd_me))
    app.add_handler(CommandHandler("top",        cmd_top))
    app.add_handler(CommandHandler("toptoday",   cmd_toptoday))
    app.add_handler(CommandHandler("topweek",    cmd_topweek))
    app.add_handler(CommandHandler("groupstats", cmd_groupstats))

    # ── Sanaydi ───────────────────────────────
    app.add_handler(CommandHandler("guruh",        cmd_guruh))
    app.add_handler(CommandHandler("guruh_off",    cmd_guruh_off))
    app.add_handler(CommandHandler("kanal",        cmd_kanal))
    app.add_handler(CommandHandler("kanal_off",    cmd_kanal_off))
    app.add_handler(CommandHandler("bal",          cmd_bal))
    app.add_handler(CommandHandler("meni",         cmd_meni))
    app.add_handler(CommandHandler("sizni",        cmd_sizni))
    app.add_handler(CommandHandler("sanaydi_top",  cmd_sanaydi_top))
    app.add_handler(CommandHandler("nol",          cmd_nol))
    app.add_handler(CommandHandler("del",          cmd_del))

    # ── Asosiy ────────────────────────────────
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_menu))
    app.add_handler(CommandHandler("menu",   cmd_menu))

    # ── ChatMember handlerlar ─────────────────
    app.add_handler(ChatMemberHandler(on_chat_member_sanaydi, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(on_bot_added_to_group,  ChatMemberHandler.MY_CHAT_MEMBER))

    # ── Callback ──────────────────────────────
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^(toggle_|settings_)"))
    app.add_handler(CallbackQueryHandler(cmd_menu,          pattern=r"^show_menu$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^noop$"))

    # ── Xabar handleri ────────────────────────
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
        on_message,
    ))

    # ── Avtomatik saqlash (har 5 daqiqa) ─────
    app.job_queue.run_repeating(periodic_save, interval=300, first=60)

    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
    logger.info("📌 Botni guruhga qo'shing va admin qiling.")

    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        _save()
        logger.info("💾 Ma'lumotlar saqlandi. Bot to'xtatildi.")


if __name__ == "__main__":
    main()
