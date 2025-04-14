import os
import sys
import socket
import requests
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in environment variables")
    sys.exit(1)
    
print(f"MongoDB URI: {mongodb_uri[:30]}...")

# Get system info
print("\nSystem Information:")
print(f"Hostname: {socket.gethostname()}")
try:
    print(f"External IP: {requests.get('https://api.ipify.org').text}")
except:
    print("Could not determine external IP")
print(f"Python version: {sys.version}")

try:
    # Import pymongo here to isolate any import errors
    print("\nImporting pymongo...")
    import pymongo
    print(f"PyMongo version: {pymongo.__version__}")
    
    # Create client with detailed options
    print("\nCreating MongoDB client...")
    client = pymongo.MongoClient(
        mongodb_uri, 
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
    
    # Test connection
    print("Testing connection...")
    server_info = client.server_info()
    
    print("\n✅ MongoDB connection successful!")
    print(f"Server info: {server_info}")
    
    # List databases
    print("\nListing databases...")
    databases = client.list_database_names()
    print(f"Available databases: {databases}")
    
    # Test database access
    print("\nTesting database access...")
    db = client.btcbuzzbot
    
    # Test collection access
    print("Testing collection creation...")
    test_collection = db.test_connection
    
    # Insert test document
    print("Inserting test document...")
    test_result = test_collection.insert_one({"test": "connection", "timestamp": datetime.datetime.now()})
    print(f"Inserted document ID: {test_result.inserted_id}")
    
    # Query test document
    print("Querying test document...")
    found = test_collection.find_one({"_id": test_result.inserted_id})
    print(f"Found document: {found}")
    
    # Clean up
    print("Cleaning up test document...")
    test_collection.delete_one({"_id": test_result.inserted_id})
    print("Test document deleted")
    
    print("\n🎉 All MongoDB tests passed successfully!")
    
except ImportError as e:
    print(f"\n❌ Error importing module: {e}", file=sys.stderr)
    sys.exit(1)
except pymongo.errors.ConfigurationError as e:
    print(f"\n❌ MongoDB configuration error: {e}", file=sys.stderr)
    print("This could be due to an invalid connection string format")
    sys.exit(1)
except pymongo.errors.ServerSelectionTimeoutError as e:
    print(f"\n❌ MongoDB server selection timeout: {e}", file=sys.stderr)
    print("This could be due to network issues, firewall settings, or incorrect host in connection string")
    sys.exit(1)
except pymongo.errors.OperationFailure as e:
    print(f"\n❌ MongoDB operation failure: {e}", file=sys.stderr)
    
    if "auth failed" in str(e).lower():
        print("This is an authentication error - check your username and password")
    elif "not authorized" in str(e).lower():
        print("This is a permissions error - check that the user has the right permissions")
    
    sys.exit(1)
except Exception as e:
    print(f"\n❌ MongoDB connection error: {e}", file=sys.stderr)
    sys.exit(1) 