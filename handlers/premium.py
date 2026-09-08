import datetime

from telegram import Update
from telegram.ext import ContextTypes

import database as db

PREMIUM_COST_GEMS = 50
PREMIUM_DURATION_DAYS = 30


async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")

    if user["gems"] < PREMIUM_COST_GEMS:
        await update.message.reply_text(
            f"💎 You need {PREMIUM_COST_GEMS} gems for premium. You have {user['gems']:.2f}."
        )
        return

    now = datetime.datetime.utcnow()
    current = user.get("premium_until")
    base = current if current and current > now else now
    new_until = base + datetime.timedelta(days=PREMIUM_DURATION_DAYS)

    await db.increment_field(tg_user.id, "gems", -PREMIUM_COST_GEMS)
    await db.set_field(tg_user.id, "premium_until", new_until)
    await update.message.reply_text(
        f"💗 Premium activated until {new_until.strftime('%Y-%m-%d')}!"
    )


async def premium_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    until = user.get("premium_until")
    now = datetime.datetime.utcnow()
    if until and until > now:
        await update.message.reply_text(f"💗 Premium active until {until.strftime('%Y-%m-%d')}.")
    else:
        await update.message.reply_text(
            f"You don't have premium. Use /buypremium ({PREMIUM_COST_GEMS} gems) to activate it."
        )


async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💗 PREMIUM\n\n"
        f"/buypremium - {PREMIUM_COST_GEMS} gems for {PREMIUM_DURATION_DAYS} days\n"
        "/premiumstatus - check your premium expiry\n"
    )
    await update.message.reply_text(text)
