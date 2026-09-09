# BTS Bot

Telegram economy/RPG bot — a BAKA-style feature clone built with `python-telegram-bot` + MongoDB (Motor).

## Setup

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env
# edit .env: put your BOT_TOKEN (from @BotFather), MONGO_URI, and OWNER_IDS
python3 main.py
```

## Deploy to Heroku

The bot uses polling (no HTTP server), so it must run on a **worker** dyno, not `web`.

```bash
cd bts_bot
git init
heroku create your-bts-bot-name
heroku config:set BOT_TOKEN=123456:your-token
heroku config:set MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
heroku config:set DB_NAME=bts_bot
heroku config:set OWNER_IDS=123456789,987654321
git add .
git commit -m "Deploy BTS bot"
git push heroku main
heroku ps:scale worker=1
heroku logs --tail
```

Notes:
- Heroku has no free tier anymore — you need at least an Eco or Basic dyno (~$5/mo).
- MongoDB must be external (Atlas free tier works fine) since Heroku dynos have no persistent disk.
- `heroku ps:scale worker=1` is required because the `Procfile` defines a `worker` process, not `web` — Heroku won't start it automatically like it does for `web`.
- If your git default branch is `master` instead of `main`, push with `git push heroku master`.


## Feature categories (all 12, matching BAKA's menu)

| Category | Commands |
|---|---|
| 💰 Economy | `/bal /daily /protect /kill /rob /economy` |
| 🤫 Whisper | `/whisper <text>` (reply to someone) |
| 👮 Management | `.ban .kick .mute .warn .promote .demote .pin .d` etc — prefix `.` or `!` |
| 👑 Ownership | `/setgroup /groups` (top-5 richest only can set) + account recovery: `/setpass /mpass /cpass /transfer` |
| 💗 Premium | `/buypremium /premiumstatus` |
| 💎 Gems | `/gems /exchange <coins>` |
| 🦅 Powers | `/powers /buypower <name>` |
| 🕹️ Games | `/game /coinflip /dice` |
| 🧸 Friends | `/addfriend /friends` |
| 🎟️ Coupons | `/redeem /createcoupon` (owner only) |
| 💞 Interactions | `/hug /slap /pat /kiss /poke` |
| 🔧 Utilities | `/ping /id` |

`/start` shows the full BAKA-style inline button menu — tapping a category shows that category's commands.

## Structure

```
bts_bot/
├── main.py           # bot startup, command registration, inline menu
├── config.py         # env-driven settings
├── database.py       # MongoDB (Motor) access layer
├── Procfile          # Heroku worker process definition
├── runtime.txt        # Python version pin for Heroku
├── handlers/
│   ├── economy.py
│   ├── whisper.py
│   ├── management.py
│   ├── ownership.py
│   ├── premium.py
│   ├── gems.py
│   ├── powers.py
│   ├── games.py
│   ├── friends.py
│   ├── coupons.py
│   ├── interactions.py
│   └── utilities.py
├── requirements.txt
└── .env.example
```

## Group Management module (`.` / `!` prefix)

Unlike every other feature (which uses normal `/commands`), Management uses a dot or bang
prefix — same style as BAKA. Send `.help` in any group the bot is in to see the full list:

```
.res <user> +-power_name   - restrict/unrestrict one permission for a member
.add <user> <power>        - grant a bot power to a user (creator only)
.remove <user> <power>     - remove a bot power from a user (creator only)

.promote <user> 0/1/2/3    - promote user to admin (higher = more rights)
.demote <user>             - demote an admin
.demote_all                - demote all BTS-promoted admins
.title <user> <title>      - set an admin's custom title

.warns <user>               - get all warnings
.warn <user>                - warn a user (3 = ban)
.unwarn <user>               - remove 1 warning

.mute <user> [30m]          - mute temp/permanent
.dmute <reply> [time]       - delete replied message and mute user
.smute <user>                - silently mute the user
.unmute <user>                - unmute the user

.ban <user>       .dban <reply>      .sban <user>      .unban <user>
.kick <user>      .skick <user>

.pin <reply>      .unpin      .d (reply)      .help
```

`<user>` = reply to their message, `@username`, or numeric user ID.

Bot powers (`ban`, `mute`, `kick`, `warn`, `pin`, `promote`, `title`, `res`) can be granted to
non-admins via `.add` — only the group creator (or a configured `OWNER_ID`) can grant/revoke
these. Real Telegram admins always have every power automatically.

**Important:** for `.promote`, `.demote`, `.title`, `.pin`, `.ban`, `.mute`, etc. to actually work,
the bot itself must be a group admin with the matching Telegram permissions
(Ban users, Delete messages, Pin messages, Add new admins).

## Account Recovery (under Ownership)

Lets a player restore their coins/gems/kills/premium onto a new account if their old
Telegram account gets deleted:

```
/setpass <password>              - set a recovery password on your current account
/mpass                            - DM yourself your password if you forget it
/cpass <old_pass> <new_pass>      - change your password
/transfer <old_id> <old_pass>     - wipe this account's data and restore <old_id>'s data here
```

Rules enforced in code:
- `/transfer` requires the stored password to match exactly.
- Each account can only be transferred out **once** (`transferred: true` flag blocks reuse).
- The bot does a best-effort check via `get_chat` to catch the obvious case where the "old"
  account is still clearly active — but the Bot API can't reliably confirm an account was
  deleted, so the password match is the real security barrier, not the deletion check.
- On a successful transfer, the **current** account's coins/gems/kills/premium/etc. are
  overwritten by the old account's data (not merged) — exactly as the feature describes.
- The stored password is plain text in MongoDB (`recovery_password` field) so `/mpass` can
  show it back to the user — this is an in-bot game code, not a real credential, but tell
  players not to reuse a real password here.

## Premium features poster

`/premium` (and the "Premium" button in `/start`) sends `assets/premium_features.png` — a
generated BTS-branded comparison card (Normal vs Premium), styled after BAKA's version.

The image is already committed to the repo, so nothing extra is needed to deploy it. If you
want to edit the table (prices, rows, colors), regenerate it locally:
```bash
pip install pillow --break-system-packages
python3 generate_premium_image.py
```
This overwrites `assets/premium_features.png` — commit the new file afterwards.

## Notes



- Every user auto-registers in MongoDB on first command with 300 starting coins.
- `/kill` and `/rob` respect `/protect` — a protected target can't be attacked.
- `/setgroup` is gated to the top 5 richest users by balance, same as BAKA.
- Coupons and powers are stubs you can expand — add more entries to the dicts in
  `handlers/coupons.py` / `handlers/powers.py`.
- Deploy on any VPS with outbound internet + your MongoDB Atlas connection
  (avoid UpCloud if you also plan voice-call features — UDP/27017 gets blocked there).
