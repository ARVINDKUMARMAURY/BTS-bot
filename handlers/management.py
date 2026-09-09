import re
import datetime

from telegram import Update, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import config
import database as db

HELP_TEXT = (
    "✅ Manage your group with some amazing group management commands of BTS!\n\n"
    ".res <user> +-power_name - restrict a member with given power\n\n"
    ".add <user> <power> - add given power for an admin\n"
    ".remove <user> <power> - remove given power for an admin\n\n"
    ".promote <user> 0/1/2/3 - Promote user to admin\n"
    ".demote <user> - Demote admin\n\n"
    ".demote_all - demote all BTS promoted admins\n\n"
    ".title <user> <title> - Set custom title\n\n"
    ".warns <user> - Get all warnings\n"
    f".warn <user> - Warn a user ({config.MAX_WARNS} = ban)\n"
    ".unwarn <user> - Remove 1 warning\n\n"
    ".mute <user> 30m - Mute temp/permanent\n"
    ".dmute <reply> <time> - delete replied message and mute user\n"
    ".smute <user> - silently mute the user\n"
    ".unmute <user> - Unmute the user\n\n"
    ".ban <user> - Ban user\n"
    ".dban reply - delete replied msg and ban user\n"
    ".sban <user> - silently ban the user\n"
    ".unban <user> - Unban user\n"
    ".kick <user> - Kick from group\n"
    ".skick <user> - silently kick the user\n\n"
    ".pin <reply> - Pin replied message\n"
    ".unpin - Unpin the current message\n"
    ".d - delete a message\n"
    ".help - Show this help\n\n"
    "Note:\n"
    "1) You can use '.' or '!' as prefix.\n"
    "2) <user> = reply/username/userid"
)

RES_POWER_MAP = {
    "msg": "can_send_messages",
    "text": "can_send_messages",
    "media": "can_send_photos",
    "sticker": "can_send_other_messages",
    "other": "can_send_other_messages",
    "poll": "can_send_polls",
    "web": "can_add_web_page_previews",
    "webpreview": "can_add_web_page_previews",
    "invite": "can_invite_users",
    "pin": "can_pin_messages",
    "info": "can_change_info",
}

PROMOTE_LEVELS = {
    "0": dict(can_manage_chat=True),
    "1": dict(can_manage_chat=True, can_delete_messages=True, can_restrict_members=True),
    "2": dict(
        can_manage_chat=True,
        can_delete_messages=True,
        can_restrict_members=True,
        can_invite_users=True,
        can_pin_messages=True,
    ),
    "3": dict(
        can_manage_chat=True,
        can_delete_messages=True,
        can_restrict_members=True,
        can_invite_users=True,
        can_pin_messages=True,
        can_promote_members=True,
        can_change_info=True,
    ),
}

DURATION_RE = re.compile(r"^(\d+)([smhd])$")


def parse_duration(text: str):
    """'30m' -> timedelta(minutes=30). Returns None if unparseable (treated as permanent)."""
    if not text:
        return None
    m = DURATION_RE.match(text.lower())
    if not m:
        return None
    amount, unit = int(m.group(1)), m.group(2)
    return {
        "s": datetime.timedelta(seconds=amount),
        "m": datetime.timedelta(minutes=amount),
        "h": datetime.timedelta(hours=amount),
        "d": datetime.timedelta(days=amount),
    }[unit]


async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    """Returns (user_obj_or_None, remaining_args). user_obj has .id and .full_name."""
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        return update.message.reply_to_message.from_user, args

    if args:
        ident = args[0]
        remaining = args[1:]
        try:
            if ident.startswith("@"):
                chat = await context.bot.get_chat(ident)
                return chat, remaining
            if ident.lstrip("-").isdigit():
                member = await update.effective_chat.get_member(int(ident))
                return member.user, remaining
        except BadRequest:
            return None, remaining
    return None, args


async def is_real_admin(update: Update, user_id: int) -> bool:
    if user_id in config.OWNER_IDS:
        return True
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except BadRequest:
        return False


async def is_creator(update: Update, user_id: int) -> bool:
    if user_id in config.OWNER_IDS:
        return True
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status == "creator"
    except BadRequest:
        return False


async def has_power(update: Update, user_id: int, power: str) -> bool:
    if await is_real_admin(update, user_id):
        return True
    powers = await db.get_powers(update.effective_chat.id, user_id)
    return power in powers


async def _require_power(update: Update, power: str) -> bool:
    actor = update.effective_user
    if await has_power(update, actor.id, power):
        return True
    await update.message.reply_text("🚫 You don't have permission for that.")
    return False


async def _require_admin(update: Update) -> bool:
    actor = update.effective_user
    if await is_real_admin(update, actor.id):
        return True
    await update.message.reply_text("🚫 Only group admins can do that.")
    return False


async def _require_creator(update: Update) -> bool:
    actor = update.effective_user
    if await is_creator(update, actor.id):
        return True
    await update.message.reply_text("🚫 Only the group creator (or bot owner) can do that.")
    return False


# --- .res ---
async def cmd_res(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "res"):
        return
    if not args:
        await update.message.reply_text("Usage: .res <user> +power_name or .res <user> -power_name")
        return

    target, remaining = await resolve_target(update, context, args)
    if not target or not remaining:
        await update.message.reply_text("Usage: .res <user> +power_name or .res <user> -power_name")
        return

    flag = remaining[0]
    if not flag or flag[0] not in "+-":
        await update.message.reply_text("Prefix the power with + to allow or - to restrict.")
        return

    sign, power_name = flag[0], flag[1:].lower()
    field = RES_POWER_MAP.get(power_name)
    if not field:
        await update.message.reply_text(f"Unknown power '{power_name}'. Options: {', '.join(RES_POWER_MAP)}")
        return

    perms = ChatPermissions(**{field: sign == "+"})
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
        state = "allowed" if sign == "+" else "restricted"
        await update.message.reply_text(f"✅ {power_name} {state} for {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


# --- .add / .remove (bot powers) ---
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_creator(update):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target or not remaining:
        await update.message.reply_text(f"Usage: .add <user> <power>. Powers: {', '.join(config.ALL_POWERS)}")
        return
    power = remaining[0].lower()
    if power not in config.ALL_POWERS:
        await update.message.reply_text(f"Unknown power. Options: {', '.join(config.ALL_POWERS)}")
        return
    await db.add_power(update.effective_chat.id, target.id, power)
    await update.message.reply_text(f"✅ Granted '{power}' to {target.full_name}.")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_creator(update):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target or not remaining:
        await update.message.reply_text(f"Usage: .remove <user> <power>. Powers: {', '.join(config.ALL_POWERS)}")
        return
    power = remaining[0].lower()
    await db.remove_power(update.effective_chat.id, target.id, power)
    await update.message.reply_text(f"✅ Removed '{power}' from {target.full_name}.")


# --- .promote / .demote / .demote_all / .title ---
async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_admin(update):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target or not remaining or remaining[0] not in PROMOTE_LEVELS:
        await update.message.reply_text("Usage: .promote <user> 0/1/2/3")
        return
    perms = PROMOTE_LEVELS[remaining[0]]
    try:
        await context.bot.promote_chat_member(update.effective_chat.id, target.id, **perms)
        await db.record_promoted(update.effective_chat.id, target.id)
        await update.message.reply_text(f"⬆️ Promoted {target.full_name} (level {remaining[0]}).")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_admin(update):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .demote <user>")
        return
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False, can_promote_members=False,
            can_change_info=False,
        )
        await db.unrecord_promoted(update.effective_chat.id, target.id)
        await update.message.reply_text(f"⬇️ Demoted {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_demote_all(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_creator(update):
        return
    chat_id = update.effective_chat.id
    user_ids = await db.get_promoted(chat_id)
    if not user_ids:
        await update.message.reply_text("No BTS-promoted admins to demote.")
        return
    count = 0
    for uid in user_ids:
        try:
            await context.bot.promote_chat_member(
                chat_id, uid,
                can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
                can_invite_users=False, can_pin_messages=False, can_promote_members=False,
                can_change_info=False,
            )
            await db.unrecord_promoted(chat_id, uid)
            count += 1
        except BadRequest:
            continue
    await update.message.reply_text(f"⬇️ Demoted {count} BTS-promoted admin(s).")


async def cmd_title(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_admin(update):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target or not remaining:
        await update.message.reply_text("Usage: .title <user> <title>")
        return
    title = " ".join(remaining)[:16]  # Telegram custom title limit
    try:
        await context.bot.set_chat_administrator_custom_title(update.effective_chat.id, target.id, title)
        await update.message.reply_text(f"🏷️ Title for {target.full_name} set to '{title}'.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message} (user must already be an admin)")


# --- Warnings ---
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "warn"):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .warn <user>")
        return
    chat_id = update.effective_chat.id
    count = await db.warn_user(chat_id, target.id)
    if count >= config.MAX_WARNS:
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            await db.reset_warns(chat_id, target.id)
            await update.message.reply_text(f"🚫 {target.full_name} reached {config.MAX_WARNS} warnings and was banned.")
        except BadRequest as e:
            await update.message.reply_text(f"Failed to ban: {e.message}")
    else:
        await update.message.reply_text(f"⚠️ {target.full_name} warned ({count}/{config.MAX_WARNS}).")


async def cmd_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "warn"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .unwarn <user>")
        return
    count = await db.unwarn_user(update.effective_chat.id, target.id)
    await update.message.reply_text(f"✅ 1 warning removed from {target.full_name}. Now at {count}.")


async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    target, _ = await resolve_target(update, context, args)
    if not target:
        target = update.effective_user
    count = await db.get_warns(update.effective_chat.id, target.id)
    await update.message.reply_text(f"⚠️ {target.full_name} has {count}/{config.MAX_WARNS} warnings.")


# --- Mute / unmute ---
async def _mute(update, context, target, until):
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms, until_date=until)


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "mute"):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .mute <user> [30m]")
        return
    duration = parse_duration(remaining[0]) if remaining else None
    until = datetime.datetime.now(datetime.timezone.utc) + duration if duration else None
    try:
        await _mute(update, context, target, until)
        label = f"for {remaining[0]}" if duration else "permanently"
        await update.message.reply_text(f"🔇 Muted {target.full_name} {label}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_dmute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "mute"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message with .dmute [time]")
        return
    target = update.message.reply_to_message.from_user
    duration = parse_duration(args[0]) if args else None
    until = datetime.datetime.now(datetime.timezone.utc) + duration if duration else None
    try:
        await update.message.reply_to_message.delete()
        await _mute(update, context, target, until)
        await update.message.reply_text(f"🔇 Deleted message and muted {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_smute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "mute"):
        return
    target, remaining = await resolve_target(update, context, args)
    if not target:
        return
    duration = parse_duration(remaining[0]) if remaining else None
    until = datetime.datetime.now(datetime.timezone.utc) + duration if duration else None
    try:
        await _mute(update, context, target, until)
        await update.message.delete()
    except BadRequest:
        pass


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "mute"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .unmute <user>")
        return
    perms = ChatPermissions(
        can_send_messages=True, can_send_photos=True, can_send_videos=True,
        can_send_other_messages=True, can_send_polls=True, can_add_web_page_previews=True,
    )
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
        await update.message.reply_text(f"🔊 Unmuted {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


# --- Ban / kick ---
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "ban"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .ban <user>")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🚫 Banned {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_dban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "ban"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message with .dban")
        return
    target = update.message.reply_to_message.from_user
    try:
        await update.message.reply_to_message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🚫 Deleted message and banned {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_sban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "ban"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.delete()
    except BadRequest:
        pass


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "ban"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .unban <user>")
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"✅ Unbanned {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "kick"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        await update.message.reply_text("Usage: .kick <user>")
        return
    try:
        chat_id = update.effective_chat.id
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        await update.message.reply_text(f"👢 Kicked {target.full_name}.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_skick(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "kick"):
        return
    target, _ = await resolve_target(update, context, args)
    if not target:
        return
    try:
        chat_id = update.effective_chat.id
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        await update.message.delete()
    except BadRequest:
        pass


# --- Pin / unpin / delete ---
async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "pin"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to pin with .pin")
        return
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text("📌 Pinned.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_power(update, "pin"):
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Unpinned.")
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_d(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    if not await _require_admin(update):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to delete with .d")
        return
    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except BadRequest as e:
        await update.message.reply_text(f"Failed: {e.message}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    await update.message.reply_text(HELP_TEXT)


COMMANDS = {
    "res": cmd_res,
    "add": cmd_add,
    "remove": cmd_remove,
    "promote": cmd_promote,
    "demote": cmd_demote,
    "demote_all": cmd_demote_all,
    "title": cmd_title,
    "warns": cmd_warns,
    "warn": cmd_warn,
    "unwarn": cmd_unwarn,
    "mute": cmd_mute,
    "dmute": cmd_dmute,
    "smute": cmd_smute,
    "unmute": cmd_unmute,
    "ban": cmd_ban,
    "dban": cmd_dban,
    "sban": cmd_sban,
    "unban": cmd_unban,
    "kick": cmd_kick,
    "skick": cmd_skick,
    "pin": cmd_pin,
    "unpin": cmd_unpin,
    "d": cmd_d,
    "help": cmd_help,
}


async def dot_command_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes .command / !command messages in groups to the matching handler above."""
    message = update.effective_message
    if not message or not message.text:
        return
    text = message.text.strip()
    if len(text) < 2 or text[0] not in ".!":
        return

    parts = text[1:].split()
    if not parts:
        return
    name = parts[0].lower()
    args = parts[1:]

    handler = COMMANDS.get(name)
    if not handler:
        return
    await handler(update, context, args)


async def management_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)
