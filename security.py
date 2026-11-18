"""
Security and Encryption utilities for Hospital LiFi System
Handles all encryption, decryption, and password operations
"""

import config
from config import fernet, Config
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
import hashlib
from datetime import datetime

class SecurityManager:
    """Manages all security and encryption operations"""
    
    @staticmethod
    def encrypt_data(data):
        """
        Encrypt string data using Fernet
        Args:
            data: String to encrypt
        Returns:
            Encrypted bytes
        """
        if isinstance(data, str):
            data = data.encode()
        return fernet.encrypt(data)
    
    @staticmethod
    def decrypt_data(encrypted_data):
        """
        Decrypt Fernet-encrypted data
        Args:
            encrypted_data: Encrypted bytes
        Returns:
            Decrypted string
        """
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return fernet.decrypt(encrypted_data).decode()
    
    @staticmethod
    def encrypt_file(file_path, original_filename):
        """
        Encrypt an entire file
        Args:
            file_path: Path to file to encrypt
            original_filename: Original name of the file
        Returns:
            Dictionary with encrypted file info
        """
        # Read file content
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encrypt the file data
        encrypted_data = fernet.encrypt(file_data)
        
        # Generate unique encrypted filename
        file_id = str(uuid.uuid4())
        encrypted_filename = f"{file_id}.encrypted"
        encrypted_path = os.path.join(Config.UPLOAD_FOLDER, encrypted_filename)
        
        # Save encrypted file
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Calculate integrity hash
        integrity_hash = hashlib.sha256(encrypted_data).hexdigest()
        
        # Clean up original file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {
            'file_id': file_id,
            'encrypted_path': encrypted_path,
            'encrypted_filename': encrypted_filename,
            'original_filename': original_filename,
            'file_size': len(encrypted_data),
            'integrity_hash': integrity_hash,
            'encryption_timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def decrypt_file(encrypted_path):
        """
        Decrypt an encrypted file (returns decrypted data, doesn't save)
        Args:
            encrypted_path: Path to encrypted file
        Returns:
            Decrypted file bytes
        """
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        return fernet.decrypt(encrypted_data)
    
    @staticmethod
    def verify_file_integrity(encrypted_path, expected_hash):
        """
        Verify encrypted file integrity
        Args:
            encrypted_path: Path to encrypted file
            expected_hash: Expected SHA256 hash
        Returns:
            Boolean indicating if file is intact
        """
        try:
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            actual_hash = hashlib.sha256(encrypted_data).hexdigest()
            return actual_hash == expected_hash
        except:
            return False
    
    @staticmethod
    def hash_password(password):
        """
        Hash password for storage
        Args:
            password: Plain text password
        Returns:
            Hashed password
        """
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @staticmethod
    def verify_password(password, password_hash):
        """
        Verify password against hash
        Args:
            password: Plain text password
            password_hash: Stored hash
        Returns:
            Boolean indicating if password matches
        """
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def generate_handoff_session_id():
        """
        Generate unique handoff session identifier
        Returns:
            Session ID string
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"LIFI-{timestamp}-{unique_id}"
    
    @staticmethod
    def generate_integrity_hash(data):
        """
        Generate SHA256 hash for data integrity
        Args:
            data: Data to hash (string or bytes)
        Returns:
            Hex digest string
        """
        if isinstance(data, str):
            data = data.encode()
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def encrypt_message(message):
        """
        Encrypt a message for shared secrets
        Args:
            message: Plain text message
        Returns:
            Dictionary with encrypted message and metadata
        """
        encrypted = SecurityManager.encrypt_data(message)
        integrity_hash = SecurityManager.generate_integrity_hash(encrypted)
        
        return {
            'encrypted_message': encrypted.decode(),
            'integrity_hash': integrity_hash,
            'algorithm': Config.ENCRYPTION_ALGORITHM,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def decrypt_message(encrypted_message_dict):
        """
        Decrypt a message and verify integrity
        Args:
            encrypted_message_dict: Dictionary with encrypted message
        Returns:
            Decrypted message or None if integrity check fails
        """
        try:
            encrypted = encrypted_message_dict['encrypted_message']
            expected_hash = encrypted_message_dict['integrity_hash']
            
            # Verify integrity first
            actual_hash = SecurityManager.generate_integrity_hash(encrypted.encode())
            if actual_hash != expected_hash:
                return None
            
            # Decrypt
            return SecurityManager.decrypt_data(encrypted)
        except:
            return None
    
    @staticmethod
    def get_static_key_display():
        """
        Get masked display of static encryption key
        Returns: Masked key string (first 8 and last 8 characters visible)
        """
        key = config.STATIC_FERNET_KEY.decode()
        if len(key) > 16:
            return f"{key[:8]}...{key[-8:]}"
        return key[:4] + "..." + key[-4:]
    
    @staticmethod
    def validate_file_extension(filename):
        """
        Validate file extension
        Args:
            filename: Name of file to validate
        Returns:
            Boolean indicating if extension is allowed
        """
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in Config.ALLOWED_EXTENSIONS

# Global security manager instance
security = SecurityManager()
