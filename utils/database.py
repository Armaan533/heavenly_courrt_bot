import pymongo
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
import os

connector: pymongo.AsyncMongoClient
hcdb: AsyncDatabase
pointsColl: AsyncCollection
wishlistColl: AsyncCollection
rewardedColl: AsyncCollection

async def init_db():
    global connector, hcdb, pointsColl, wishlistColl, rewardedColl
    connector = pymongo.AsyncMongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
    info = await connector.server_info()  # Trigger connection to verify credentials and connectivity
    print("Connected to MongoDB")
    print(f"Server Info: {info}")

    hcdb = connector.get_database("heavenly-court")

    pointsColl = hcdb.points
    wishlistColl = hcdb.whitelist
    rewardedColl = hcdb.rewarded


#           Points System           #


async def get_points(user_id: int) -> int:
    user: dict | None = await pointsColl.find_one({"user_id": user_id})
    if user is None:
        return 0
    return user.get("points", 0)

async def add_points(user_id: int, amount: int) -> None:
    await pointsColl.update_one({"user_id": user_id}, {"$inc": {"points": amount}}, upsert=True)

async def remove_points(user_id: int, amount: int) -> int:
    user: dict | None = await pointsColl.find_one({"user_id": user_id, "points": {"$gte": amount}})
    if user is None:
        raise ValueError("User does not have enough points")
    await pointsColl.update_one({"user_id": user_id}, {"$inc": {"points": -amount}}, upsert=True)
    return user["points"] - amount

async def set_points(user_id: int, amount: int) -> None:
    await pointsColl.update_one({"user_id": user_id}, {"$set": {"points": amount}}, upsert=True)

async def get_leaderboard(limit: int = 10) -> list[tuple[int, int]]:
    cursor = pointsColl.find({}, {"user_id": 1, "points": 1}).sort("points", pymongo.DESCENDING).limit(limit)
    return [(doc["user_id"], doc["points"]) async for doc in cursor]


#         Whitelist System         #


async def is_whitelisted(user_id: int) -> bool:
    user: dict | None = await wishlistColl.find_one({"user_id": user_id})
    if user is None:
        return False
    return True

async def add_to_whitelist(user_id: int) -> None:
    user : dict | None = await wishlistColl.find_one({"user_id": user_id})
    if user is not None:
        raise ValueError("User is already whitelisted")
    await wishlistColl.insert_one({"user_id": user_id})

async def remove_from_whitelist(user_id: int) -> None:
    user : dict | None = await wishlistColl.find_one({"user_id": user_id})
    if user is None:
        raise ValueError("User is not whitelisted")
    await wishlistColl.delete_one({"user_id": user_id})

async def get_whitelist() -> list[int]:
    cursor = wishlistColl.find({}, {"user_id": 1})
    return [doc["user_id"] async for doc in cursor]


#         Drop Reward Tracking         #


# async def is_rewarded(message_id: int) -> bool:
#     reward: dict | None = await rewardedColl.find_one({"message_id": message_id})
#     print(reward)
#     if reward is None:
#         return False
#     return True

# async def mark_as_rewarded(message_id: int) -> None:
#     reward: dict | None = await rewardedColl.find_one({"message_id": message_id})
#     if reward is None:
#         await rewardedColl.insert_one({"message_id": message_id})

async def try_claim_reward(message_id: int) -> bool:
    result = await rewardedColl.update_one({"message_id": message_id}, {"$setOnInsert": {"message_id": message_id}}, upsert=True)
    print(result.upserted_id)
    return result.upserted_id is not None
