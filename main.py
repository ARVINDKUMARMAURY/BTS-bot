import logging
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
import database as db
from handlers import (
    economy,
    whisper,
    management,
    ownership,
    premium,
    gems,
    powers,
    games,
    friends,
    coupons,
    interactions,
    utilities,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bts_bot")

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
)


def sc(text: str) -> str:
    """Convert plain ASCII letters to small-caps unicode for a stylized look."""
    return text.translate(SMALL_CAPS_MAP)


CATEGORY_TEXTS = {
    "whisper": (
        "🤫 WHISPER\n\n"
        "Reply with /whisper <text> to privately DM the replied user through the bot.\n"
        "(They must have started a DM with the bot at least once.)"
    ),
    "management": (
        "👮 MANAGEMENT (group admins / granted powers)\n\n"
        "Use '.' or '!' as prefix, e.g. .ban, !mute\n"
        ".ban .kick .mute .warn .promote .demote .pin .d and more\n"
        "Send .help in the group for the full command list"
    ),
    "ownership": (
        "👑 OWNERSHIP\n\n"
        "/setgroup <link> <name> - top 5 richest users only, feature your group\n"
        "/groups - see currently featured groups\n\n"
        "✅ ACCOUNT RECOVERY\n"
        "/setpass <password> - secure your current account data\n"
        "/mpass - get your password in DM if you forget it\n"
        "/cpass <old_pass> <new_pass> - change your password\n"
        "/transfer <old_id> <old_pass> - restore a deleted account's stats into this one"
    ),
    "premium": (
        f"💗 PREMIUM\n\n"
        f"/buypremium - {premium.PREMIUM_COST_GEMS} gems for {premium.PREMIUM_DURATION_DAYS} days\n"
        "/premiumstatus - check your premium expiry"
    ),
    "gems": (
        "💎 GEMS\n\n"
        "/gems - check your gem balance\n"
        f"/exchange <coins> - convert coins to gems ({gems.COINS_PER_GEM} coins = 1 gem)"
    ),
    "powers": (
        "🦅 POWERS (bought with gems)\n\n"
        + "\n".join(
            f"/buypower {name} - {p['cost_gems']} gems, {p['duration_hours']}h — {p['desc']}"
            for name, p in powers.POWERS.items()
        )
    ),
    "economy": (
        "💰 ECONOMY SYSTEM\n\n"
        "/bal - check your stats\n"
        "/daily - claim free coins every 24h\n"
        "/protect - shield yourself from /kill and /rob for a fee\n"
        "/kill - reply to someone to steal a big cut of their coins\n"
        "/rob - reply to someone for a smaller, riskier steal"
    ),
    "games": (
        "🕹️ MINI GAMES\n\n"
        "/coinflip <amount> heads|tails - 50/50 double or nothing\n"
        "/dice <amount> - roll a dice, 4-6 wins double"
    ),
    "friends": (
        "🧸 FRIENDS\n\n"
        "/addfriend - reply to someone to add them\n"
        "/friends - view your friends list"
    ),
    "coupons": (
        "🎟️ COUPONS\n\n"
        "/redeem <code> - claim a coupon's reward\n"
        "/createcoupon <code> <reward> <uses> - owner only"
    ),
    "interactions": (
        "💞 INTERACTIONS\n\n"
        + "\n".join(f"/{a} (reply)" for a in interactions.ACTIONS)
        + "\n/crush (reply) - check replied user's crush meter"
        + "\n/brain (reply) - check someone's brain"
        + "\n/stupid_meter (reply) - check how stupid someone is"
        + "\n/couples - choose random couples from the group"
    ),
    "utilities": (
        "🔧 UTILITIES\n\n"
        "/ping - check bot latency\n"
        "/id - get your Telegram ID / chat ID"
    ),
}

CATEGORY_LABELS = {
    "whisper": f"🤫 {sc('Whisper')}",
    "management": f"👮 {sc('Management')}",
    "ownership": f"👑 {sc('Ownership')}",
    "premium": f"💗 {sc('Premium')}",
    "gems": f"💎 {sc('Gems')}",
    "powers": f"🦅 {sc('Powers')}",
    "economy": f"💰 {sc('Economy')}",
    "games": f"🕹️ {sc('Games')}",
    "friends": f"🧸 {sc('Friends')}",
    "coupons": f"🎟️ {sc('Coupons')}",
    "interactions": f"💞 {sc('Interactions')}",
    "utilities": f"🔧 {sc('Utilities')}",
}


# --- Level 1: the /start screen (matches BAKA FEATURES / Groups / Promoter / Updates / Games / Add me) ---

def build_start_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"🍀 {sc('BTS FEATURES')}", callback_data="menu:features")],
        [
            InlineKeyboardButton(f"👥 {sc('GROUPS')}", callback_data="menu:groups"),
            InlineKeyboardButton(f"💸 {sc('PROMOTER')}", url="https://t.me/"),
        ],
        [
            InlineKeyboardButton(f"📢 {sc('UPDATES')}", url="https://t.me/"),
            InlineKeyboardButton(f"🎮 {sc('GAMES')}", callback_data="menu:games"),
        ],
        [InlineKeyboardButton(f"➕ {sc('ADD ME TO YOUR GROUP')}", url="https://t.me/your_bts_bot?startgroup=true")],
    ]
    return InlineKeyboardMarkup(rows)


# --- Level 2: the BTS FEATURES grid (Whisper / Management / Ownership / ... / Utilities) ---


def build_features_menu() -> InlineKeyboardMarkup:
    keys = list(CATEGORY_LABELS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        pair = keys[i : i + 2]
        rows.append([InlineKeyboardButton(CATEGORY_LABELS[k], callback_data=f"menu:{k}") for k in pair])
    rows.append([InlineKeyboardButton(f"⬅️ {sc('Back')}", callback_data="menu:back")])
    return InlineKeyboardMarkup(rows)


async def build_start_text(tg_user) -> str:
    user = await db.get_user(tg_user.id, tg_user.username or "")
    rank = await db.get_rank(tg_user.id)
    name = html.escape(tg_user.first_name or "there")
    intro = sc("I'm BTS - a gaming and chatting bot having lots of features to engage your group.")
    stats_block = (
        "<blockquote>"
        f"💰 {sc('Balance')}: {user['balance']}\n"
        f"🏆 {sc('Rank')}: {rank}\n"
        f"💎 {sc('Gems')}: {user['gems']:.2f}\n"
        f"🔪 {sc('Kills')}: {user['kills']}"
        "</blockquote>"
    )
    return (
        f"💙 {sc('Hieeeee')} {name}, {intro}\n\n"
        f"📊 {sc('Your stats:')}\n"
        f"{stats_block}\n\n"
        f"🕹️ {sc('How to play?')}\n"
        f"💰 /bal - {sc('check your stats')}\n"
        f"👤 /pfp - {sc('check your pfp')}\n"
        f"🎁 /daily - {sc('get free coins')}\n"
        f"🛡️ /protect - {sc('save yourself')}\n"
        f"⚔️ /kill & /rob - {sc('loot others')}\n\n"
        f"👇 {sc('Choose an option below:')}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build_start_text(update.effective_user)
    await update.message.reply_text(text, reply_markup=build_start_menu(), parse_mode=ParseMode.HTML)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":", 1)[1]

    # Back to the very first /start screen
    if data == "back":
        text = await build_start_text(query.from_user)
        await query.edit_message_text(text, reply_markup=build_start_menu(), parse_mode=ParseMode.HTML)
        return

    # "BTS FEATURES" tapped -> show the 12-category grid
    if data == "features":
        await query.edit_message_text(
            f"ℹ️ {sc('ABOUT BTS')}\n\n{sc('Click the buttons below to know more about BTS features.')}",
            reply_markup=build_features_menu(),
        )
        return

    # "GAMES" tapped from the level-1 menu -> same as the games category info
    if data == "groups":
        text = f"👥 {sc('Use /groups in chat to see currently featured groups, or /setgroup if you are top 5 richest.')}"
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⬅️ {sc('Back')}", callback_data="menu:back")]])
        )
        return

    # A specific category from the features grid
    text = CATEGORY_TEXTS.get(data, f"{CATEGORY_LABELS.get(data, data)}: no info available.")
    back_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"⬅️ {sc('Back to features')}", callback_data="menu:features")]]
    )
    await query.edit_message_text(text, reply_markup=back_button)


async def track_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently remembers active group members so /couples has a pool to pick from."""
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type in ("group", "supergroup") and not user.is_bot:
        await db.track_group_member(chat.id, user.id, user.full_name)


def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file.")

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Core
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))

    # Economy
    app.add_handler(CommandHandler("bal", economy.bal))
    app.add_handler(CommandHandler("pfp", economy.pfp))
    app.add_handler(CommandHandler("daily", economy.daily))
    app.add_handler(CommandHandler("protect", economy.protect))
    app.add_handler(CommandHandler("kill", economy.kill))
    app.add_handler(CommandHandler("rob", economy.rob))
    app.add_handler(CommandHandler("economy", economy.economy_info))

    # Whisper
    app.add_handler(CommandHandler("whisper", whisper.whisper))

    # Management
    app.add_handler(
        MessageHandler(filters.Regex(r"^[.!]\w") & filters.ChatType.GROUPS, management.dot_command_dispatcher)
    )
    app.add_handler(CommandHandler("management", management.management_info))

    # Ownership
    app.add_handler(CommandHandler("setgroup", ownership.setgroup))
    app.add_handler(CommandHandler("groups", ownership.groups))
    app.add_handler(CommandHandler("setpass", ownership.setpass))
    app.add_handler(CommandHandler("mpass", ownership.mpass))
    app.add_handler(CommandHandler("cpass", ownership.cpass))
    app.add_handler(CommandHandler("transfer", ownership.transfer))
    app.add_handler(CommandHandler("ownership", ownership.ownership_info))

    # Premium
    app.add_handler(CommandHandler("buypremium", premium.buy_premium))
    app.add_handler(CommandHandler("premiumstatus", premium.premium_status))
    app.add_handler(CommandHandler("premium", premium.premium_info))

    # Gems
    app.add_handler(CommandHandler("gems", gems.gems_balance))
    app.add_handler(CommandHandler("exchange", gems.exchange))

    # Powers
    app.add_handler(CommandHandler("powers", powers.powers_list))
    app.add_handler(CommandHandler("buypower", powers.buy_power))

    # Games
    app.add_handler(CommandHandler("game", games.game_menu))
    app.add_handler(CommandHandler("coinflip", games.coinflip))
    app.add_handler(CommandHandler("dice", games.dice))

    # Friends
    app.add_handler(CommandHandler("addfriend", friends.add_friend))
    app.add_handler(CommandHandler("friends", friends.friends_list))

    # Coupons
    app.add_handler(CommandHandler("redeem", coupons.redeem))
    app.add_handler(CommandHandler("createcoupon", coupons.create_coupon))

    # Interactions
    for action in interactions.ACTIONS:
        app.add_handler(CommandHandler(action, interactions.make_handler(action)))
    app.add_handler(CommandHandler("crush", interactions.crush))
    app.add_handler(CommandHandler("brain", interactions.brain))
    app.add_handler(CommandHandler("stupid_meter", interactions.stupid_meter))
    app.add_handler(CommandHandler("couples", interactions.couples))
    app.add_handler(CommandHandler("interactions", interactions.interactions_info))

    # Track group members for /couples (runs on every group text message, lowest priority group)
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT, track_member), group=1
    )

    # Utilities
    app.add_handler(CommandHandler("ping", utilities.ping))
    app.add_handler(CommandHandler("id", utilities.id_cmd))
    app.add_handler(CommandHandler("utilities", utilities.utilities_info))

    logger.info("BTS bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
