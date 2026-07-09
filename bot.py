"""
Anti-reklama Telegram bot — Render.com uchun (webhook rejimi)
---------------------------------------------------------------
Bu versiya Render'ning "Web Service" talabiga mos: doimiy port tinglaydi
va Telegram xabarlarini webhook orqali qabul qiladi (polling emas).

MUHIM: Token va boshqa maxfiy narsalarni koddan EMAS,
       Render dashboard'idagi "Environment Variables" bo'limidan beramiz.
"""

import logging
import os
import re
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(name)

# ====================== SOZLAMALAR ======================

# Tokenni Render Environment Variables'dan o'qiymiz (koddа yozmaymiz!)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Render dashboard -> Environment -> "
        "BOT_TOKEN nomli o'zgaruvchi qo'shing."
    )

# Render avtomatik beradigan port va domen
PORT = int(os.environ.get("PORT", "10000"))
RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if not RENDER_HOSTNAME:
    raise RuntimeError(
        "RENDER_EXTERNAL_HOSTNAME topilmadi! Bu Render'da avtomatik "
        "beriladi — faqat kodni Render'ga deploy qilganda ishlaydi, "
        "lokal kompyuterda emas."
    )
WEBHOOK_URL = f"https://{RENDER_HOSTNAME}/{BOT_TOKEN}"

# Reklama deb hisoblanadigan so'zlar (kerak bo'lsa moslashtiring)
BLOCKED_KEYWORDS = [
    "reklama",
    "sotiladi",
    "chegirma",
    "aksiya",
    "obuna bo'ling",
    "sotib oling",
    "buyurtma",
    "заказ",
    "скидка",
    "продажа",
    "подпишись",
]

BLOCK_LINKS = True
LINK_PATTERN = re.compile(
    r"(https?://\S+|t\.me/\S+|www\.\S+|@[a-zA-Z0-9_]{5,})", re.IGNORECASE
)

WARN_LIMIT = 3
user_warnings: dict[int, int] = {}


# ====================== YORDAMCHI FUNKSIYALAR ======================

def is_ad_message(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()

    for word in BLOCKED_KEYWORDS:
        if word in lowered:
            return True

    if BLOCK_LINKS and LINK_PATTERN.search(text):
        return True

    return False


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        logger.warning(f"Admin holatini tekshirib bo'lmadi: {e}")
        return False


# ====================== ASOSIY HANDLER ======================

async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None or message.text is None:
        return

    if await is_user_admin(update, context):
        return

    if is_ad_message(message.text):
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Xabarni o'chirib bo'lmadi: {e}")
            return

        user_id = update.effective_user.id
        user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
        count = user_warnings[user_id]

        warn_text = (
            f"⚠️ {update.effective_user.mention_html()}, reklama/spam xabar "
            f"o'chirildi. ({count}/{WARN_LIMIT})"
        )
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=warn_text, parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Ogohlantirish yuborilmadi: {e}")

if WARN_LIMIT and count >= WARN_LIMIT:
            try:
                await context.bot.restrict_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🚫 {update.effective_user.mention_html()} jimlatildi (ko'p marta reklama tashlagani uchun).",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Foydalanuvchini jimlatib bo'lmadi: {e}")


# ====================== ISHGA TUSHIRISH (WEBHOOK) ======================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message)
    )

    logger.info(f"Webhook manzili: {WEBHOOK_URL}")
    logger.info(f"Port: {PORT}")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )


if name == "main":
    main()
