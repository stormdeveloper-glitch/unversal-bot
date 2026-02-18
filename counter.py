"""
📊 SANOQCHI (COUNTER) MODULI
Xabar sanoqchisi, top foydalanuvchilar, statistika
"""
import time
from collections import defaultdict
from datetime import datetime, timezone
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# ═══ DATA ═══
# { chat_id: { user_id: { "name": str, "total": int, "daily": {date: int}, "weekly": {week: int} } } }
user_message_counts: dict[int, dict[int, dict]] = defaultdict(dict)
# { chat_id: { user_id: join_time } }
member_join_dates: dict[int, dict[int, float]] = defaultdict(dict)


def _get_user_data(chat_id: int, user_id: int, name: str) -> dict:
    if user_id not in user_message_counts[chat_id]:
        user_message_counts[chat_id][user_id] = {
            "name": name, "total": 0, "daily": defaultdict(int), "weekly": defaultdict(int),
            "text": 0, "photo": 0, "video": 0, "voice": 0, "sticker": 0, "other": 0,
        }
    data = user_message_counts[chat_id][user_id]
    data["name"] = name
    return data


def count_message(chat_id: int, user_id: int, name: str, msg) -> dict:
    """Xabarni hisoblash."""
    data = _get_user_data(chat_id, user_id, name)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week = now.strftime("%Y-W%W")

    data["total"] += 1
    data["daily"][today] = data["daily"].get(today, 0) + 1
    data["weekly"][week] = data["weekly"].get(week, 0) + 1

    if msg.text: data["text"] += 1
    elif msg.photo: data["photo"] += 1
    elif msg.video: data["video"] += 1
    elif msg.voice or msg.video_note: data["voice"] += 1
    elif msg.sticker: data["sticker"] += 1
    else: data["other"] += 1

    return data


def register_member(chat_id: int, user_id: int):
    member_join_dates[chat_id][user_id] = time.time()


async def cmd_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining xabar sonini ko'rsatish."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    uid = user.id
    name = user.first_name or user.username or "Noma'lum"
    data = _get_user_data(chat_id, uid, name)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week = now.strftime("%Y-W%W")

    today_count = data["daily"].get(today, 0)
    week_count = data["weekly"].get(week, 0)

    text = (
        f"📊 <b>{name}</b> ning xabar statistikasi:\n\n"
        f"📝 Jami xabarlar: <b>{data['total']}</b>\n"
        f"📅 Bugun: <b>{today_count}</b>\n"
        f"📆 Bu hafta: <b>{week_count}</b>\n\n"
        f"<b>Xabar turlari:</b>\n"
        f"├ 💬 Matn: <b>{data['text']}</b>\n"
        f"├ 📷 Rasm: <b>{data['photo']}</b>\n"
        f"├ 🎬 Video: <b>{data['video']}</b>\n"
        f"├ 🎤 Ovozli: <b>{data['voice']}</b>\n"
        f"├ 🎭 Sticker: <b>{data['sticker']}</b>\n"
        f"└ 📎 Boshqa: <b>{data['other']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top faol a'zolar."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    users = user_message_counts.get(chat_id, {})
    if not users:
        await update.message.reply_text("📊 Hozircha statistika yo'q.")
        return

    limit = 10
    if context.args:
        try: limit = min(int(context.args[0]), 50)
        except: pass

    sorted_users = sorted(users.items(), key=lambda x: x[1]["total"], reverse=True)[:limit]
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Top faol a'zolar:</b>\n"]

    for i, (uid, data) in enumerate(sorted_users):
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        lines.append(f"{medal} {data['name']} — <b>{data['total']}</b> xabar")

    total_msgs = sum(d["total"] for d in users.values())
    lines.append(f"\n📈 Jami guruh xabarlari: <b>{total_msgs}</b>")
    lines.append(f"👥 Faol a'zolar soni: <b>{len(users)}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_toptoday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bugungi top a'zolar."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    users = user_message_counts.get(chat_id, {})
    if not users:
        await update.message.reply_text("📊 Hozircha statistika yo'q.")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_data = [(uid, d["name"], d["daily"].get(today, 0)) for uid, d in users.items() if d["daily"].get(today, 0) > 0]
    today_data.sort(key=lambda x: x[2], reverse=True)

    if not today_data:
        await update.message.reply_text("📊 Bugun hali xabar yuborilmagan.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"📅 <b>Bugungi top ({today}):</b>\n"]
    for i, (uid, name, count) in enumerate(today_data[:10]):
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        lines.append(f"{medal} {name} — <b>{count}</b> xabar")

    total = sum(c for _, _, c in today_data)
    lines.append(f"\n📈 Bugungi jami: <b>{total}</b> xabar")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_topweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalik top a'zolar."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    users = user_message_counts.get(chat_id, {})
    if not users:
        await update.message.reply_text("📊 Hozircha statistika yo'q.")
        return

    week = datetime.now(timezone.utc).strftime("%Y-W%W")
    week_data = [(uid, d["name"], d["weekly"].get(week, 0)) for uid, d in users.items() if d["weekly"].get(week, 0) > 0]
    week_data.sort(key=lambda x: x[2], reverse=True)

    if not week_data:
        await update.message.reply_text("📊 Bu hafta hali xabar yuborilmagan.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["📆 <b>Haftalik top:</b>\n"]
    for i, (uid, name, count) in enumerate(week_data[:10]):
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        lines.append(f"{medal} {name} — <b>{count}</b> xabar")

    total = sum(c for _, _, c in week_data)
    lines.append(f"\n📈 Haftalik jami: <b>{total}</b> xabar")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'z statistikasini ko'rish."""
    await cmd_count(update, context)


async def cmd_groupstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh umumiy statistikasi."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    try:
        member_count = await context.bot.get_chat_member_count(chat_id)
    except:
        member_count = "?"

    users = user_message_counts.get(chat_id, {})
    total = sum(d["total"] for d in users.values())
    active = len(users)

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week = now.strftime("%Y-W%W")
    today_total = sum(d["daily"].get(today, 0) for d in users.values())
    week_total = sum(d["weekly"].get(week, 0) for d in users.values())

    type_stats = defaultdict(int)
    for d in users.values():
        for t in ("text", "photo", "video", "voice", "sticker", "other"):
            type_stats[t] += d.get(t, 0)

    text = (
        f"📊 <b>Guruh Statistikasi</b>\n\n"
        f"👥 A'zolar soni: <b>{member_count}</b>\n"
        f"💬 Faol a'zolar: <b>{active}</b>\n"
        f"📝 Jami xabarlar: <b>{total}</b>\n"
        f"📅 Bugun: <b>{today_total}</b>\n"
        f"📆 Bu hafta: <b>{week_total}</b>\n\n"
        f"<b>Xabar turlari:</b>\n"
        f"├ 💬 Matn: <b>{type_stats['text']}</b>\n"
        f"├ 📷 Rasm: <b>{type_stats['photo']}</b>\n"
        f"├ 🎬 Video: <b>{type_stats['video']}</b>\n"
        f"├ 🎤 Ovozli: <b>{type_stats['voice']}</b>\n"
        f"├ 🎭 Sticker: <b>{type_stats['sticker']}</b>\n"
        f"└ 📎 Boshqa: <b>{type_stats['other']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
