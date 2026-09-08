import hashlib
import random
import datetime

from telegram import Update
from telegram.ext import ContextTypes

import database as db

ACTIONS = {
    "kiss": "😘 {sender} kisses {target}!",
    "hug": "🤗 {sender} hugs {target}!",
    "slap": "👋 {sender} slaps {target}!",
    "punch": "👊 {sender} punches {target}!",
    "bite": "😬 {sender} bites {target}!",
    "murder": "🔪 {sender} murders {target}! (relax, it's fake)",
    "love": "❤️ {sender} shows love to {target}!",
    "look": "👀 {sender} looks at {target}...",
    "pat": "🖐️ {sender} pats {target} on the head!",
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


def _stable_pct(*parts, salt: str = "") -> int:
    """Deterministic 0-100 'percentage' from the given parts, stable until salt changes."""
    key = "|".join(str(p) for p in parts) + salt
    digest = hashlib.sha256(key.encode()).hexdigest()
    return int(digest, 16) % 101


async def crush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to someone's message to /crush check them.")
        return
    sender = update.effective_user
    target = update.message.reply_to_message.from_user
    pct = _stable_pct(sender.id, target.id, salt="crush")
    await update.message.reply_text(
        f"💘 {target.full_name}'s crush meter on {sender.full_name}: {pct}%"
    )


async def brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else tg_user
    today = datetime.date.today().isoformat()
    pct = _stable_pct(target.id, salt=f"brain-{today}")
    await update.message.reply_text(f"🧠 {target.full_name}'s brain is {pct}% full today.")


async def stupid_meter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else tg_user
    today = datetime.date.today().isoformat()
    pct = _stable_pct(target.id, salt=f"stupid-{today}")
    await update.message.reply_text(f"🤪 {target.full_name} is {pct}% stupid today.")


async def couples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("This only works in groups.")
        return

    members = await db.get_group_members(chat.id)
    if len(members) < 2:
        await update.message.reply_text(
            "Not enough active members seen yet. Chat a bit more in the group and try again."
        )
        return

    pair = random.sample(members, 2)
    a, b = pair[0], pair[1]
    pct = _stable_pct(a["_id"], b["_id"], salt=f"couple-{datetime.date.today()}")
    await update.message.reply_text(
        f"💞 Today's couple: {a['name']} + {b['name']} — {pct}% match!"
    )


async def interactions_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["💞 INTERACTIONS\n"]
    lines += [f"/{a} (reply)" for a in ACTIONS]
    lines.append("/crush (reply) - check replied user's crush meter")
    lines.append("/brain (reply) - check someone's brain")
    lines.append("/stupid_meter (reply) - check how stupid someone is")
    lines.append("/couples - choose random couples from the group")
    await update.message.reply_text("\n".join(lines))
