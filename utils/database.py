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
    global connector, hcdb, pointsColl, wishlistColl, rewardedColl, auctionWinnersColl
    connector = pymongo.AsyncMongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
    info = await connector.server_info()  # Trigger connection to verify credentials and connectivity
    print("Connected to MongoDB")
    print(f"Server Info: {info}")

    hcdb = connector.get_database("heavenly-court")

    pointsColl = hcdb.points
    wishlistColl = hcdb.whitelist
    rewardedColl = hcdb.rewarded
    auctionWinnersColl = hcdb.auction_winners


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

# true if not claimed
async def try_claim_reward(message_id: int) -> bool:
    result = await rewardedColl.update_one({"message_id": message_id}, {"$setOnInsert": {"message_id": message_id}}, upsert=True)
    print(result.upserted_id)
    return result.upserted_id is not None

#true if pog not claimed
async def try_claim_pog_reward(message_id: int) -> bool:
    result = await rewardedColl.update_one({"message_id": message_id}, {"$setOnInsert": {"pog_rewarded": True}}, upsert=True)
    return result.modified_count == 0

#auction winner tracking

async def is_auction_winner(user_id: int) -> bool:
    user = await auctionWinnersColl.find_one({"user_id": user_id})
    return user is not None

async def add_auction_winner(user_id: int) -> None:
    await auctionWinnersColl.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

async def remove_auction_winner(user_id: int) -> None:
    result = await auctionWinnersColl.delete_one({"user_id": user_id})
    if result.deleted_count == 0:
        raise ValueError("User is not in the winner list.")

async def get_auction_winners() -> list[int]:
    cursor = auctionWinnersColl.find({}, {"user_id": 1})
    return [doc["user_id"] async for doc in cursor]

async def clear_auction_winners() -> None:
    await auctionWinnersColl.delete_many({})

#booster stuff 

async def get_booster_points(user_id: int) -> int:
    user = await pointsColl.find_one({"user_id": user_id})
    if user is None:
        return 0
    return user.get("booster_points", 0)

async def add_booster_points(user_id: int, amount: int) -> None:
    await pointsColl.update_one({"user_id": user_id}, {"$inc": {"booster_points": amount}}, upsert=True)

async def remove_booster_points(user_id: int, amount: int) -> int:
    user = await pointsColl.find_one({"user_id": user_id, "booster_points": {"$gte": amount}})
    if user is None:
        raise ValueError("User does not have enough booster points")
    await pointsColl.update_one({"user_id": user_id}, {"$inc": {"booster_points": -amount}}, upsert=True)
    return user["booster_points"] - amount

async def set_booster_points(user_id: int, amount: int) -> None:
    await pointsColl.update_one({"user_id": user_id}, {"$set": {"booster_points": amount}}, upsert=True)