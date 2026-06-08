from pymongo import MongoClient

# Paste your exact URL here, the exact same one you put in Azure
uri = "mongodb+srv://MLAdmin:TestPass1234@mlproject.8tzzzh8.mongodb.net/?appName=MLProject"

print("Attempting to connect to MongoDB...")
try:
    client = MongoClient(uri)
    # The 'ping' command forces a connection test
    client.admin.command('ping')
    print("✅ SUCCESS! The username and password are correct!")
except Exception as e:
    print("❌ FAILED!")
    print(e)