import random

from telegram import Update
from telegram.ext import ContextTypes

import database as db


async def game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🕹️ MINI GAMES\n\n"
        "/coinflip <amount> heads|tails - 50/50 double or nothing\n"
        "/dice <amount> - roll a dice, 4-6 wins double\n"
    )
    await update.message.reply_text(text)


async def coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /coinflip <amount> heads|tails")
        return

    amount = int(context.args[0])
    choice = context.args[1].lower()
    if choice not in ("heads", "tails"):
        await update.message.reply_text("Choose heads or tails.")
        return

    user = await db.get_user(tg_user.id, tg_user.username or "")
    if amount <= 0 or amount > user["balance"]:
        await update.message.reply_text("Invalid bet amount.")
        return

    result = random.choice(["heads", "tails"])
    if result == choice:
        await db.update_balance(tg_user.id, amount)
        await update.message.reply_text(f"🪙 It's {result}! You won {amount} coins!")
    else:
        await db.update_balance(tg_user.id, -amount)
        await update.message.reply_text(f"🪙 It's {result}! You lost {amount} coins.")


async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /dice <amount>")
        return

    amount = int(context.args[0])
    user = await db.get_user(tg_user.id, tg_user.username or "")
    if amount <= 0 or amount > user["balance"]:
        await update.message.reply_text("Invalid bet amount.")
        return

    roll = random.randint(1, 6)
    if roll >= 4:
        await db.update_balance(tg_user.id, amount)
        await update.message.reply_text(f"🎲 Rolled {roll}! You won {amount} coins!")
    else:
        await db.update_balance(tg_user.id, -amount)
        await update.message.reply_text(f"🎲 Rolled {roll}! You lost {amount} coins.")
