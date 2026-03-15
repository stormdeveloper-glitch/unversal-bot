"""
🎯 DECORATORS — Admin tekshiruvi va xato ushlagichlar
"""
import functools
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MESSAGES
from utils.helpers import is_admin, is_bot_admin

logger = logging.getLogger(__name__)


def admin_only(func):
    """Faqat adminlar uchun buyruq. Admin bo'lmasa xabar yuboriladi."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await is_admin(update, context):
            await update.message.reply_text(
                MESSAGES["not_admin"], parse_mode=ParseMode.HTML
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def group_only(func):
    """Faqat guruhlarda ishlaydigan buyruq."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                MESSAGES["group_only"], parse_mode=ParseMode.HTML
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def requires_reply(func):
    """Buyruq reply xabar talab qiladi."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.message.reply_to_message:
            await update.message.reply_text(
                MESSAGES["no_reply"], parse_mode=ParseMode.HTML
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def handle_errors(func):
    """Barcha xatolarni ushlab, foydalanuvchiga xabar beradi."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"Xatolik [{func.__name__}]: {e}\n{traceback.format_exc()}"
            )
            if update and update.message:
                await update.message.reply_text(
                    f"⚠️ Xatolik yuz berdi: <code>{type(e).__name__}</code>\n"
                    f"Iltimos, qaytadan urinib ko'ring.",
                    parse_mode=ParseMode.HTML,
                )
    return wrapper
