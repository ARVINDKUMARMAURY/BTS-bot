from telegram import Update
from telegram.ext import ContextTypes

import database as db


async def add_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to add as a friend.")
        return
    sender = update.effective_user
    target = update.message.reply_to_message.from_user
    if target.id == sender.id:
        await update.message.reply_text("You can't friend yourself.")
        return

    user = await db.get_user(sender.id, sender.username or "")
    if target.id in user.get("friends", []):
        await update.message.reply_text(f"You're already friends with {target.full_name}.")
        return

    await db.users.update_one({"_id": sender.id}, {"$addToSet": {"friends": target.id}})
    await update.message.reply_text(f"🧸 {target.full_name} added to your friends list!")


async def friends_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = await db.get_user(tg_user.id, tg_user.username or "")
    friend_ids = user.get("friends", [])
    if not friend_ids:
        await update.message.reply_text("You have no friends added yet. Reply /addfriend to someone.")
        return
    lines = ["🧸 YOUR FRIENDS:\n"]
    async for f in db.users.find({"_id": {"$in": friend_ids}}):
        lines.append(f"• @{f.get('username') or f['_id']}")
    await update.message.reply_text("\n".join(lines))
