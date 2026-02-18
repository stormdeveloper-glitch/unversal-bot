"""
╔══════════════════════════════════════════════════════════════╗
║       🛡️  TELEGRAM UNIVERSAL BOT — QOROVUL BOT  🛡️         ║
║   Qorovul + Sanoqchi + Reklama Tozalagich — Har tomonlama   ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from telegram import (
    ChatMember,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, DEFAULT_SETTINGS, MESSAGES, ADMIN_IDS, SECRET_OWNER_ID, OWNER_IDS
from counter import (
    count_message, register_member, cmd_count, cmd_top,
    cmd_toptoday, cmd_topweek, cmd_me, cmd_groupstats,
)
from ad_cleaner import check_ad_comprehensive

# ════════════════════════════════════════════════════════════
#  LOGGING
# ════════════════════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
#  DATA STORAGE (IN-MEMORY)
# ════════════════════════════════════════════════════════════
# Guruh sozlamalari:   { chat_id: { ...settings... } }
group_settings: dict[int, dict] = {}

# Ogohlantirishlar:    { chat_id: { user_id: count } }
user_warns: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

# Spam kuzatuvi:       { chat_id: { user_id: [timestamps] } }
message_timestamps: dict[int, dict[int, list]] = defaultdict(lambda: defaultdict(list))

# Sticker spam:        { chat_id: { user_id: [timestamps] } }
sticker_timestamps: dict[int, dict[int, list]] = defaultdict(lambda: defaultdict(list))

# Captcha ma'lumotlari: { chat_id: { user_id: { answer, msg_id, timestamp } } }
pending_captcha: dict[int, dict[int, dict]] = defaultdict(dict)

# Log tarixi:          { chat_id: [ { action, user, admin, time, reason } ] }
action_logs: dict[int, list] = defaultdict(list)

# Yangi a'zo vaqtlari: { chat_id: { user_id: join_timestamp } }
new_member_times: dict[int, dict[int, float]] = defaultdict(dict)

# ════════════════════════════════════════════════════════════
#  SANAYDI BOT — DATA STORAGE
# ════════════════════════════════════════════════════════════
# Guruh rejimi: { chat_id: True/False }
sanaydi_guruh_mode: dict[int, bool] = defaultdict(bool)

# Kanal rejimi: { chat_id: "@kanal_username" yoki None }
sanaydi_kanal_mode: dict[int, str] = {}

# Referral hisob: { chat_id: { inviter_user_id: { "name": str, "count": int, "bal": int } } }
sanaydi_data: dict[int, dict[int, dict]] = defaultdict(dict)

# Invite link → user_id mapping: { chat_id: { invite_link_str: user_id } }
sanaydi_invite_links: dict[int, dict[str, int]] = defaultdict(dict)


def sanaydi_get_data(chat_id: int, user_id: int, name: str) -> dict:
    """Foydalanuvchi sanaydi ma'lumotlarini olish."""
    if user_id not in sanaydi_data[chat_id]:
        sanaydi_data[chat_id][user_id] = {
            "name": name,
            "count": 0,
            "bal": 0,
        }
    sanaydi_data[chat_id][user_id]["name"] = name
    return sanaydi_data[chat_id][user_id]


# Bad words
BAD_WORDS_FILE = os.path.join(os.path.dirname(__file__), "bad_words.json")


def load_bad_words() -> tuple[list[str], list[str]]:
    """Bad words va patternlarni yuklash."""
    try:
        with open(BAD_WORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("words", []), data.get("patterns", [])
    except FileNotFoundError:
        return [], []


def save_bad_words(words: list[str], patterns: list[str]):
    """Bad words ni saqlash."""
    with open(BAD_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"words": words, "patterns": patterns}, f, ensure_ascii=False, indent=4)


bad_words_list, bad_patterns = load_bad_words()


# ════════════════════════════════════════════════════════════
#  YORDAMCHI FUNKSIYALAR
# ════════════════════════════════════════════════════════════
def get_settings(chat_id: int) -> dict:
    """Guruh sozlamalarini olish (default bilan)."""
    if chat_id not in group_settings:
        group_settings[chat_id] = DEFAULT_SETTINGS.copy()
    return group_settings[chat_id]


def get_name(user) -> str:
    """Foydalanuvchi ismini olish."""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or "Foydalanuvchi"


def add_log(chat_id: int, action: str, user_name: str, admin_name: str = "", reason: str = ""):
    """Log yozish."""
    entry = {
        "action": action,
        "user": user_name,
        "admin": admin_name,
        "reason": reason,
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    action_logs[chat_id].append(entry)
    # Faqat oxirgi 200 ta logni saqlash
    if len(action_logs[chat_id]) > 200:
        action_logs[chat_id] = action_logs[chat_id][-200:]


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> bool:
    """Foydalanuvchi admin yoki yo'qligini tekshirish."""
    uid = user_id or update.effective_user.id
    # Barcha ownerlar va ADMIN_IDS doim admin
    if uid in OWNER_IDS or uid in ADMIN_IDS:
        return True
    member = await context.bot.get_chat_member(update.effective_chat.id, uid)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def is_bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Bot admin yoki yo'qligini tekshirish."""
    bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
    return bot_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


def generate_captcha() -> tuple[str, int]:
    """Matematik captcha yaratish."""
    ops = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("×", lambda a, b: a * b),
    ]
    op_symbol, op_func = random.choice(ops)
    a = random.randint(1, 20)
    b = random.randint(1, 10)
    if op_symbol == "-" and a < b:
        a, b = b, a
    question = f"{a} {op_symbol} {b}"
    answer = op_func(a, b)
    return question, answer


# ════════════════════════════════════════════════════════════
#  KOMANDALAR — ASOSIY
# ════════════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida ma'lumot."""
    text = (
        "🛡️ <b>Universal Qorovul Bot</b>\n\n"
        "Men guruhingizni har tomonlama himoya qilaman:\n\n"
        "<b>🔰 Qorovul:</b>\n"
        "├ Anti-spam va flood himoyasi\n"
        "├ Havola bloklash\n"
        "├ Yangi a'zolar uchun captcha\n"
        "├ Nojo'ya so'zlarni filtrlash\n"
        "├ Tungi rejim\n"
        "└ Warn / Mute / Ban tizimi\n\n"
        "<b>📢 Reklama Tozalash:</b>\n"
        "├ Kanal/bot username aniqlash\n"
        "├ Inline reklama tugmalarni bloklash\n"
        "├ Kontakt va joylashuv spam\n"
        "├ Ko'p forward aniqlash\n"
        "└ Reklama matn pattern aniqlash\n\n"
        "<b>📊 Sanoqchi:</b>\n"
        "├ Xabar sanoqchisi\n"
        "├ Top faol a'zolar\n"
        "├ Kunlik/haftalik statistika\n"
        "└ Guruh umumiy statistika\n\n"
        "📌 Meni guruhga qo'shing va <b>admin</b> qiling!\n"
        "⚙️ Sozlamalar uchun: /settings"
    )

    # Web App tugmasi
    web_app = WebAppInfo(url="https://unversal-qorovul-bot.netlify.app")
    keyboard = [
        [InlineKeyboardButton("🌐 Web Ilova", web_app=web_app)],
        [InlineKeyboardButton("➕ Guruhga Qo'shish", url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyruqlar ro'yxati — /menu ga yo'naltiradi."""
    await cmd_menu(update, context)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha buyruqlarni chiroyli ko'rsatish."""
    text = (
        "🛡️ <b>UNIVERSAL QOROVUL BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "👮 <b>ADMIN BUYRUQLARI</b>\n"
        "┌ /warn — ⚠️ Ogohlantirish berish\n"
        "├ /warns — 📋 Ogohlantirishlarni ko'rish\n"
        "├ /clearwarns — 🧹 Ogohlantirishlarni tozalash\n"
        "├ /mute [daqiqa] — 🔇 Ovozini o'chirish\n"
        "├ /unmute — 🔊 Ovozini yoqish\n"
        "├ /ban — 🚫 Guruhdan chiqarish\n"
        "├ /unban — ✅ Blokni olib tashlash\n"
        "└ /kick — 👢 Chiqarish\n\n"

        "👑 <b>ADMIN BOSHQARUVI</b>\n"
        "┌ /addadmin — ➕ Admin qo'shish\n"
        "├ /removeadmin — ➖ Adminni olib tashlash\n"
        "└ /admins — 📋 Adminlar ro'yxati\n\n"

        "📊 <b>SANOQCHI</b>\n"
        "┌ /count — 🔢 Xabar soni (reply)\n"
        "├ /me — 👤 O'z statistikam\n"
        "├ /top [son] — 🏆 Top faol a'zolar\n"
        "├ /toptoday — 📅 Bugungi top\n"
        "├ /topweek — 📆 Haftalik top\n"
        "└ /groupstats — 📈 Guruh statistikasi\n\n"

        "⚙️ <b>SOZLAMALAR</b>\n"
        "┌ /settings — 🎛 Inline sozlamalar paneli\n"
        "├ /config — ⚙️ Sozlamalar paneli (alias)\n"
        "├ /nightmode — 🌙 Tungi rejim\n"
        "├ /addword [so'z] — ➕ Taqiqlangan so'z qo'shish\n"
        "└ /delword [so'z] — ➖ Taqiqlangan so'z o'chirish\n\n"

        "🔍 <b>MA'LUMOT VA BOSHQARUV</b>\n"
        "┌ /info — 🔍 Foydalanuvchi to'liq ma'lumoti\n"
        "├ /reload — 🔄 Adminlar ro'yxatini yangilash\n"
        "├ /log — 📜 Oxirgi harakatlar\n"
        "├ /stats — 📊 Bot statistikasi\n"
        "├ /start — 🏠 Bot haqida\n"
        "├ /help — ❓ Yordam\n"
        "└ /menu — 📋 Shu menyu\n\n"

        "👥 <b>SANAYDI — ODAM YIG'ISH</b>\n"
        "┌ /guruh — 👥 Guruhga odam yig'ishni yoqish\n"
        "├ /guruh_off — ❌ Guruh rejimini o'chirish\n"
        "├ /kanal @kanal — 📣 Kanalga odam yig'ishni yoqish\n"
        "├ /kanal_off — ❌ Kanal rejimini o'chirish\n"
        "├ /bal [son] — 🎁 Bal qo'shish (reply)\n"
        "├ /meni — 📊 O'z referral statistikam\n"
        "├ /sizni — 📈 Boshqasining statistikasi (reply)\n"
        "├ /sanaydi_top — 🏆 Eng ko'p odam qo'shgan 10 talik\n"
        "├ /nol — 🪓 Foydalanuvchi ma'lumotini 0 ga tushirish\n"
        "└ /del — 🗑 Barcha ma'lumotlarni tozalash\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ <i>Qorovul</i> • 📢 <i>Reklama Tozalash</i>\n"
        "📊 <i>Sanoqchi</i> • 👥 <i>Sanaydi</i> • 🔍 <i>Info & Reload</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
#  SOZLAMALAR — INLINE KEYBOARD
# ════════════════════════════════════════════════════════════
def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Sozlamalar inline klaviaturasi."""
    s = get_settings(chat_id)

    def status(key):
        return "✅" if s.get(key) else "❌"

    keyboard = [
        [
            InlineKeyboardButton(f"{status('anti_spam')} Anti-Spam", callback_data="toggle_anti_spam"),
            InlineKeyboardButton(f"{status('anti_link')} Anti-Link", callback_data="toggle_anti_link"),
        ],
        [
            InlineKeyboardButton(f"{status('anti_forward')} Anti-Forward", callback_data="toggle_anti_forward"),
            InlineKeyboardButton(f"{status('bad_words_filter')} So'z Filtri", callback_data="toggle_bad_words_filter"),
        ],
        [
            InlineKeyboardButton(f"{status('captcha_enabled')} Captcha", callback_data="toggle_captcha_enabled"),
            InlineKeyboardButton(f"{status('night_mode')} Tungi Rejim", callback_data="toggle_night_mode"),
        ],
        [
            InlineKeyboardButton(f"{status('anti_sticker_spam')} Anti-Sticker", callback_data="toggle_anti_sticker_spam"),
            InlineKeyboardButton(f"{status('anti_arabic')} Anti-Arab", callback_data="toggle_anti_arabic"),
        ],
        [
            InlineKeyboardButton(
                f"{status('new_member_media_restrict')} Yangi A'zo Media",
                callback_data="toggle_new_member_media_restrict"
            ),
        ],
        [
            InlineKeyboardButton(f"{status('anti_ad')} Anti-Reklama", callback_data="toggle_anti_ad"),
            InlineKeyboardButton(f"{status('counter_enabled')} Sanoqchi", callback_data="toggle_counter_enabled"),
        ],
        [
            InlineKeyboardButton(f"{status('anti_channel_username')} Anti-@kanal", callback_data="toggle_anti_channel_username"),
            InlineKeyboardButton(f"{status('anti_ad_patterns')} Anti-Pattern", callback_data="toggle_anti_ad_patterns"),
        ],
        [InlineKeyboardButton("🔄 Yopish", callback_data="settings_close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sozlamalar panelini ochish."""
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("⚙️ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    s = get_settings(chat_id)
    text = (
        "⚙️ <b>Bot Sozlamalari</b>\n\n"
        f"🔹 Spam limiti: <b>{s['spam_message_limit']}</b> xabar / <b>{s['spam_time_window']}</b> son.\n"
        f"🔹 Mute davomiyligi: <b>{s['mute_duration_minutes']}</b> daqiqa\n"
        f"🔹 Max ogohlantirishlar: <b>{s['max_warns']}</b>\n"
        f"🔹 Captcha vaqti: <b>{s['captcha_timeout']}</b> soniya\n"
        f"🔹 Tungi rejim: <b>{s['night_start_hour']}:00 — {s['night_end_hour']}:00</b>\n\n"
        "Tugmalarni bosib sozlamalarni o'zgartiring:"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=build_settings_keyboard(chat_id),
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sozlamalar tugmalarini boshqarish."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    data = query.data

    if data == "settings_close":
        await query.message.delete()
        return

    if not await is_admin(update, context, query.from_user.id):
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    if data.startswith("toggle_"):
        key = data.replace("toggle_", "")
        s = get_settings(chat_id)
        if key in s:
            s[key] = not s[key]
            state = "yoqildi ✅" if s[key] else "o'chirildi ❌"
            await query.answer(f"{key}: {state}")

            # Tungi rejim o'zgarsa chat permissionlarini yangilash
            if key == "night_mode":
                await apply_night_mode(context, chat_id, s[key])

    await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(chat_id))


# ════════════════════════════════════════════════════════════
#  CAPTCHA — YANGI A'ZO TEKSHIRUVI
# ════════════════════════════════════════════════════════════
async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi a'zo qo'shilganda captcha berish."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        # Yangi a'zo vaqtini saqlash
        new_member_times[chat_id][member.id] = time.time()

        if not s["captcha_enabled"]:
            # Captcha o'chiq — oddiy welcome
            welcome = f"👋 Salom, <b>{get_name(member)}</b>! Guruhga xush kelibsiz!"
            await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
            continue

        # Captcha yoqiq — tekshiruv
        question, answer = generate_captcha()

        # Foydalanuvchini vaqtincha cheklash
        try:
            await context.bot.restrict_chat_member(
                chat_id, member.id,
                ChatPermissions(
                    can_send_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
            )
        except Exception as e:
            logger.warning(f"Captcha restrict xatolik: {e}")

        text = MESSAGES["welcome"].format(
            name=get_name(member),
            question=question,
            timeout=s["captcha_timeout"],
        )
        msg = await update.message.reply_text(text, parse_mode=ParseMode.HTML)

        pending_captcha[chat_id][member.id] = {
            "answer": answer,
            "msg_id": msg.message_id,
            "timestamp": time.time(),
        }

        # Timeout uchun job
        context.job_queue.run_once(
            captcha_timeout,
            s["captcha_timeout"],
            data={"chat_id": chat_id, "user_id": member.id},
            name=f"captcha_{chat_id}_{member.id}",
        )


async def captcha_timeout(context: ContextTypes.DEFAULT_TYPE):
    """Captcha vaqti tugaganda."""
    data = context.job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]

    if chat_id in pending_captcha and user_id in pending_captcha[chat_id]:
        info = pending_captcha[chat_id].pop(user_id)
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            name = get_name(member.user)
            # Guruhdan chiqarish
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)  # qayta kirish uchun

            text = MESSAGES["captcha_fail"].format(name=name)
            await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            add_log(chat_id, "CAPTCHA_FAIL", name, "Bot", "Vaqt tugadi")
        except Exception as e:
            logger.warning(f"Captcha timeout xatolik: {e}")

        # Captcha xabarini o'chirish
        try:
            await context.bot.delete_message(chat_id, info["msg_id"])
        except Exception:
            pass


async def on_message_captcha_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captcha javobini tekshirish."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in pending_captcha or user_id not in pending_captcha[chat_id]:
        return False  # Bu foydalanuvchi captcha kutilmayapti

    info = pending_captcha[chat_id][user_id]
    text = (update.message.text or "").strip()

    try:
        user_answer = int(text)
    except (ValueError, TypeError):
        return True  # Raqam emas — e'tiborsiz qoldirish

    if user_answer == info["answer"]:
        # To'g'ri javob!
        pending_captcha[chat_id].pop(user_id)

        # Job'ni bekor qilish
        jobs = context.job_queue.get_jobs_by_name(f"captcha_{chat_id}_{user_id}")
        for job in jobs:
            job.schedule_removal()

        # Cheklovlarni olib tashlash
        try:
            await context.bot.restrict_chat_member(
                chat_id, user_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_send_polls=True,
                    can_invite_users=True,
                    can_pin_messages=False,
                    can_manage_topics=False,
                ),
            )
        except Exception:
            pass

        name = get_name(update.effective_user)
        success_text = MESSAGES["captcha_success"].format(name=name)
        await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "CAPTCHA_OK", name)

        # Captcha xabarini o'chirish
        try:
            await context.bot.delete_message(chat_id, info["msg_id"])
        except Exception:
            pass

        return True  # Captcha hal qilindi
    else:
        # Noto'g'ri javob
        await update.message.reply_text(
            MESSAGES["captcha_wrong"], parse_mode=ParseMode.HTML
        )
        return True


# ════════════════════════════════════════════════════════════
#  ANTI-SPAM — FLOOD HIMOYASI
# ════════════════════════════════════════════════════════════
async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Spam tekshiruvi. True qaytarsa = spam aniqlandi."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s["anti_spam"]:
        return False

    now = time.time()
    timestamps = message_timestamps[chat_id][user_id]
    timestamps.append(now)

    # Eski timestamplarni tozalash
    cutoff = now - s["spam_time_window"]
    message_timestamps[chat_id][user_id] = [t for t in timestamps if t > cutoff]

    if len(message_timestamps[chat_id][user_id]) > s["spam_message_limit"]:
        name = get_name(update.effective_user)
        duration = s["mute_duration_minutes"]

        if s["spam_action"] == "ban":
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                text = MESSAGES["spam_banned"].format(name=name)
                await update.message.reply_text(text, parse_mode=ParseMode.HTML)
                add_log(chat_id, "SPAM_BAN", name, "Bot")
            except Exception as e:
                logger.warning(f"Spam ban xatolik: {e}")
        else:
            try:
                until = datetime.now(timezone.utc) + timedelta(minutes=duration)
                await context.bot.restrict_chat_member(
                    chat_id, user_id,
                    ChatPermissions(can_send_messages=False),
                    until_date=until,
                )
                text = MESSAGES["spam_muted"].format(name=name, duration=duration)
                await update.message.reply_text(text, parse_mode=ParseMode.HTML)
                add_log(chat_id, "SPAM_MUTE", name, "Bot", f"{duration} daqiqa")
            except Exception as e:
                logger.warning(f"Spam mute xatolik: {e}")

        # Timestamplarni tozalash
        message_timestamps[chat_id][user_id] = []
        return True

    return False


# ════════════════════════════════════════════════════════════
#  ANTI-STICKER SPAM
# ════════════════════════════════════════════════════════════
async def check_sticker_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sticker spam tekshiruvi."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s.get("anti_sticker_spam"):
        return False

    if not update.message.sticker and not update.message.animation:
        return False

    now = time.time()
    timestamps = sticker_timestamps[chat_id][user_id]
    timestamps.append(now)

    cutoff = now - s["sticker_time_window"]
    sticker_timestamps[chat_id][user_id] = [t for t in timestamps if t > cutoff]

    if len(sticker_timestamps[chat_id][user_id]) > s["sticker_limit"]:
        try:
            await update.message.delete()
        except Exception:
            pass

        name = get_name(update.effective_user)
        text = MESSAGES["sticker_spam"].format(name=name)
        await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        sticker_timestamps[chat_id][user_id] = []
        add_log(chat_id, "STICKER_SPAM", name, "Bot")
        return True

    return False


# ════════════════════════════════════════════════════════════
#  ANTI-LINK
# ════════════════════════════════════════════════════════════
URL_PATTERN = re.compile(
    r"(?:https?://|www\.)"
    r"[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
    r"|(?:[a-zA-Z0-9\-]+\.)+(?:com|org|net|ru|uz|me|io|info|xyz|co|uk|de)",
    re.IGNORECASE,
)


async def check_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Havolalarni tekshirish."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["anti_link"]:
        return False

    text = update.message.text or update.message.caption or ""
    matches = URL_PATTERN.findall(text)

    if not matches:
        return False

    # Ruxsat berilgan domenlarni tekshirish
    allowed = s["allowed_domains"]
    for url in matches:
        is_allowed = False
        for domain in allowed:
            if domain in url:
                is_allowed = True
                break
        if not is_allowed:
            try:
                await update.message.delete()
            except Exception:
                pass

            name = get_name(update.effective_user)
            text = MESSAGES["link_deleted"].format(name=name)
            await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            add_log(chat_id, "LINK_DELETED", name, "Bot")
            return True

    return False


# ════════════════════════════════════════════════════════════
#  ANTI-FORWARD
# ════════════════════════════════════════════════════════════
async def check_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Forward xabarlarni tekshirish."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["anti_forward"]:
        return False

    if update.message.forward_date or update.message.forward_from or update.message.forward_from_chat:
        try:
            await update.message.delete()
        except Exception:
            pass

        name = get_name(update.effective_user)
        text = MESSAGES["forward_deleted"].format(name=name)
        await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "FORWARD_DELETED", name, "Bot")
        return True

    return False


# ════════════════════════════════════════════════════════════
#  BAD WORDS FILTRI
# ════════════════════════════════════════════════════════════
async def check_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Nojo'ya so'zlarni tekshirish."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["bad_words_filter"]:
        return False

    text = (update.message.text or update.message.caption or "").lower()

    # So'zlarni tekshirish
    for word in bad_words_list:
        if word.lower() in text:
            try:
                await update.message.delete()
            except Exception:
                pass

            name = get_name(update.effective_user)
            msg = MESSAGES["bad_word_deleted"].format(name=name)
            await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
            add_log(chat_id, "BAD_WORD", name, "Bot", f"So'z: {word}")
            return True

    # Patternlarni tekshirish
    for pattern in bad_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            try:
                await update.message.delete()
            except Exception:
                pass

            name = get_name(update.effective_user)
            msg = MESSAGES["bad_word_deleted"].format(name=name)
            await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
            add_log(chat_id, "BAD_PATTERN", name, "Bot")
            return True

    return False


# ════════════════════════════════════════════════════════════
#  ANTI-ARABIC
# ════════════════════════════════════════════════════════════
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]{5,}")


async def check_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Arab yozuvini tekshirish."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s.get("anti_arabic"):
        return False

    text = update.message.text or ""
    if ARABIC_PATTERN.search(text):
        try:
            await update.message.delete()
        except Exception:
            pass
        return True

    return False


# ════════════════════════════════════════════════════════════
#  YANGI A'ZO MEDIA CHEKLOVI
# ════════════════════════════════════════════════════════════
async def check_new_member_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Yangi a'zolarning media yuborishini cheklash."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    s = get_settings(chat_id)

    if not s.get("new_member_media_restrict"):
        return False

    join_time = new_member_times.get(chat_id, {}).get(user_id)
    if not join_time:
        return False

    hours_since_join = (time.time() - join_time) / 3600
    if hours_since_join > s["new_member_restrict_hours"]:
        return False

    # Media xabarlarni tekshirish
    msg = update.message
    if msg.photo or msg.video or msg.document or msg.voice or msg.video_note or msg.animation:
        try:
            await msg.delete()
        except Exception:
            pass

        name = get_name(update.effective_user)
        restrict_h = s["new_member_restrict_hours"]
        text = f"🚫 <b>{name}</b>, yangi a'zolarga {restrict_h} soat davomida media yuborish taqiqlangan!"
        await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        return True

    return False


# ════════════════════════════════════════════════════════════
#  TUNGI REJIM
# ════════════════════════════════════════════════════════════
async def check_night_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Tungi rejim tekshiruvi."""
    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    if not s["night_mode"]:
        return False

    now_hour = datetime.now().hour
    start = s["night_start_hour"]
    end = s["night_end_hour"]

    is_night = False
    if start > end:
        # Masalan 23:00 — 06:00
        is_night = now_hour >= start or now_hour < end
    else:
        is_night = start <= now_hour < end

    if is_night:
        try:
            await update.message.delete()
        except Exception:
            pass
        # Har safar xabar yubormaslik uchun
        return True

    return False


async def apply_night_mode(context: ContextTypes.DEFAULT_TYPE, chat_id: int, enable: bool):
    """Tungi rejimni qo'llash."""
    if enable:
        await context.bot.set_chat_permissions(
            chat_id,
            ChatPermissions(can_send_messages=False),
        )
        await context.bot.send_message(
            chat_id, MESSAGES["night_mode_on"], parse_mode=ParseMode.HTML
        )
    else:
        await context.bot.set_chat_permissions(
            chat_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_invite_users=True,
            ),
        )
        await context.bot.send_message(
            chat_id, MESSAGES["night_mode_off"], parse_mode=ParseMode.HTML
        )


async def cmd_nightmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tungi rejimni yoqish/o'chirish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    s = get_settings(chat_id)
    s["night_mode"] = not s["night_mode"]
    await apply_night_mode(context, chat_id, s["night_mode"])


# ════════════════════════════════════════════════════════════
#  ADMIN BUYRUQLARI — WARN / MUTE / BAN / KICK
# ════════════════════════════════════════════════════════════
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini ogohlantirish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    reason = " ".join(context.args) if context.args else "Sabab ko'rsatilmagan"
    s = get_settings(chat_id)

    user_warns[chat_id][target.id] += 1
    count = user_warns[chat_id][target.id]
    max_warns = s["max_warns"]
    name = get_name(target)

    if count >= max_warns:
        # Ban
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            text = MESSAGES["warn_ban"].format(name=name, max=max_warns)
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            user_warns[chat_id][target.id] = 0
            add_log(chat_id, "WARN_BAN", name, get_name(update.effective_user), reason)
        except Exception as e:
            logger.warning(f"Warn ban xatolik: {e}")
    else:
        text = MESSAGES["warn_given"].format(
            name=name, count=count, max=max_warns, reason=reason
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "WARN", name, get_name(update.effective_user), reason)


async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining ogohlantirishlarini ko'rish."""
    chat_id = update.effective_chat.id

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    count = user_warns[chat_id].get(target.id, 0)
    s = get_settings(chat_id)
    name = get_name(target)

    text = f"⚠️ <b>{name}</b> ning ogohlantirishlari: <b>{count}/{s['max_warns']}</b>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_clearwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ogohlantirishlarni tozalash."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    user_warns[chat_id][target.id] = 0
    name = get_name(target)
    await update.message.reply_text(
        f"✅ <b>{name}</b> ning ogohlantirishlari tozalandi.", parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "WARNS_CLEAR", name, get_name(update.effective_user))


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini mute qilish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    # Default yoki ko'rsatilgan vaqt
    duration = int(context.args[0]) if context.args else get_settings(chat_id)["mute_duration_minutes"]
    name = get_name(target)

    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=duration)
        await context.bot.restrict_chat_member(
            chat_id, target.id,
            ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        text = MESSAGES["muted"].format(name=name, duration=duration)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "MUTE", name, get_name(update.effective_user), f"{duration} daqiqa")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini unmute qilish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    name = get_name(target)

    try:
        await context.bot.restrict_chat_member(
            chat_id, target.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_invite_users=True,
            ),
        )
        text = MESSAGES["unmuted"].format(name=name)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "UNMUTE", name, get_name(update.effective_user))
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini ban qilish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    name = get_name(target)
    reason = " ".join(context.args) if context.args else ""

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        text = MESSAGES["banned"].format(name=name)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "BAN", name, get_name(update.effective_user), reason)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini unban qilish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    name = get_name(target)

    try:
        await context.bot.unban_chat_member(chat_id, target.id)
        text = MESSAGES["unbanned"].format(name=name)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "UNBAN", name, get_name(update.effective_user))
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchini chiqarish (qayta kirishi mumkin)."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    if await is_admin(update, context, target.id):
        await update.message.reply_text(MESSAGES["cant_restrict_admin"], parse_mode=ParseMode.HTML)
        return

    name = get_name(target)

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        text = MESSAGES["kicked"].format(name=name)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        add_log(chat_id, "KICK", name, get_name(update.effective_user))
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


# ════════════════════════════════════════════════════════════
#  BAD WORDS BOSHQARUVI
# ════════════════════════════════════════════════════════════
async def cmd_addword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taqiqlangan so'z qo'shish."""
    global bad_words_list

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not context.args:
        await update.message.reply_text("❌ Foydalanish: /addword <so'z>")
        return

    word = " ".join(context.args).lower()
    if word not in bad_words_list:
        bad_words_list.append(word)
        save_bad_words(bad_words_list, bad_patterns)
        await update.message.reply_text(f"✅ <b>'{word}'</b> taqiqlangan so'zlar ro'yxatiga qo'shildi.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"ℹ️ <b>'{word}'</b> allaqachon ro'yxatda.", parse_mode=ParseMode.HTML)


async def cmd_delword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taqiqlangan so'zni o'chirish."""
    global bad_words_list

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not context.args:
        await update.message.reply_text("❌ Foydalanish: /delword <so'z>")
        return

    word = " ".join(context.args).lower()
    if word in bad_words_list:
        bad_words_list.remove(word)
        save_bad_words(bad_words_list, bad_patterns)
        await update.message.reply_text(f"✅ <b>'{word}'</b> ro'yxatdan o'chirildi.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ <b>'{word}'</b> ro'yxatda topilmadi.", parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
#  ADMIN BOSHQARUVI — ADDADMIN / REMOVEADMIN / ADMINS
# ════════════════════════════════════════════════════════════
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi admin qo'shish (barcha adminlar uchun)."""
    caller_id = update.effective_user.id

    if caller_id not in OWNER_IDS and caller_id not in ADMIN_IDS:
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    target_id = None
    target_name = None

    # Reply orqali
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = get_name(update.message.reply_to_message.from_user)
    # ID orqali
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_name = str(target_id)
        except ValueError:
            await update.message.reply_text("❌ Foydalanish: /addadmin <ID> yoki xabariga reply qiling")
            return
    else:
        await update.message.reply_text("❌ Foydalanish: /addadmin <ID> yoki xabariga reply qiling")
        return

    if target_id in ADMIN_IDS:
        await update.message.reply_text(f"ℹ️ <b>{target_name}</b> allaqachon admin.", parse_mode=ParseMode.HTML)
        return

    ADMIN_IDS.append(target_id)
    await update.message.reply_text(
        f"✅ <b>{target_name}</b> (ID: <code>{target_id}</code>) admin qilib tayinlandi!\n\n"
        f"👑 Jami adminlar: <b>{len(ADMIN_IDS)}</b>",
        parse_mode=ParseMode.HTML,
    )
    add_log(update.effective_chat.id, "ADD_ADMIN", target_name, get_name(update.effective_user))


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminni olib tashlash (barcha adminlar uchun)."""
    caller_id = update.effective_user.id

    if caller_id not in OWNER_IDS and caller_id not in ADMIN_IDS:
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    target_id = None
    target_name = None

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = get_name(update.message.reply_to_message.from_user)
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_name = str(target_id)
        except ValueError:
            await update.message.reply_text("❌ Foydalanish: /removeadmin <ID> yoki xabarига reply qiling")
            return
    else:
        await update.message.reply_text("❌ Foydalanish: /removeadmin <ID> yoki xabariga reply qiling")
        return

    if target_id == caller_id:
        await update.message.reply_text("❌ O'zingizni olib tashlay olmaysiz!", parse_mode=ParseMode.HTML)
        return

    if target_id not in ADMIN_IDS:
        await update.message.reply_text(f"❌ <b>{target_name}</b> admin emas.", parse_mode=ParseMode.HTML)
        return

    ADMIN_IDS.remove(target_id)
    await update.message.reply_text(
        f"✅ <b>{target_name}</b> (ID: <code>{target_id}</code>) admin ro'yxatidan olib tashlandi.",
        parse_mode=ParseMode.HTML,
    )
    add_log(update.effective_chat.id, "REMOVE_ADMIN", target_name, get_name(update.effective_user))


async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ro'yxatini ko'rsatish (yashirin ega ko'rinmaydi)."""
    if not ADMIN_IDS:
        await update.message.reply_text("👑 Hozircha tayinlangan admin yo'q.")
        return

    lines = ["👑 <b>Bot adminlari:</b>\n"]
    for i, admin_id in enumerate(ADMIN_IDS, 1):
        # SECRET_OWNER va OWNER_IDS hech qachon ko'rsatilmaydi
        if admin_id in OWNER_IDS:
            continue
        try:
            member = await context.bot.get_chat(admin_id)
            name = member.first_name or member.username or str(admin_id)
        except Exception:
            name = str(admin_id)
        lines.append(f"{i}. <b>{name}</b> — <code>{admin_id}</code>")

    lines.append(f"\n📊 Jami: <b>{len(ADMIN_IDS)}</b> admin")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
#  LOG VA STATISTIKA
# ════════════════════════════════════════════════════════════
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi harakatlarni ko'rish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    logs = action_logs.get(chat_id, [])
    if not logs:
        await update.message.reply_text("📋 Hozircha hech qanday log yo'q.")
        return

    # Oxirgi 15 ta
    recent = logs[-15:]
    lines = ["📋 <b>Oxirgi harakatlar:</b>\n"]
    for entry in reversed(recent):
        line = f"🔸 <b>{entry['action']}</b> — {entry['user']}"
        if entry["admin"]:
            line += f" (admin: {entry['admin']})"
        if entry["reason"]:
            line += f"\n    📝 {entry['reason']}"
        line += f"\n    🕐 {entry['time']}"
        lines.append(line)

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh statistikasi."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    logs = action_logs.get(chat_id, [])
    s = get_settings(chat_id)

    # Statistikani hisoblash
    stats = defaultdict(int)
    for entry in logs:
        stats[entry["action"]] += 1

    warns_count = sum(user_warns[chat_id].values())
    captcha_pending = len(pending_captcha.get(chat_id, {}))

    text = (
        "📊 <b>Guruh Statistikasi</b>\n\n"
        f"🔹 Jami loglar: <b>{len(logs)}</b>\n"
        f"🔹 Spam bloklangan: <b>{stats.get('SPAM_MUTE', 0) + stats.get('SPAM_BAN', 0)}</b>\n"
        f"🔹 Havolalar o'chirilgan: <b>{stats.get('LINK_DELETED', 0)}</b>\n"
        f"🔹 Forward o'chirilgan: <b>{stats.get('FORWARD_DELETED', 0)}</b>\n"
        f"🔹 Nojo'ya so'zlar: <b>{stats.get('BAD_WORD', 0) + stats.get('BAD_PATTERN', 0)}</b>\n"
        f"🔹 Ogohlantirishlar: <b>{stats.get('WARN', 0)}</b>\n"
        f"🔹 Banlar: <b>{stats.get('BAN', 0) + stats.get('WARN_BAN', 0)}</b>\n"
        f"🔹 Captcha muvaffaqiyatli: <b>{stats.get('CAPTCHA_OK', 0)}</b>\n"
        f"🔹 Captcha muvaffaqiyatsiz: <b>{stats.get('CAPTCHA_FAIL', 0)}</b>\n\n"
        f"⚠️ Aktiv ogohlantirishlar: <b>{warns_count}</b>\n"
        f"🧮 Captcha kutilmoqda: <b>{captcha_pending}</b>\n\n"
        f"⚙️ Anti-Spam: {'✅' if s['anti_spam'] else '❌'} | "
        f"Anti-Link: {'✅' if s['anti_link'] else '❌'}\n"
        f"⚙️ Captcha: {'✅' if s['captcha_enabled'] else '❌'} | "
        f"Tungi rejim: {'✅' if s['night_mode'] else '❌'}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
#  ASOSIY XABAR HANDLER
# ════════════════════════════════════════════════════════════
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha xabarlarni kuzatuvchi asosiy handler."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return

    # Shaxsiy chatda ishlamasin
    if update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    s = get_settings(chat_id)

    # ═══ SANOQCHI — adminlar ham hisoblanadi ═══
    if s.get("counter_enabled", True):
        name = get_name(update.effective_user)
        count_message(chat_id, update.effective_user.id, name, update.message)

    # Admin xabarlarini qorovuldan o'tkazib yuborish
    try:
        if await is_admin(update, context):
            return
    except Exception:
        return

    # Bot admin ekanligini tekshirish
    try:
        if not await is_bot_admin(update, context):
            return
    except Exception:
        return

    # 1. Captcha tekshiruvi
    if await on_message_captcha_check(update, context):
        return

    # 2. Tungi rejim
    if await check_night_mode(update, context):
        return

    # 3. Reklama tozalash (yangi!)
    if await check_ad_comprehensive(update, context, s, add_log, get_name):
        return

    # 4. Forward tekshiruvi
    if await check_forward(update, context):
        return

    # 5. Link tekshiruvi
    if await check_link(update, context):
        return

    # 6. Bad words tekshiruvi
    if await check_bad_words(update, context):
        return

    # 7. Arab yozuvi tekshiruvi
    if await check_arabic(update, context):
        return

    # 8. Yangi a'zo media cheklovi
    if await check_new_member_media(update, context):
        return

    # 9. Sticker spam
    if await check_sticker_spam(update, context):
        return

    # 10. Spam (flood) tekshiruvi
    if await check_spam(update, context):
        return


# ════════════════════════════════════════════════════════════
#  SANAYDI BOT — GURUH/KANAL ODAM YIG'ISH MODULI
# ════════════════════════════════════════════════════════════

async def cmd_sanaydi_guruh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhga odam yig'ishni yoqish va invite link yaratish."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    name = get_name(user)

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return

    try:
        # Invite link yaratish
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=chat_id,
            name=f"Sanaydi_{user.id}",
            creates_join_request=False,
        )
        invite_link = link_obj.invite_link
        # Link → user_id ni saqlash
        sanaydi_invite_links[chat_id][invite_link] = user.id
        sanaydi_guruh_mode[chat_id] = True
        # Ma'lumot yaratish (0 dan boshlash emas, avvalgisini saqlaymiz)
        sanaydi_get_data(chat_id, user.id, name)

        text = (
            f"✅ <b>Guruhga odam yig'ish yoqildi!</b>\n\n"
            f"👥 Quyidagi havolani ulashing:\n"
            f"🔗 {invite_link}\n\n"
            f"📊 Havola orqali qo'shilganlar sizning hisobingizga yoziladi!\n"
            f"📈 Natijani ko'rish: /meni"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}\nBot guruhda admin bo'lishi kerak!")


async def cmd_sanaydi_guruh_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhga odam yig'ishni o'chirish."""
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    sanaydi_guruh_mode[chat_id] = False
    await update.message.reply_text(
        "❌ <b>Guruhga odam yig'ish o'chirildi!</b>", parse_mode=ParseMode.HTML
    )


async def cmd_sanaydi_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanalga odam yig'ishni yoqish."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    name = get_name(user)

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Foydalanish: /kanal @kanalingiz_useri\nMasalan: /kanal @mening_kanalim"
        )
        return

    kanal_username = context.args[0]
    if not kanal_username.startswith("@"):
        kanal_username = "@" + kanal_username

    if not await is_bot_admin(update, context):
        await update.message.reply_text(MESSAGES["bot_not_admin"], parse_mode=ParseMode.HTML)
        return

    try:
        # Kanal uchun invite link yaratish
        kanal_chat = await context.bot.get_chat(kanal_username)
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=kanal_chat.id,
            name=f"Sanaydi_{user.id}",
            creates_join_request=False,
        )
        invite_link = link_obj.invite_link
        sanaydi_invite_links[kanal_chat.id][invite_link] = user.id
        sanaydi_kanal_mode[chat_id] = kanal_username
        sanaydi_get_data(chat_id, user.id, name)

        text = (
            f"✅ <b>Kanalga odam yig'ish yoqildi!</b>\n\n"
            f"📣 Kanal: <b>{kanal_username}</b>\n"
            f"🔗 Havola:\n{invite_link}\n\n"
            f"📊 Bu havola orqali qo'shilganlar sizning hisobingizga yoziladi!\n"
            f"📈 Natijani ko'rish: /meni"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Xatolik: {e}\n\n"
            f"Tekshiring:\n"
            f"• Kanal username to'g'rimi?\n"
            f"• Bot kanalda admin ekanligini"
        )


async def cmd_sanaydi_kanal_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kanalga odam yig'ishni o'chirish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    sanaydi_kanal_mode.pop(chat_id, None)
    await update.message.reply_text(
        "❌ <b>Kanalga odam yig'ish o'chirildi!</b>", parse_mode=ParseMode.HTML
    )


async def cmd_sanaydi_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchiga bal qo'shish (faqat adminlar uchun)."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Foydalanish: Foydalanuvchi xabariga reply qilib /bal <son> yuboring.\nMasalan: /bal 5"
        )
        return

    if not context.args:
        await update.message.reply_text("❌ Foydalanish: /bal <son>\nMasalan: /bal 5")
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Son kiriting! Masalan: /bal 5")
        return

    target = update.message.reply_to_message.from_user
    name = get_name(target)
    data = sanaydi_get_data(chat_id, target.id, name)
    data["bal"] += amount
    data["count"] += amount

    text = (
        f"🎁 <b>{name}</b> ga <b>+{amount}</b> bal qo'shildi!\n\n"
        f"📊 Jami qo'shgan odamlar: <b>{data['count']}</b>\n"
        f"🎯 Bonus ballar: <b>{data['bal']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    add_log(chat_id, "BAL_ADDED", name, get_name(update.effective_user), f"+{amount} bal")


async def cmd_sanaydi_meni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'z referral statistikasini ko'rish."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    name = get_name(user)

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    data = sanaydi_get_data(chat_id, user.id, name)

    kanal = sanaydi_kanal_mode.get(chat_id, "—")
    guruh_status = "✅ Yoqiq" if sanaydi_guruh_mode.get(chat_id) else "❌ O'chiq"

    text = (
        f"📊 <b>{name}</b> ning statistikasi:\n\n"
        f"👥 Guruhga qo'shgan: <b>{data['count']}</b> odam\n"
        f"🎁 Bonus ballar: <b>{data['bal']}</b>\n\n"
        f"⚙️ Guruh rejimi: {guruh_status}\n"
        f"📣 Kanal: <b>{kanal}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_sanaydi_sizni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boshqa foydalanuvchining referral statistikasini ko'rish."""
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    name = get_name(target)
    data = sanaydi_get_data(chat_id, target.id, name)

    text = (
        f"📈 <b>{name}</b> ning statistikasi:\n\n"
        f"👥 Guruhga qo'shgan: <b>{data['count']}</b> odam\n"
        f"🎁 Bonus ballar: <b>{data['bal']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_sanaydi_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eng ko'p odam qo'shgan 10 talik."""
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    users = sanaydi_data.get(chat_id, {})
    if not users:
        await update.message.reply_text("📊 Hozircha hech kim odam qo'shmagan.")
        return

    sorted_users = sorted(users.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Eng ko'p odam qo'shganlar:</b>\n"]

    for i, (uid, data) in enumerate(sorted_users):
        if data["count"] == 0:
            continue
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        bal_text = f" (+{data['bal']} bal)" if data["bal"] > 0 else ""
        lines.append(f"{medal} {data['name']} — <b>{data['count']}</b> odam{bal_text}")

    if len(lines) == 1:
        await update.message.reply_text("📊 Hozircha hech kim odam qo'shmagan.")
        return

    total = sum(d["count"] for d in users.values())
    lines.append(f"\n📈 Jami qo'shilgan odamlar: <b>{total}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_sanaydi_nol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi ma'lumotini 0 ga tushirish."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(MESSAGES["no_reply"], parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user
    name = get_name(target)

    if target.id in sanaydi_data.get(chat_id, {}):
        sanaydi_data[chat_id][target.id]["count"] = 0
        sanaydi_data[chat_id][target.id]["bal"] = 0

    await update.message.reply_text(
        f"🪓 <b>{name}</b> ning ma'lumoti 0 ga tushirildi.", parse_mode=ParseMode.HTML
    )
    add_log(chat_id, "SANAYDI_NOL", name, get_name(update.effective_user))


async def cmd_sanaydi_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha odam qo'shganlar ma'lumotini tozalash."""
    chat_id = update.effective_chat.id

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    count = len(sanaydi_data.get(chat_id, {}))
    sanaydi_data[chat_id] = {}
    sanaydi_invite_links[chat_id] = {}

    await update.message.reply_text(
        f"🗑 <b>{count}</b> ta foydalanuvchining barcha ma'lumotlari tozalandi!",
        parse_mode=ParseMode.HTML,
    )
    add_log(chat_id, "SANAYDI_DEL_ALL", "Hammasi", get_name(update.effective_user))


async def on_chat_member_sanaydi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Yangi a'zo qo'shilganda kim taklif qilganini aniqlash va hisobga olish.
    ChatMemberHandler orqali ishlaydi.
    """
    result: ChatMemberUpdated = update.chat_member

    # Faqat qo'shilishni kuzatamiz
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    # Faqat JOINED holatini ushlash
    joined = (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, "kicked")
        and new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )

    if not joined:
        return

    chat_id = result.chat.id
    new_user = result.new_chat_member.user

    # Bot bo'lsa o'tkazib yuborish
    if new_user.is_bot:
        return

    # Invite link orqali kim qo'shganini aniqlash
    if result.invite_link:
        link_str = result.invite_link.invite_link
        inviter_id = sanaydi_invite_links.get(chat_id, {}).get(link_str)

        if inviter_id:
            # Inviterni topish
            try:
                inviter_member = await context.bot.get_chat_member(chat_id, inviter_id)
                inviter_name = get_name(inviter_member.user)
            except Exception:
                inviter_name = f"User{inviter_id}"

            data = sanaydi_get_data(chat_id, inviter_id, inviter_name)
            data["count"] += 1

            logger.info(f"✅ {inviter_name} +1 odam qo'shdi (jami: {data['count']})")
        return

    # Agar kim qo'shganini bilsak (from_user orqali)
    if result.from_user and result.from_user.id != new_user.id:
        inviter = result.from_user
        inviter_name = get_name(inviter)

        # Guruh rejimi yoqiq bo'lsa hisoblaymiz
        if sanaydi_guruh_mode.get(chat_id):
            data = sanaydi_get_data(chat_id, inviter.id, inviter_name)
            data["count"] += 1
            logger.info(f"✅ {inviter_name} +1 odam qo'shdi (jami: {data['count']})")


# ════════════════════════════════════════════════════════════
#  YANGI KOMANDALAR: /info, /reload, /config
# ════════════════════════════════════════════════════════════

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchi haqida to'liq ma'lumot.
    Foydalanish: /info | /info @username | /info <user_id> | yoki reply
    """
    chat_id = update.effective_chat.id
    target_user = None
    target_member = None

    # 1. Reply orqali
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        try:
            target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        except Exception:
            pass

    # 2. Argument orqali (username yoki ID)
    elif context.args:
        arg = context.args[0]
        try:
            if arg.startswith("@"):
                chat_obj = await context.bot.get_chat(arg)
                target_user = chat_obj
                try:
                    target_member = await context.bot.get_chat_member(chat_id, chat_obj.id)
                except Exception:
                    pass
            else:
                uid = int(arg)
                target_member = await context.bot.get_chat_member(chat_id, uid)
                target_user = target_member.user
        except Exception as e:
            await update.message.reply_text(f"❌ Foydalanuvchi topilmadi: {e}")
            return

    # 3. O'zi haqida
    else:
        target_user = update.effective_user
        try:
            target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        except Exception:
            pass

    if not target_user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    # Status tarjimasi
    status_map = {
        "creator": "👑 Guruh egasi",
        "administrator": "⭐️ Admin",
        "member": "👤 A'zo",
        "restricted": "🔇 Cheklangan",
        "left": "🚪 Chiqib ketgan",
        "kicked": "🚫 Bloklangan",
    }
    status_str = "❓ Noma'lum"
    if target_member:
        status_str = status_map.get(target_member.status, target_member.status)

    # Username
    username_str = f"@{target_user.username}" if getattr(target_user, "username", None) else "—"

    # Warn hisob
    warns_count = user_warns[chat_id].get(target_user.id, 0)
    s = get_settings(chat_id)
    max_warns = s.get("max_warns", 3)

    # Sanaydi statistikasi
    sanaydi_stats = sanaydi_data.get(chat_id, {}).get(target_user.id, {})
    invited_count = sanaydi_stats.get("count", 0)

    # Til
    lang = getattr(target_user, "language_code", None) or "—"

    # Bot yoki yo'q
    is_bot_user = "🤖 Ha" if getattr(target_user, "is_bot", False) else "👤 Yo'q"

    # Premium
    is_premium = "💎 Ha" if getattr(target_user, "is_premium", False) else "—"

    # To'liq ism
    full_name = get_name(target_user)

    text = (
        f"👤 <b>Foydalanuvchi Ma'lumoti</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪪 <b>Ism:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username_str}\n"
        f"🆔 <b>User ID:</b> <code>{target_user.id}</code>\n"
        f"🤖 <b>Bot:</b> {is_bot_user}\n"
        f"💎 <b>Premium:</b> {is_premium}\n"
        f"🌐 <b>Til:</b> {lang}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Guruh holati:</b> {status_str}\n"
        f"⚠️ <b>Ogohlantirishlar:</b> {warns_count}/{max_warns}\n"
        f"👥 <b>Qo'shgan odamlar:</b> {invited_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Profil:</b> "
        f"<a href='tg://user?id={target_user.id}'>{full_name}</a>"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Adminlar ro'yxatini Telegram'dan qayta yuklash va yangilash.
    /reload — guruh adminlarini bot xotirasiga yuklaydi.
    """
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text(MESSAGES["not_admin"], parse_mode=ParseMode.HTML)
        return

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_list = []
        lines = ["👑 <b>Adminlar ro'yxati yangilandi!</b>\n"]

        for i, admin in enumerate(admins, 1):
            if admin.user.is_bot:
                continue
            name = get_name(admin.user)
            status_icon = "👑" if admin.status == ChatMemberStatus.OWNER else "⭐️"
            lines.append(f"{i}. {status_icon} <b>{name}</b> — <code>{admin.user.id}</code>")
            admin_list.append(admin.user.id)

        lines.append(f"\n📊 Jami adminlar: <b>{len(admin_list)}</b>")
        lines.append(f"🔄 Yangilandi: <b>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</b>")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        add_log(chat_id, "RELOAD_ADMINS", "—", get_name(update.effective_user))

    except Exception as e:
        await update.message.reply_text(
            f"❌ Xatolik: {e}\nBot admin bo'lishi kerak!"
        )


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /config — bot sozlamalar panelini ko'rsatish (/settings ga alias).
    Bir xil funksiya, faqat buyruq nomi farq qiladi.
    """
    await cmd_settings(update, context)


async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bot yangi guruhga qo'shilganda yoki admin qilinganda shablon xabar yuborish.
    MY_CHAT_MEMBER handler orqali ishlaydi.
    """
    result = update.my_chat_member
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    chat = update.effective_chat

    # Faqat guruh va superguruhda ishlash
    if chat.type not in ("group", "supergroup"):
        return

    # Bot yangi qo'shildi (left/kicked → member/admin)
    bot_joined = (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, "kicked")
        and new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )

    # Bot admin qilindi (member → admin)
    bot_promoted = (
        old_status == ChatMemberStatus.MEMBER
        and new_status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )

    if not (bot_joined or bot_promoted):
        return

    # Bot nomi
    bot_username = f"@{context.bot.username}" if context.bot.username else "bot"

    text = (
        f"Salom👋\n\n"
        f"Men guruhingizni 24soat davomida o'zbekcha va arabcha "
        f"reklamalarni, ssilkalarni va join, left kabi "
        f"(kirdi, chiqdilarni) o'chirib tartibni saqlayman 👨🏻‍✈️\n\n"
        f"Man to'liq ishlashim uchun guruhizga qo'shib "
        f"<b>ADMIN</b> berishiz kerak😄\n\n"
        f"/help - Guruhga odam ko'paytirish uchun Batafsil Qo'llanma ☑️"
    )

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"✅ Shablon xabar yuborildi: {chat.title} ({chat.id})")
    except Exception as e:
        logger.warning(f"❌ Shablon xabar yuborishda xatolik: {e}")


# ════════════════════════════════════════════════════════════
#  BOT ISHGA TUSHIRILISHI
# ════════════════════════════════════════════════════════════
def main():
    """Botni ishga tushirish."""
    if not BOT_TOKEN:
        print("=" * 50)
        print("❌ BOT_TOKEN environment variable topilmadi!")
        print("Railway'da BOT_TOKEN va SECRET_OWNER_ID ni sozlang.")
        print("Token olish: https://t.me/BotFather")
        print("=" * 50)
        return

    print("🛡️ Universal Qorovul Bot ishga tushmoqda...")

    app = Application.builder().token(BOT_TOKEN).build()

    # ─── Qorovul buyruqlari ───
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("nightmode", cmd_nightmode))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("warns", cmd_warns))
    app.add_handler(CommandHandler("clearwarns", cmd_clearwarns))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("addword", cmd_addword))
    app.add_handler(CommandHandler("delword", cmd_delword))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # ─── Admin boshqaruvi ───
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("admins", cmd_admins))

    # ─── Sanoqchi buyruqlari ───
    app.add_handler(CommandHandler("count", cmd_count))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("toptoday", cmd_toptoday))
    app.add_handler(CommandHandler("topweek", cmd_topweek))
    app.add_handler(CommandHandler("groupstats", cmd_groupstats))

    # ─── Sanaydi Bot buyruqlari ───
    app.add_handler(CommandHandler("guruh", cmd_sanaydi_guruh))
    app.add_handler(CommandHandler("guruh_off", cmd_sanaydi_guruh_off))
    app.add_handler(CommandHandler("kanal", cmd_sanaydi_kanal))
    app.add_handler(CommandHandler("kanal_off", cmd_sanaydi_kanal_off))
    app.add_handler(CommandHandler("bal", cmd_sanaydi_bal))
    app.add_handler(CommandHandler("meni", cmd_sanaydi_meni))
    app.add_handler(CommandHandler("sizni", cmd_sanaydi_sizni))
    app.add_handler(CommandHandler("sanaydi_top", cmd_sanaydi_top))
    app.add_handler(CommandHandler("nol", cmd_sanaydi_nol))
    app.add_handler(CommandHandler("del", cmd_sanaydi_del))

    # ─── Info / Reload / Config buyruqlari ───
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("config", cmd_config))

    # ─── Sanaydi: yangi a'zo kuzatuv handler ───
    app.add_handler(ChatMemberHandler(on_chat_member_sanaydi, ChatMemberHandler.CHAT_MEMBER))

    # ─── Bot yangi guruhga qo'shilganda shablon xabar ───
    app.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

    # ─── Callback handler ───
    app.add_handler(CallbackQueryHandler(settings_callback))

    # ─── Yangi a'zo handler ───
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))

    # ─── Asosiy xabar handler ───
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
        on_message,
    ))

    print("✅ Universal Qorovul Bot muvaffaqiyatli ishga tushdi!")
    print("📌 Botni guruhga qo'shing va admin qiling.")
    print("🛡️ Qorovul | 📢 Reklama Tozalash | 📊 Sanoqchi | 👥 Sanaydi")
    print("⚙️ Sozlamalar: /settings")
    print("📋 Buyruqlar: /help | /menu")
    print("-" * 50)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
