import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
print(">>> DEBUG MONGO_URI:", MONGO_URI)
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("MONGO_COLL")

print("Connecting to MongoDB at", MONGO_URI)
print("Using database:", DB_NAME)
print("Using collection:", COLLECTION_NAME)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

doc = {
    "title": "Hello Mongo",
    "authors": ["Test Author"],
    "summary": "Inserted from Python.",
    "published": "2025-09-19",
    "link": "http://arxiv.org/abs/test"
}
inserted_id = collection.insert_one(doc).inserted_id
print(f"✅ Inserted document with _id={inserted_id}")

result = collection.find_one({"_id": inserted_id})
print("📄 Found:", result)


# import os
# from pymongo import MongoClient

# MONGO_URI = os.getenv("MONGO_URI")
# print(">>> MONGO_URI =", MONGO_URI)

# client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)

# try:
#     print(">>> PING:", client.admin.command("ping"))
# except Exception as e:
#     print(">>> ERROR:", e)