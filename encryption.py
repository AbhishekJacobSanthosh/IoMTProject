from cryptography.fernet import Fernet
import json
import os

class DataEncryptor:
    def __init__(self):
        self.key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datastore', 'encryption_key.key')
        self.key = self._load_or_generate_key()
        self.cipher_suite = Fernet(self.key)

    def _load_or_generate_key(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        
        # Load existing key or generate new one
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as key_file:
                key_file.write(key)
            return key

    def encrypt_data(self, data):
        """Encrypt data using Fernet symmetric encryption"""
        json_data = json.dumps(data).encode()
        encrypted = self.cipher_suite.encrypt(json_data)
        return encrypted

    def decrypt_data(self, encrypted_data):
        """Decrypt data using Fernet symmetric encryption"""
        decrypted = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
