from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Replace with your actual connection string
MONGO_URL = "mongodb+srv://srs_engine_user:srs_engine_123456@cluster0.asyoy.mongodb.net/?appName=Cluster0"

try:
    # Create client
    client = MongoClient(MONGO_URL)

    # The ping command checks the connection
    client.admin.command("ping")

    print("✅ Successfully connected to MongoDB Atlas!")

except ConnectionFailure as e:
    print("❌ Connection failed:", e)

except Exception as e:
    print("⚠️ Something went wrong:", e)