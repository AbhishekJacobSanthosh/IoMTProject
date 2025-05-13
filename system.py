from blockchain import Blockchain, Block
from encryption import DataEncryptor
from iomt_simulator import IoMTDeviceSimulator
from smart_contract import HealthSmartContract
import time
import json
import os
import datetime

class HealthMonitoringSystem:
    def __init__(self, mongo):
        self.blockchain = Blockchain()
        self.encryptor = DataEncryptor()
        self.contract = HealthSmartContract()
        self.device = IoMTDeviceSimulator()
        self.patients = {}  # Dictionary to store patient data
        self.mongo = mongo  # MongoDB connection
        
        # MongoDB collections
        self.patients_collection = mongo.db.patients
        self.health_records_collection = mongo.db.health_records
        self.blockchain_collection = mongo.db.blockchain

    def process_health_data(self, custom_data=None, skip_db_save=False):
        # Use custom data if provided, otherwise generate random data
        raw_data = custom_data if custom_data else self.device.generate_health_data()
        
        # Check for alerts using smart contract
        alerts = self.contract.check_vitals(raw_data)
        raw_data['alerts'] = alerts
        
        # Store patient ID for future reference
        patient_id = raw_data['patient_id']
        if patient_id not in self.patients:
            self.patients[patient_id] = []
        self.patients[patient_id].append(raw_data)
        
        # Encrypt data before storing in blockchain
        encrypted_data = self.encryptor.encrypt_data(raw_data)
        
        # Create and add new block
        new_block = Block(
            index=len(self.blockchain.chain),
            timestamp=time.time(),
            data=encrypted_data.decode(),
            previous_hash=self.blockchain.get_latest_block().hash
        )
        self.blockchain.add_block(new_block)
        
        # Store in MongoDB with explicit error handling
        if not skip_db_save:
            try:
                # Save health record
                health_record = raw_data.copy()
                health_record['block_hash'] = new_block.hash
                health_record['block_index'] = new_block.index
                health_record['created_at'] = datetime.datetime.now()
                
                record_result = self.health_records_collection.insert_one(health_record)
                print(f"Health record saved to MongoDB with ID: {record_result.inserted_id}")
                
                # Save blockchain data
                block_data = {
                    'index': new_block.index,
                    'timestamp': new_block.timestamp,
                    'hash': new_block.hash,
                    'previous_hash': new_block.previous_hash,
                    'patient_id': patient_id,
                    'created_at': datetime.datetime.now()
                }
                block_result = self.blockchain_collection.insert_one(block_data)
                print(f"Blockchain data saved to MongoDB with ID: {block_result.inserted_id}")
                
                # Update patient record if it exists
                patient_exists = self.patients_collection.find_one({'patient_id': patient_id})
                if patient_exists:
                    update_result = self.patients_collection.update_one(
                        {'patient_id': patient_id},
                        {'$push': {'records': str(record_result.inserted_id)}}
                    )
                    print(f"Patient record updated: {update_result.modified_count} document(s) modified")
            except Exception as e:
                print(f"Error saving to MongoDB: {e}")
        
        return new_block, alerts, raw_data

    def view_medical_history(self, patient_id):
        # Get history from MongoDB for better performance
        try:
            records = list(self.health_records_collection.find({'patient_id': patient_id}).sort('timestamp', -1))
            if records:
                # Convert ObjectId to string for JSON serialization
                for record in records:
                    if '_id' in record:
                        record['_id'] = str(record['_id'])
                return records
        except Exception as e:
            print(f"Error retrieving from MongoDB: {e}")
        
        # Fallback to blockchain if MongoDB fails
        history = []
        for block in self.blockchain.chain[1:]:  # Skip genesis block
            try:
                decrypted = self.encryptor.decrypt_data(block.data.encode())
                if decrypted['patient_id'] == patient_id:
                    history.append(decrypted)
            except Exception as e:
                # Skip blocks that can't be decrypted
                pass
        return history

    def get_all_patients(self):
        # Get all patients from MongoDB
        try:
            patients = [p['patient_id'] for p in self.patients_collection.find()]
            return patients
        except Exception as e:
            print(f"Error retrieving patients from MongoDB: {e}")
            return list(self.patients.keys())

    def get_blockchain_data(self):
        # Get blockchain data from MongoDB for better performance
        try:
            blocks = list(self.blockchain_collection.find().sort('index', 1))
            if blocks:
                blockchain_data = []
                for block in blocks:
                    # Get corresponding health record
                    health_record = self.health_records_collection.find_one({'block_hash': block['hash']})
                    if health_record:
                        # Convert ObjectId to string for JSON serialization
                        if '_id' in health_record:
                            health_record['_id'] = str(health_record['_id'])
                        if '_id' in block:
                            block['_id'] = str(block['_id'])
                        
                        block_info = {
                            'index': block['index'],
                            'timestamp': block['timestamp'],
                            'hash': block['hash'],
                            'previous_hash': block['previous_hash'],
                            'data': health_record
                        }
                        blockchain_data.append(block_info)
                return blockchain_data
        except Exception as e:
            print(f"Error retrieving blockchain data from MongoDB: {e}")
        
        # Fallback to blockchain if MongoDB fails
        blockchain_data = []
        for block in self.blockchain.chain[1:]:  # Skip genesis block
            try:
                decrypted = self.encryptor.decrypt_data(block.data.encode())
                block_info = {
                    'index': block.index,
                    'timestamp': block.timestamp,
                    'hash': block.hash,
                    'previous_hash': block.previous_hash,
                    'data': decrypted
                }
                blockchain_data.append(block_info)
            except Exception as e:
                # Skip blocks that can't be decrypted
                pass
        return blockchain_data

    def get_patient_blockchain_data(self, patient_id):
        # Get blockchain data for a specific patient
        try:
            blocks = list(self.blockchain_collection.find({'patient_id': patient_id}).sort('index', 1))
            if blocks:
                blockchain_data = []
                for block in blocks:
                    # Get corresponding health record
                    health_record = self.health_records_collection.find_one({'block_hash': block['hash']})
                    if health_record:
                        # Convert ObjectId to string for JSON serialization
                        if '_id' in health_record:
                            health_record['_id'] = str(health_record['_id'])
                        if '_id' in block:
                            block['_id'] = str(block['_id'])
                        
                        block_info = {
                            'index': block['index'],
                            'timestamp': block['timestamp'],
                            'hash': block['hash'],
                            'previous_hash': block['previous_hash'],
                            'data': health_record
                        }
                        blockchain_data.append(block_info)
                return blockchain_data
        except Exception as e:
            print(f"Error retrieving patient blockchain data from MongoDB: {e}")
        
        # Fallback to filtering all blockchain data
        return [block for block in self.get_blockchain_data() if block['data']['patient_id'] == patient_id]
    
    def remove_patient(self, patient_id):
        """
        Remove a patient from the system.
        Note: This doesn't remove blocks from the blockchain (as that would violate immutability),
        but it removes the patient from the patients dictionary.
        """
        if patient_id in self.patients:
            del self.patients[patient_id]
            return True
        return False
    
    def save_state(self):
        """Save blockchain data to MongoDB"""
        try:
            for block in self.blockchain.chain:
                # Skip genesis block
                if block.index == 0:
                    continue
                    
                # Check if block already exists in MongoDB
                existing_block = self.blockchain_collection.find_one({'hash': block.hash})
                if existing_block:
                    continue
                    
                try:
                    # For each block, try to decrypt and save data
                    decrypted_data = self.encryptor.decrypt_data(block.data.encode())
                    
                    # Save blockchain data
                    block_data = {
                        'index': block.index,
                        'timestamp': block.timestamp,
                        'hash': block.hash,
                        'previous_hash': block.previous_hash,
                        'patient_id': decrypted_data.get('patient_id', 'unknown'),
                        'created_at': datetime.datetime.now()
                    }
                    self.blockchain_collection.insert_one(block_data)
                    
                    # Save health record
                    health_record = decrypted_data.copy()
                    health_record['block_hash'] = block.hash
                    health_record['block_index'] = block.index
                    health_record['created_at'] = datetime.datetime.now()
                    self.health_records_collection.insert_one(health_record)
                    
                    # Update patient record
                    patient_id = decrypted_data.get('patient_id')
                    if patient_id and patient_id != 'unknown':
                        self.patients_collection.update_one(
                            {'patient_id': patient_id},
                            {'$push': {'records': block.hash}},
                            upsert=True
                        )
                except Exception as e:
                    print(f"Error processing block {block.index}: {e}")
            
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    def load_state(self):
        """Load blockchain data from MongoDB"""
        try:
            # Clear existing chain except genesis block
            self.blockchain.chain = [self.blockchain.chain[0]]
            
            # Load blockchain data from MongoDB
            blocks = list(self.blockchain_collection.find().sort('index', 1))
            if not blocks:
                return False
                
            # Load patients from MongoDB
            patients = list(self.patients_collection.find())
            for patient in patients:
                patient_id = patient.get('patient_id')
                if patient_id and patient_id not in self.patients:
                    self.patients[patient_id] = []
            
            # Reconstruct blockchain directly without calling process_health_data
            for block_data in blocks:
                # Get corresponding health record
                health_record = self.health_records_collection.find_one({'block_hash': block_data['hash']})
                if health_record:
                    # Create a new block directly
                    try:
                        # Remove MongoDB-specific fields for encryption
                        health_record_copy = health_record.copy()
                        if '_id' in health_record_copy:
                            del health_record_copy['_id']
                        if 'created_at' in health_record_copy:
                            del health_record_copy['created_at']
                        if 'block_hash' in health_record_copy:
                            del health_record_copy['block_hash']
                        if 'block_index' in health_record_copy:
                            del health_record_copy['block_index']
                        
                        # Encrypt the data
                        encrypted_data = self.encryptor.encrypt_data(health_record_copy)
                        
                        # Create a new block with the original hash and data
                        new_block = Block(
                            index=block_data['index'],
                            timestamp=block_data['timestamp'],
                            data=encrypted_data.decode(),
                            previous_hash=block_data['previous_hash']
                        )
                        
                        # Set the hash to match the stored hash
                        new_block.hash = block_data['hash']
                        
                        # Add to blockchain directly (not through process_health_data)
                        self.blockchain.chain.append(new_block)
                        
                        # Update patients dictionary
                        patient_id = health_record_copy.get('patient_id')
                        if patient_id and patient_id not in self.patients:
                            self.patients[patient_id] = []
                        if patient_id:
                            self.patients[patient_id].append(health_record_copy)
                    except Exception as e:
                        print(f"Error reconstructing block {block_data['index']}: {e}")
            
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False

    # Add a method to clear the database for testing
    def clear_database(self):
        """Clear all data from MongoDB collections"""
        try:
            self.health_records_collection.delete_many({})
            self.blockchain_collection.delete_many({})
            # Don't delete patients to preserve user accounts
            # self.patients_collection.delete_many({})
            print("Database cleared successfully")
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
