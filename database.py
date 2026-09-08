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
