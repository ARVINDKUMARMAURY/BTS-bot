from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes


async def _is_group_admin(update: Update) -> bool:
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_group_admin(update):
        await update.message.reply_text("Only group admins can use /mute.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to mute.")
        return
    target = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"🔇 Muted {target.full_name}.")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_group_admin(update):
        await update.message.reply_text("Only group admins can use /unmute.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to unmute.")
        return
    target = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id, target.id, ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"🔊 Unmuted {target.full_name}.")


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_group_admin(update):
        await update.message.reply_text("Only group admins can use /warn.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to warn.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason given"
    await update.message.reply_text(f"⚠️ {target.full_name} warned. Reason: {reason}")


async def management_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👮 MANAGEMENT (group admins only)\n\n"
        "/mute - reply to mute a user\n"
        "/unmute - reply to unmute a user\n"
        "/warn <reason> - reply to warn a user\n"
    )
    await update.message.reply_text(text)
