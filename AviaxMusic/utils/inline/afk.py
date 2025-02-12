import time
import pymongo
from pyrogram import Client, filters
from pyrogram.types import Message

# Connect to MongoDB (Replace with your actual URI)
mongo_client = pymongo.MongoClient("YOUR_MONGO_URI_HERE")
db = mongo_client["AFKBot"]
afk_collection = db["afk_users"]

# Auto AFK Timeout (in seconds)
AUTO_AFK_TIMEOUT = 3600  # 1 hour

# Command to Set AFK (Supports Text & Image)
@Client.on_message(filters.command("afk") & (filters.private | filters.group))
async def set_afk(client, message: Message):
    user_id = message.from_user.id
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "I'm AFK!"
    afk_time = time.time()
    afk_image = None

    # Check if an image is attached
    if message.reply_to_message and message.reply_to_message.photo:
        afk_image = message.reply_to_message.photo.file_id

    afk_data = {"user_id": user_id, "reason": reason, "time": afk_time, "image": afk_image}
    afk_collection.update_one({"user_id": user_id}, {"$set": afk_data}, upsert=True)

    reply_text = f"🚶‍♂️ **{message.from_user.first_name}** is now AFK!\n\n📌 **Reason:** {reason}"
    if afk_image:
        await message.reply_photo(afk_image, caption=reply_text)
    else:
        await message.reply_text(reply_text)

# Detect Mentions & Notify the AFK User
@Client.on_message(filters.mentioned & ~filters.me)
async def mention_handler(client, message: Message):
    user_id = message.from_user.id
    afk_data = afk_collection.find_one({"user_id": user_id})

    if afk_data:
        afk_time = int(time.time() - afk_data["time"])
        minutes = afk_time // 60
        hours = minutes // 60
        afk_duration = f"{hours}h {minutes % 60}m" if hours > 0 else f"{minutes}m"
        reason = afk_data["reason"]
        afk_image = afk_data.get("image")

        reply_text = f"👤 **{message.from_user.first_name}** is AFK!\n\n📌 **Reason:** {reason}\n⏳ **Since:** {afk_duration} ago"
        
        if afk_image:
            await message.reply_photo(afk_image, caption=reply_text)
        else:
            await message.reply_text(reply_text)

        # Notify the AFK user in private
        try:
            await client.send_message(user_id, f"🔔 Someone mentioned you while you were AFK:\n📍 Chat: {message.chat.title}\n💬 Message: {message.text}")
        except Exception:
            pass

# Remove AFK Status When User Sends a Message
@Client.on_message(filters.text & (filters.private | filters.group))
async def remove_afk(client, message: Message):
    user_id = message.from_user.id
    afk_data = afk_collection.find_one({"user_id": user_id})

    if afk_data:
        afk_collection.delete_one({"user_id": user_id})
        afk_time = int(time.time() - afk_data["time"])
        minutes = afk_time // 60
        hours = minutes // 60
        afk_duration = f"{hours}h {minutes % 60}m" if hours > 0 else f"{minutes}m"

        await message.reply_text(f"✅ **{message.from_user.first_name}** is back!\n⏳ **AFK Duration:** {afk_duration}")

# Auto AFK Mode: Set AFK If User Is Inactive
@Client.on_message(filters.text & (filters.private | filters.group))
async def auto_afk(client, message: Message):
    user_id = message.from_user.id
    last_active = afk_collection.find_one({"user_id": user_id})

    if last_active and time.time() - last_active["time"] > AUTO_AFK_TIMEOUT:
        afk_collection.update_one({"user_id": user_id}, {"$set": {"time": time.time(), "reason": "Auto AFK"}})
        await message.reply_text(f"⏳ **{message.from_user.first_name}** is now AFK due to inactivity.")
