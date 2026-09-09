"""
Async MongoDB layer for BTS bot (Motor).
Single 'users' collection holds the full economy profile per user.
"""

import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from config import MONGO_URI, DB_NAME, STARTING_BALANCE

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

users = db["users"]
coupons = db["coupons"]        # {code, reward, uses_left, redeemed_by: [user_id,...]}
group_promos = db["group_promos"]  # {position, name, link} - set via /setgroup by top 5
group_members = db["group_members"]  # {_id: f"{chat_id}:{user_id}", chat_id, user_id, name}


def default_user(user_id: int, username: str = "") -> dict:
    return {
        "_id": user_id,
        "username": username,
        "balance": STARTING_BALANCE,
        "gems": 0,
        "kills": 0,
        "pfp_file_id": None,
        "protected_until": None,
        "premium_until": None,
        "last_daily": None,
        "friends": [],
        "redeemed_coupons": [],
        "created_at": datetime.datetime.utcnow(),
    }


async def get_user(user_id: int, username: str = "") -> dict:
    user = await users.find_one({"_id": user_id})
    if not user:
        user = default_user(user_id, username)
        await users.insert_one(user)
    elif username and user.get("username") != username:
        await users.update_one({"_id": user_id}, {"$set": {"username": username}})
        user["username"] = username
    return user


async def update_balance(user_id: int, delta: int):
    await users.update_one({"_id": user_id}, {"$inc": {"balance": delta}})


async def set_field(user_id: int, field: str, value):
    await users.update_one({"_id": user_id}, {"$set": {field: value}})


async def increment_field(user_id: int, field: str, delta=1):
    await users.update_one({"_id": user_id}, {"$inc": {field: delta}})


async def get_rank(user_id: int) -> int:
    """1-indexed global rank by balance."""
    user = await users.find_one({"_id": user_id})
    if not user:
        return -1
    higher = await users.count_documents({"balance": {"$gt": user["balance"]}})
    return higher + 1


async def get_top_richest(limit: int = 5):
    cursor = users.find().sort("balance", -1).limit(limit)
    return [u async for u in cursor]


async def is_top5(user_id: int) -> bool:
    top5 = await get_top_richest(5)
    return any(u["_id"] == user_id for u in top5)


async def track_group_member(chat_id: int, user_id: int, name: str):
    """Remembers that this user has been seen active in this group (for /couples)."""
    await group_members.update_one(
        {"_id": f"{chat_id}:{user_id}"},
        {"$set": {"chat_id": chat_id, "user_id": user_id, "name": name}},
        upsert=True,
    )


async def get_group_members(chat_id: int, limit: int = 200) -> list:
    cursor = group_members.find({"chat_id": chat_id}).limit(limit)
    docs = [m async for m in cursor]
    return [{"_id": m["user_id"], "name": m["name"]} for m in docs]


# --- Management module: bot-granted powers, bot-promoted admins, warnings ---

admin_powers = db["admin_powers"]        # {_id: "chat:user", chat_id, user_id, powers: [str,...]}
promoted_admins = db["promoted_admins"]  # {_id: "chat:user", chat_id, user_id} - promoted via .promote
warnings = db["warnings"]                # {_id: "chat:user", chat_id, user_id, count}


async def add_power(chat_id: int, user_id: int, power: str):
    await admin_powers.update_one(
        {"_id": f"{chat_id}:{user_id}"},
        {"$set": {"chat_id": chat_id, "user_id": user_id}, "$addToSet": {"powers": power}},
        upsert=True,
    )


async def remove_power(chat_id: int, user_id: int, power: str):
    await admin_powers.update_one(
        {"_id": f"{chat_id}:{user_id}"}, {"$pull": {"powers": power}}
    )


async def get_powers(chat_id: int, user_id: int) -> list:
    doc = await admin_powers.find_one({"_id": f"{chat_id}:{user_id}"})
    return doc.get("powers", []) if doc else []


async def record_promoted(chat_id: int, user_id: int):
    await promoted_admins.update_one(
        {"_id": f"{chat_id}:{user_id}"},
        {"$set": {"chat_id": chat_id, "user_id": user_id}},
        upsert=True,
    )


async def unrecord_promoted(chat_id: int, user_id: int):
    await promoted_admins.delete_one({"_id": f"{chat_id}:{user_id}"})


async def get_promoted(chat_id: int) -> list:
    cursor = promoted_admins.find({"chat_id": chat_id})
    return [d["user_id"] async for d in cursor]


async def warn_user(chat_id: int, user_id: int) -> int:
    doc = await warnings.find_one_and_update(
        {"_id": f"{chat_id}:{user_id}"},
        {"$inc": {"count": 1}, "$set": {"chat_id": chat_id, "user_id": user_id}},
        upsert=True,
        return_document=True,
    )
    return doc["count"]


async def unwarn_user(chat_id: int, user_id: int) -> int:
    doc = await warnings.find_one({"_id": f"{chat_id}:{user_id}"})
    if not doc or doc.get("count", 0) <= 0:
        return 0
    await warnings.update_one({"_id": f"{chat_id}:{user_id}"}, {"$inc": {"count": -1}})
    return doc["count"] - 1


async def reset_warns(chat_id: int, user_id: int):
    await warnings.update_one({"_id": f"{chat_id}:{user_id}"}, {"$set": {"count": 0}})


async def get_warns(chat_id: int, user_id: int) -> int:
    doc = await warnings.find_one({"_id": f"{chat_id}:{user_id}"})
    return doc.get("count", 0) if doc else 0


# --- Account recovery (password-based transfer between accounts) ---

TRANSFERABLE_FIELDS = [
    "balance", "gems", "kills", "pfp_file_id", "protected_until",
    "premium_until", "friends", "redeemed_coupons",
]


async def set_password(user_id: int, password: str):
    await users.update_one({"_id": user_id}, {"$set": {"recovery_password": password}})


async def get_password(user_id: int):
    user = await users.find_one({"_id": user_id})
    return user.get("recovery_password") if user else None


async def transfer_account(old_id: int, new_id: int):
    """Wipes new_id's current game data and replaces it with old_id's, then locks old_id out."""
    old_user = await users.find_one({"_id": old_id})
    if not old_user:
        return False

    update_fields = {field: old_user.get(field) for field in TRANSFERABLE_FIELDS if field in old_user}
    await users.update_one({"_id": new_id}, {"$set": update_fields})
    await users.update_one({"_id": old_id}, {"$set": {"recovery_password": None, "transferred": True}})
    return True
