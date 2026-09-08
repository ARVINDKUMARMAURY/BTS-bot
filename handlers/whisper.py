from telegram import Update
from telegram.ext import ContextTypes


async def whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/whisper <text> as a reply to someone -> bot DMs them the text, group only sees a notice."""
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message and use /whisper <text>.")
        return
    if not context.args:
        await update.message.reply_text("Usage: reply with /whisper <your secret message>")
        return

    sender = update.effective_user
    target = update.message.reply_to_message.from_user
    text = " ".join(context.args)

    try:
        await context.bot.send_message(
            chat_id=target.id,
            text=f"🤫 Whisper from {sender.full_name}:\n\n{text}",
        )
        await update.message.reply_text(f"🤫 Whisper sent to {target.full_name} privately.")
    except Exception:
        await update.message.reply_text(
            "Couldn't deliver — the user needs to have started a DM with the bot first."
        )
