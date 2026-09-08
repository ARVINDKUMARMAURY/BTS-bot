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
        "/groups - see currently featured groups\n"
        f"Bot owner IDs configured: {len(config.OWNER_IDS)}\n"
    )
    await update.message.reply_text(text)
