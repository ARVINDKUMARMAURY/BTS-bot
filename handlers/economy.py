import random
import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import database as db
import config


def _fmt_user(u) -> str:
    return f"@{u['username']}" if u.get("username") else str(u["_id"])


async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    rank = await db.get_rank(tg_user.id)
    text = (
        "📊 YOUR STATS:\n"
        "<blockquote>"
        f"💰 Balance: {user['balance']}\n"
        f"🏆 Rank: {rank}\n"
        f"💎 Gems: {user['gems']:.2f}\n"
        f"🔪 Kills: {user['kills']}"
        "</blockquote>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def pfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    if user.get("pfp_file_id"):
        await update.message.reply_photo(user["pfp_file_id"], caption="👤 Your saved PFP")
    else:
        photos = await context.bot.get_user_profile_photos(tg_user.id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            await db.set_field(tg_user.id, "pfp_file_id", file_id)
            await update.message.reply_photo(file_id, caption="👤 Your PFP")
        else:
            await update.message.reply_text("You don't have a profile photo set on Telegram.")


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    now = datetime.datetime.utcnow()
    last = user.get("last_daily")
    if last and (now - last) < datetime.timedelta(hours=24):
        remaining = datetime.timedelta(hours=24) - (now - last)
        hrs = int(remaining.total_seconds() // 3600)
        mins = int((remaining.total_seconds() % 3600) // 60)
        await update.message.reply_text(f"⏳ Already claimed. Come back in {hrs}h {mins}m.")
        return
    await db.update_balance(tg_user.id, config.DAILY_REWARD)
    await db.set_field(tg_user.id, "last_daily", now)
    await update.message.reply_text(f"🎁 You received {config.DAILY_REWARD} coins! Come back tomorrow.")


async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    now = datetime.datetime.utcnow()
    until = user.get("protected_until")
    if until and until > now:
        await update.message.reply_text(f"🛡️ Already protected until {until.strftime('%H:%M UTC')}.")
        return
    if user["balance"] < config.PROTECTION_COST:
        await update.message.reply_text(f"❌ You need {config.PROTECTION_COST} coins for protection.")
        return
    new_until = now + datetime.timedelta(hours=config.PROTECTION_DURATION_HOURS)
    await db.update_balance(tg_user.id, -config.PROTECTION_COST)
    await db.set_field(tg_user.id, "protected_until", new_until)
    await update.message.reply_text(
        f"🛡️ Protected for {config.PROTECTION_DURATION_HOURS}h (until {new_until.strftime('%H:%M UTC')})."
    )


async def _is_protected(user: dict) -> bool:
    until = user.get("protected_until")
    return bool(until and until > datetime.datetime.utcnow())


async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker_tg = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message you want to /kill.")
        return
    target_tg = update.message.reply_to_message.from_user
    if target_tg.id == attacker_tg.id:
        await update.message.reply_text("You can't kill yourself.")
        return

    attacker = await db.get_user(attacker_tg.id, attacker_tg.username or "")
    target = await db.get_user(target_tg.id, target_tg.username or "")

    if await _is_protected(target):
        await update.message.reply_text(f"🛡️ {_fmt_user(target)} is protected right now. Attack failed.")
        return

    if target["balance"] <= 0:
        await update.message.reply_text(f"{_fmt_user(target)} has nothing to lose.")
        return

    pct = random.uniform(config.KILL_MIN_STEAL_PCT, config.KILL_MAX_STEAL_PCT)
    stolen = max(1, int(target["balance"] * pct))

    await db.update_balance(target_tg.id, -stolen)
    await db.update_balance(attacker_tg.id, stolen)
    await db.increment_field(attacker_tg.id, "kills", 1)

    await update.message.reply_text(
        f"🔪 {_fmt_user(attacker)} killed {_fmt_user(target)} and stole {stolen} coins!"
    )


async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker_tg = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message you want to /rob.")
        return
    target_tg = update.message.reply_to_message.from_user
    if target_tg.id == attacker_tg.id:
        await update.message.reply_text("You can't rob yourself.")
        return

    attacker = await db.get_user(attacker_tg.id, attacker_tg.username or "")
    target = await db.get_user(target_tg.id, target_tg.username or "")

    if await _is_protected(target):
        await update.message.reply_text(f"🛡️ {_fmt_user(target)} is protected right now. Rob failed.")
        return

    # Rob has a fail chance unlike kill
    if random.random() < 0.4:
        await update.message.reply_text(f"🚨 {_fmt_user(attacker)}'s robbery attempt failed!")
        return

    if target["balance"] <= 0:
        await update.message.reply_text(f"{_fmt_user(target)} has nothing to steal.")
        return

    pct = random.uniform(config.ROB_MIN_STEAL_PCT, config.ROB_MAX_STEAL_PCT)
    stolen = max(1, int(target["balance"] * pct))

    await db.update_balance(target_tg.id, -stolen)
    await db.update_balance(attacker_tg.id, stolen)

    await update.message.reply_text(
        f"🥷 {_fmt_user(attacker)} robbed {_fmt_user(target)} and got away with {stolen} coins!"
    )


async def economy_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💰 ECONOMY SYSTEM\n\n"
        "/bal - check your stats\n"
        "/daily - claim free coins every 24h\n"
        "/protect - shield yourself from /kill and /rob for a fee\n"
        "/kill - reply to someone to steal a big cut of their coins (blocked if protected)\n"
        "/rob - reply to someone for a smaller, riskier steal (can fail)\n"
    )
    await update.message.reply_text(text)
