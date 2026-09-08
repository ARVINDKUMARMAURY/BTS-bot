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
| 👮 Management | `/mute /unmute /warn` (group admins only) |
| 👑 Ownership | `/setgroup /groups` (top-5 richest only can set) |
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

## Notes

- Every user auto-registers in MongoDB on first command with 300 starting coins.
- `/kill` and `/rob` respect `/protect` — a protected target can't be attacked.
- `/setgroup` is gated to the top 5 richest users by balance, same as BAKA.
- Coupons and powers are stubs you can expand — add more entries to the dicts in
  `handlers/coupons.py` / `handlers/powers.py`.
- Deploy on any VPS with outbound internet + your MongoDB Atlas connection
  (avoid UpCloud if you also plan voice-call features — UDP/27017 gets blocked there).
