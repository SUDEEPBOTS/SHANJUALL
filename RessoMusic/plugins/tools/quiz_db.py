from RessoMusic.misc import mongodb

# Collections
quizdb = mongodb.anime_quiz_users
settingsdb = mongodb.anime_quiz_settings
questionsdb = mongodb.anime_quiz_questions
apidb = mongodb.anime_quiz_api
useddb = mongodb.anime_quiz_history  # NEW: Ye purane questions yaad rakhega

# --- SMALL CAPS CONVERTER ---
def smcp(text):
    mapping = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
    }
    return "".join(mapping.get(c, c) for c in text)

# --- USER FUNCTIONS ---
async def add_points(user_id, name, points):
    user = await quizdb.find_one({"user_id": user_id})
    if user:
        new_pts = user["points"] + points
        await quizdb.update_one({"user_id": user_id}, {"$set": {"points": new_pts, "name": name}})
    else:
        await quizdb.insert_one({"user_id": user_id, "name": name, "points": points})

async def get_leaderboard(limit=10):
    cursor = quizdb.find().sort("points", -1).limit(limit)
    return [doc async for doc in cursor]

async def reset_leaderboard():
    await quizdb.delete_many({})

# --- SETTINGS & PRIZES ---
async def set_prize(text):
    await settingsdb.update_one({"_id": "prizes"}, {"$set": {"text": text}}, upsert=True)

async def get_prize():
    doc = await settingsdb.find_one({"_id": "prizes"})
    return doc["text"] if doc else smcp("No Prizes Announced Yet.")

async def get_stored_month():
    doc = await settingsdb.find_one({"_id": "current_season"})
    return doc["month"] if doc else None

async def set_stored_month(month_str):
    await settingsdb.update_one({"_id": "current_season"}, {"$set": {"month": month_str}}, upsert=True)

# --- GROQ API MANAGEMENT ---
async def add_api_key(key):
    exist = await apidb.find_one({"key": key})
    if not exist:
        await apidb.insert_one({"key": key})
        return True
    return False

async def remove_api_key(key):
    result = await apidb.delete_one({"key": key})
    return result.deleted_count > 0

async def get_random_api_key():
    pipeline = [{"$sample": {"size": 1}}]
    cursor = apidb.aggregate(pipeline)
    async for doc in cursor:
        return doc["key"]
    return None

# --- DUPLICATE CHECKER (HISTORY) ---
async def is_question_used(q_text):
    # Check if exact question text exists in history
    found = await useddb.find_one({"q": q_text})
    return bool(found)

async def mark_question_used(q_text):
    # Save question to history
    await useddb.insert_one({"q": q_text})

# --- QUESTIONS (Hybrid) ---
async def add_question(question, options, correct_answer):
    await questionsdb.insert_one({
        "q": question,
        "o": options,
        "a": correct_answer
    })

async def get_random_question():
    pipeline = [{"$sample": {"size": 1}}]
    cursor = questionsdb.aggregate(pipeline)
    async for doc in cursor:
        return doc
    return None
    
