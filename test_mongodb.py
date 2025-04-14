from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

def test_mongodb_connection():
    # Load environment variables
    load_dotenv()
    
    # Get MongoDB URI
    uri = os.getenv('MONGODB_URI')
    if not uri:
        print("Error: MONGODB_URI environment variable not found")
        return False
    
    print(f"Testing MongoDB connection with URI starting with: {uri[:30]}...")
    
    try:
        # Create client with short timeout
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        print("Attempting server info...")
        info = client.server_info()
        
        print("Connection successful!")
        print(f"Server info: {info}")
        
        # List databases
        databases = client.list_database_names()
        print(f"Available databases: {databases}")
        
        # Test btcbuzzbot database and collections
        db = client.btcbuzzbot
        
        # Create test document
        test_result = db.test_collection.insert_one({"test": "MongoDB connection test", "timestamp": "now"})
        print(f"Inserted test document with ID: {test_result.inserted_id}")
        
        # Delete test document
        db.test_collection.delete_one({"_id": test_result.inserted_id})
        print("Test document deleted")
        
        return True
    
    except Exception as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = test_mongodb_connection()
    if success:
        print("\nMongoDB connection test passed!")
    else:
        print("\nMongoDB connection test failed!")
        sys.exit(1) 