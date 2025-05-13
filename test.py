from pymongo import MongoClient
import datetime

def test_mongodb_connection():
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["iomt_blockchain_db"]
        
        # Print available databases
        print("Available databases:", client.list_database_names())
        
        # Create test collections if they don't exist
        if "test_collection" not in db.list_collection_names():
            db.create_collection("test_collection")
        
        # Insert a test document
        test_collection = db["test_collection"]
        test_document = {
            "name": "Test Patient",
            "created_at": datetime.datetime.now()
        }
        
        result = test_collection.insert_one(test_document)
        print(f"Test document inserted with ID: {result.inserted_id}")
        
        # Verify the document was inserted
        inserted_doc = test_collection.find_one({"_id": result.inserted_id})
        if inserted_doc:
            print("Document successfully inserted and retrieved")
            print(f"Document content: {inserted_doc}")
        else:
            print("Failed to retrieve inserted document")
        
        # List all collections
        print("Collections in database:", db.list_collection_names())
        
        return True
    except Exception as e:
        print(f"MongoDB test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_mongodb_connection()
    print(f"MongoDB connection test {'succeeded' if success else 'failed'}")
