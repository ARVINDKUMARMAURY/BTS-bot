import time

from telegram import Update
from telegram.ext import ContextTypes


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.monotonic()
    msg = await update.message.reply_text("Pinging...")
    elapsed_ms = (time.monotonic() - start) * 1000
    await msg.edit_text(f"🏓 Pong! {elapsed_ms:.0f}ms")


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    chat = update.effective_chat
    text = f"👤 Your ID: {tg_user.id}\n💬 Chat ID: {chat.id}"
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        text += f"\n🎯 Replied user ID: {target.id}"
    await update.message.reply_text(text)


async def utilities_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔧 UTILITIES\n\n"
        "/ping - check bot latency\n"
        "/id - get your Telegram ID / chat ID\n"
    )
    await update.message.reply_text(text)
