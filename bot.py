import os
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

LINK_PATTERN = re.compile(
    r"(https?://|t\.me/|telegram\.me/|@\w+)",
    re.IGNORECASE
)

async def delete_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.effective_chat
    user = update.effective_user

    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status in ["administrator", "creator"]:
        return

    text = update.message.text or update.message.caption or ""

    if LINK_PATTERN.search(text):
        try:
            await update.message.delete()
        except:
            pass

app = Application.builder().token(TOKEN).build()

app.add_handler(
    MessageHandler(filters.TEXT | filters.CaptionRegex(".*"), delete_ads)
)

app.run_polling()
