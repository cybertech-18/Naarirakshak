"""
End-to-end encryption for sensitive data
"""
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import os
import json
import base64
from typing import Dict, Any


class EncryptionManager:
    """Handles encryption/decryption of sensitive data"""
    
    def __init__(self, master_key: bytes = None):
        """
        Initialize encryption manager
        
        Args:
            master_key: Master encryption key (32 bytes)
        """
        if master_key is None:
            # Generate a random key for demo (in production, use secure key storage)
            master_key = os.urandom(32)
        
        self.master_key = master_key
        self.aesgcm = AESGCM(self.master_key)
    
    def generate_session_key(self) -> bytes:
        """Generate a unique session key for each alert"""
        return os.urandom(32)
    
    def encrypt_location(self, latitude: float, longitude: float, 
                        accuracy: float = None, session_key: bytes = None) -> Dict[str, str]:
        """
        Encrypt GPS location data
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            accuracy: GPS accuracy in meters
            session_key: Optional session-specific key
            
        Returns:
            Dictionary with encrypted data and metadata
        """
        # Use session key or master key
        key = session_key if session_key else self.master_key
        aesgcm = AESGCM(key)
        
        # Prepare location data
        location_data = {
            'lat': latitude,
            'lng': longitude,
            'accuracy': accuracy,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Convert to JSON and encode
        plaintext = json.dumps(location_data).encode('utf-8')
        
        # Generate nonce (96 bits for AES-GCM)
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # Return base64-encoded values
        return {
            'encrypted_data': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'algorithm': 'AES-256-GCM'
        }
    
    def decrypt_location(self, encrypted_data: str, nonce: str, 
                        session_key: bytes = None) -> Dict[str, Any]:
        """
        Decrypt GPS location data
        
        Args:
            encrypted_data: Base64-encoded ciphertext
            nonce: Base64-encoded nonce
            session_key: Optional session-specific key
            
        Returns:
            Decrypted location data
        """
        try:
            # Use session key or master key
            key = session_key if session_key else self.master_key
            aesgcm = AESGCM(key)
            
            # Decode from base64
            ciphertext = base64.b64decode(encrypted_data)
            nonce_bytes = base64.b64decode(nonce)
            
            # Decrypt
            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext, None)
            
            # Parse JSON
            location_data = json.loads(plaintext.decode('utf-8'))
            
            return location_data
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_user_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt user profile data
        
        Args:
            data: Dictionary with user data
            
        Returns:
            Encrypted data with metadata
        """
        plaintext = json.dumps(data).encode('utf-8')
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        
        return {
            'encrypted_data': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8')
        }
    
    def decrypt_user_data(self, encrypted_data: str, nonce: str) -> Dict[str, Any]:
        """
        Decrypt user profile data
        
        Args:
            encrypted_data: Base64-encoded ciphertext
            nonce: Base64-encoded nonce
            
        Returns:
            Decrypted user data
        """
        try:
            ciphertext = base64.b64decode(encrypted_data)
            nonce_bytes = base64.b64decode(nonce)
            plaintext = self.aesgcm.decrypt(nonce_bytes, ciphertext, None)
            return json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def hash_phone_number(self, phone: str, salt: bytes = None) -> tuple:
        """
        Hash phone number for privacy-preserving storage
        
        Args:
            phone: Phone number to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_phone, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        hashed = kdf.derive(phone.encode('utf-8'))
        
        return (
            base64.b64encode(hashed).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    def generate_ephemeral_id(self, user_id: int, rotation_date: str = None) -> str:
        """
        Generate rotating ephemeral user ID
        
        Args:
            user_id: Internal user ID
            rotation_date: Date for rotation (YYYY-MM-DD)
            
        Returns:
            Ephemeral ID (changes daily)
        """
        from datetime import datetime
        
        if rotation_date is None:
            rotation_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Combine user_id with rotation date
        data = f"{user_id}:{rotation_date}".encode('utf-8')
        
        # Hash to generate ephemeral ID
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data)
        digest.update(self.master_key)
        hash_bytes = digest.finalize()
        
        # Return first 16 bytes as hex
        return hash_bytes[:16].hex()
    
    def create_access_token(self, alert_id: str, responder_id: str, 
                           expiry_minutes: int = 60) -> str:
        """
        Create time-limited access token for alert data
        
        Args:
            alert_id: Alert identifier
            responder_id: Responder identifier
            expiry_minutes: Token validity in minutes
            
        Returns:
            Access token
        """
        from datetime import datetime, timedelta
        
        expiry = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        token_data = {
            'alert_id': alert_id,
            'responder_id': responder_id,
            'expiry': expiry.isoformat()
        }
        
        plaintext = json.dumps(token_data).encode('utf-8')
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        
        # Combine nonce and ciphertext
        token = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
        return token
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode access token
        
        Args:
            token: Access token to verify
            
        Returns:
            Decoded token data if valid
            
        Raises:
            ValueError if token is invalid or expired
        """
        from datetime import datetime
        
        try:
            # Decode token
            data = base64.urlsafe_b64decode(token)
            nonce = data[:12]
            ciphertext = data[12:]
            
            # Decrypt
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            token_data = json.loads(plaintext.decode('utf-8'))
            
            # Check expiry
            expiry = datetime.fromisoformat(token_data['expiry'])
            if datetime.utcnow() > expiry:
                raise ValueError("Token expired")
            
            return token_data
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")


# Global encryption manager instance
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        master_key = None

        # Try to load key from env
        key_hex = os.getenv('ENCRYPTION_KEY')
        if key_hex:
            try:
                master_key = bytes.fromhex(key_hex)
            except ValueError:
                print("Invalid ENCRYPTION_KEY format.")

        if master_key is None:
            # Try to load key from file
            base_path = os.path.dirname(os.path.abspath(__file__))
            key_file = os.path.join(base_path, 'encryption.key')

            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    master_key = f.read()
            else:
                # Generate new key and save it
                master_key = os.urandom(32)
                try:
                    with open(key_file, 'wb') as f:
                        f.write(master_key)
                    # Set restrictive permissions (read/write for owner only)
                    os.chmod(key_file, 0o600)
                except Exception as e:
                    print(f"Warning: Could not save encryption key: {e}")

        _encryption_manager = EncryptionManager(master_key)
    return _encryption_manager


# Import datetime for use in methods
from datetime import datetime
