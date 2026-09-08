from telegram import Update
from telegram.ext import ContextTypes

ACTIONS = {
    "hug": "🤗 {sender} hugs {target}!",
    "slap": "👋 {sender} slaps {target}!",
    "pat": "🖐️ {sender} pats {target} on the head!",
    "kiss": "😘 {sender} kisses {target}!",
    "poke": "👉 {sender} pokes {target}!",
}


def make_handler(action: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        sender = update.effective_user
        if not update.message.reply_to_message:
            await update.message.reply_text(f"Reply to someone's message to /{action} them.")
            return
        target = update.message.reply_to_message.from_user
        text = ACTIONS[action].format(sender=sender.full_name, target=target.full_name)
        await update.message.reply_text(text)

    return handler


async def interactions_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💞 INTERACTIONS\n\n" + "\n".join(f"/{a} - reply to someone" for a in ACTIONS)
    await update.message.reply_text(text)
