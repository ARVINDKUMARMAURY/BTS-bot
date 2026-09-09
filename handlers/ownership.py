from telegram import Update
from telegram.ext import ContextTypes

import database as db
import config


async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only the top 5 globally richest users can register their group link here."""
    tg_user = update.effective_user
    if not await db.is_top5(tg_user.id):
        await update.message.reply_text(
            "👉 Only the top 5 globally richest users can use this command."
        )
        return
    if not context.args:
        await update.message.reply_text("Usage: /setgroup <group invite link> <group name>")
        return

    link = context.args[0]
    name = " ".join(context.args[1:]) or "Unnamed Group"
    rank = await db.get_rank(tg_user.id)

    await db.group_promos.update_one(
        {"_id": tg_user.id},
        {"$set": {"link": link, "name": name, "rank": rank}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ Your group '{name}' is now featured in /groups.")


async def groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor = db.group_promos.find().sort("rank", 1).limit(5)
    promos = [p async for p in cursor]
    if not promos:
        await update.message.reply_text("No groups have been featured yet.")
        return
    lines = ["👥 JOIN THESE GROUPS:\n"]
    for p in promos:
        lines.append(f"• {p['name']} — {p['link']}")
    await update.message.reply_text("\n".join(lines))


async def ownership_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 OWNERSHIP\n\n"
        "/setgroup <link> <name> - top 5 richest users only, feature your group\n"
        "/groups - see currently featured groups\n\n"
        "✅ ACCOUNT RECOVERY\n"
        "/setpass <password> - secure your current account data\n"
        "/mpass - get your password in DM if you forget it\n"
        "/cpass <old_pass> <new_pass> - change your password\n"
        "/transfer <old_id> <old_pass> - restore a deleted account's stats into this one\n"
        f"Bot owner IDs configured: {len(config.OWNER_IDS)}\n"
    )
    await update.message.reply_text(text)


# --- Account recovery ---

async def setpass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /setpass <password>")
        return
    password = context.args[0]
    if len(password) < 4:
        await update.message.reply_text("Password must be at least 4 characters.")
        return

    await db.get_user(tg_user.id, tg_user.username or "")  # ensure the user doc exists
    await db.set_password(tg_user.id, password)
    try:
        await context.bot.send_message(
            tg_user.id,
            "🔐 Your BTS recovery password has been set. Keep it safe — you'll need it "
            "with /transfer if this account ever gets deleted.\n\n"
            "⚠️ Don't reuse a real-world password — this only protects your in-bot stats.",
        )
        await update.message.reply_text("🔐 Password set! Check your DM for a confirmation.")
    except Exception:
        await update.message.reply_text(
            "🔐 Password set! Start a DM with me first so I can confirm important recovery messages there."
        )


async def mpass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    password = await db.get_password(tg_user.id)
    if not password:
        await update.message.reply_text("You haven't set a password yet. Use /setpass <password> first.")
        return
    try:
        await context.bot.send_message(tg_user.id, f"🔐 Your BTS recovery password: {password}")
        await update.message.reply_text("🔐 Sent to your DM.")
    except Exception:
        await update.message.reply_text("Please start a DM with me first, then try /mpass again.")


async def cpass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /cpass <old_password> <new_password>")
        return
    old_pass, new_pass = context.args[0], context.args[1]
    current = await db.get_password(tg_user.id)
    if not current:
        await update.message.reply_text("You haven't set a password yet. Use /setpass <password> first.")
        return
    if current != old_pass:
        await update.message.reply_text("❌ Old password is incorrect.")
        return
    if len(new_pass) < 4:
        await update.message.reply_text("New password must be at least 4 characters.")
        return
    await db.set_password(tg_user.id, new_pass)
    await update.message.reply_text("✅ Password changed successfully.")


async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /transfer <old_id> <deleted account password>")
        return
    old_id_str, password = context.args[0], context.args[1]
    if not old_id_str.isdigit():
        await update.message.reply_text("old_id must be a numeric Telegram user ID.")
        return
    old_id = int(old_id_str)

    if old_id == tg_user.id:
        await update.message.reply_text("You can't transfer an account into itself.")
        return

    stored_password = await db.get_password(old_id)
    if not stored_password:
        await update.message.reply_text("❌ That account never set a recovery password.")
        return
    if stored_password != password:
        await update.message.reply_text("❌ Incorrect password.")
        return

    old_doc = await db.users.find_one({"_id": old_id})
    if old_doc and old_doc.get("transferred"):
        await update.message.reply_text("❌ This account's data has already been transferred once.")
        return

    # Best-effort check that the old account is actually gone. The Bot API can't reliably
    # confirm deletion, so this only blocks the obvious case where the old account is still
    # clearly active and reachable — the password match is the real security barrier.
    try:
        old_chat = await context.bot.get_chat(old_id)
        if old_chat and old_chat.username and old_chat.type == "private":
            await update.message.reply_text(
                "⚠️ That account still looks active. /transfer is only for accounts that "
                "have actually been deleted. If it really is gone, contact the bot owner."
            )
            return
    except Exception:
        pass  # couldn't resolve it at all — consistent with a deleted account, proceed

    await db.get_user(tg_user.id, tg_user.username or "")  # ensure current account doc exists
    ok = await db.transfer_account(old_id, tg_user.id)
    if not ok:
        await update.message.reply_text("❌ No data found for that old account.")
        return

    await update.message.reply_text(
        "✅ Transfer complete! Your current account's coins, kills, gems, premium and other "
        "stats have been replaced with the recovered account's data."
    )
