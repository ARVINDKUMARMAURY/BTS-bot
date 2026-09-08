from telegram import Update
from telegram.ext import ContextTypes

import database as db

# Exchange rate: coins -> gems
COINS_PER_GEM = 500


async def gems_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    await update.message.reply_text(f"💎 You have {user['gems']:.2f} gems.")


async def exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/exchange <amount_of_coins> -> converts coins to gems."""
    tg_user = update.effective_user
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(f"Usage: /exchange <coins> ({COINS_PER_GEM} coins = 1 gem)")
        return

    coins = int(context.args[0])
    user = await db.get_user(tg_user.id, tg_user.username or "")
    if coins > user["balance"]:
        await update.message.reply_text("You don't have that many coins.")
        return

    gems_gained = coins / COINS_PER_GEM
    await db.update_balance(tg_user.id, -coins)
    await db.increment_field(tg_user.id, "gems", gems_gained)
    await update.message.reply_text(f"💎 Exchanged {coins} coins for {gems_gained:.2f} gems.")


async def gems_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 GEMS\n\n"
        "/gems - check your gem balance\n"
        f"/exchange <coins> - convert coins to gems ({COINS_PER_GEM} coins = 1 gem)\n"
        "Gems are used for premium and special powers.\n"
    )
    await update.message.reply_text(text)
