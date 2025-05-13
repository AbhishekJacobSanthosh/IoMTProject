from pymongo import MongoClient

# Your connection string
connection_string = "mongodb://localhost:27017"

try:
    # Attempt to connect
    client = MongoClient(connection_string)
    
    # Check if the connection is valid by listing databases
    dbs = client.list_database_names()
    print("Connection successful!")
    print("Available databases:", dbs)
    
except Exception as e:
    print("Connection failed:", e)
