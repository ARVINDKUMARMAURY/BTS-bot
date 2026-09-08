import datetime

from telegram import Update
from telegram.ext import ContextTypes

import database as db

POWERS = {
    "doublesteal": {"cost_gems": 10, "duration_hours": 6, "desc": "Doubles your /kill and /rob steal %"},
    "shield": {"cost_gems": 8, "duration_hours": 12, "desc": "Same as /protect but paid in gems"},
    "luck": {"cost_gems": 5, "duration_hours": 6, "desc": "Reduces /rob fail chance"},
}


async def powers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🦅 POWERS (bought with gems)\n"]
    for name, p in POWERS.items():
        lines.append(f"• /buypower {name} - {p['cost_gems']} gems, {p['duration_hours']}h — {p['desc']}")
    await update.message.reply_text("\n".join(lines))


async def buy_power(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not context.args or context.args[0].lower() not in POWERS:
        names = ", ".join(POWERS.keys())
        await update.message.reply_text(f"Usage: /buypower <name>. Available: {names}")
        return

    power_name = context.args[0].lower()
    power = POWERS[power_name]
    user = await db.get_user(tg_user.id, tg_user.username or "")

    if user["gems"] < power["cost_gems"]:
        await update.message.reply_text(f"💎 You need {power['cost_gems']} gems for {power_name}.")
        return

    until = datetime.datetime.utcnow() + datetime.timedelta(hours=power["duration_hours"])
    await db.increment_field(tg_user.id, "gems", -power["cost_gems"])
    await db.set_field(tg_user.id, f"power_{power_name}_until", until)

    await update.message.reply_text(
        f"🦅 {power_name} activated until {until.strftime('%H:%M UTC')}."
    )
