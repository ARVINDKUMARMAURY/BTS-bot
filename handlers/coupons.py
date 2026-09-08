from telegram import Update
from telegram.ext import ContextTypes

import database as db
import config


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /redeem <code>")
        return

    code = context.args[0].upper()
    coupon = await db.coupons.find_one({"_id": code})
    if not coupon:
        await update.message.reply_text("❌ Invalid coupon code.")
        return
    if tg_user.id in coupon.get("redeemed_by", []):
        await update.message.reply_text("You've already redeemed this coupon.")
        return
    if coupon.get("uses_left", 0) <= 0:
        await update.message.reply_text("This coupon has no uses left.")
        return

    reward = coupon.get("reward", 0)
    await db.update_balance(tg_user.id, reward)
    await db.coupons.update_one(
        {"_id": code},
        {"$inc": {"uses_left": -1}, "$addToSet": {"redeemed_by": tg_user.id}},
    )
    await update.message.reply_text(f"🎟️ Coupon redeemed! You got {reward} coins.")


async def create_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: /createcoupon <code> <reward> <uses>"""
    tg_user = update.effective_user
    if tg_user.id not in config.OWNER_IDS:
        await update.message.reply_text("Only the bot owner can create coupons.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /createcoupon <code> <reward> <uses>")
        return

    code, reward, uses = context.args[0].upper(), context.args[1], context.args[2]
    if not reward.isdigit() or not uses.isdigit():
        await update.message.reply_text("Reward and uses must be numbers.")
        return

    await db.coupons.update_one(
        {"_id": code},
        {"$set": {"reward": int(reward), "uses_left": int(uses)}, "$setOnInsert": {"redeemed_by": []}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ Coupon {code} created: {reward} coins, {uses} uses.")
