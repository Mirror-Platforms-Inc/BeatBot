"""
Secure credential storage using OS-level keyrings.

Addresses Moltbot's vulnerability of storing API keys in plaintext.
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes

import keyring
from keyring.errors import PasswordDeleteError
import base64


class CredentialManager:
    """
    Manages secure storage of credentials using OS keyring.
    
    Uses system keyring (Windows Credential Manager, macOS Keychain,
    Linux Secret Service) for maximum security.
    """
    
    SERVICE_NAME = "BeatBot"
    ENCRYPTION_KEY_NAME = "encryption_key"
    
    def __init__(self, use_encryption: bool = True):
        """
        Initialize credential manager.
        
        Args:
            use_encryption: Whether to use additional encryption layer
        """
        self.use_encryption = use_encryption
        self._cipher = None
        
        if use_encryption:
            self._initialize_encryption()
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption cipher with key from keyring or generate new one."""
        # Try to get existing encryption key
        key_str = keyring.get_password(self.SERVICE_NAME, self.ENCRYPTION_KEY_NAME)
        
        if key_str is None:
            # Generate new encryption key
            key = Fernet.generate_key()
            keyring.set_password(self.SERVICE_NAME, self.ENCRYPTION_KEY_NAME, key.decode())
            key_str = key.decode()
        
        self._cipher = Fernet(key_str.encode())
    
    def store_credential(self, name: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a credential securely.
        
        Args:
            name: Credential identifier (e.g., "discord_token", "api_key")
            value: Credential value to store
            metadata: Optional metadata about the credential
        """
        # Combine value and metadata
        data = {"value": value}
        if metadata:
            data["metadata"] = metadata
        
        data_str = json.dumps(data)
        
        # Encrypt if enabled
        if self.use_encryption and self._cipher:
            encrypted = self._cipher.encrypt(data_str.encode())
            store_value = base64.b64encode(encrypted).decode()
        else:
            store_value = data_str
        
        # Store in keyring
        keyring.set_password(self.SERVICE_NAME, name, store_value)
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Retrieve a credential.
        
        Args:
            name: Credential identifier
        
        Returns:
            Credential value or None if not found
        """
        stored_value = keyring.get_password(self.SERVICE_NAME, name)
        
        if stored_value is None:
            return None
        
        # Decrypt if enabled
        if self.use_encryption and self._cipher:
            try:
                encrypted = base64.b64decode(stored_value.encode())
                decrypted = self._cipher.decrypt(encrypted)
                data = json.loads(decrypted.decode())
            except Exception as e:
                raise CredentialError(f"Failed to decrypt credential '{name}': {str(e)}")
        else:
            data = json.loads(stored_value)
        
        return data.get("value")
    
    def get_credential_with_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a credential with its metadata.
        
        Args:
            name: Credential identifier
        
        Returns:
            Dict with 'value' and optional 'metadata' keys, or None if not found
        """
        stored_value = keyring.get_password(self.SERVICE_NAME, name)
        
        if stored_value is None:
            return None
        
        # Decrypt if enabled
        if self.use_encryption and self._cipher:
            try:
                encrypted = base64.b64decode(stored_value.encode())
                decrypted = self._cipher.decrypt(encrypted)
                data = json.loads(decrypted.decode())
            except Exception as e:
                raise CredentialError(f"Failed to decrypt credential '{name}': {str(e)}")
        else:
            data = json.loads(stored_value)
        
        return data
    
    def delete_credential(self, name: str) -> bool:
        """
        Delete a credential.
        
        Args:
            name: Credential identifier
        
        Returns:
            True if deleted, False if not found
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, name)
            return True
        except PasswordDeleteError:
            return False
    
    def list_credentials(self) -> list[str]:
        """
        List all stored credential names.
        
        Note: This is a basic implementation. Some keyring backends
        don't support listing, so this may return an empty list.
        
        Returns:
            List of credential identifiers
        """
        # This is backend-dependent and may not work with all keyrings
        # For production, consider maintaining a separate index
        try:
            # Try to access the credential backend
            backend = keyring.get_keyring()
            if hasattr(backend, 'get_all_passwords'):
                passwords = backend.get_all_passwords()
                return [p[1] for p in passwords if p[0] == self.SERVICE_NAME]
        except Exception:
            pass
        
        return []
    
    def rotate_encryption_key(self) -> None:
        """
        Rotate the encryption key.
        
        This will re-encrypt all stored credentials with a new key.
        WARNING: This operation should be done carefully and may fail
        if credentials cannot be accessed.
        """
        if not self.use_encryption:
            raise CredentialError("Encryption is not enabled")
        
        # Get all credentials with old key
        old_cipher = self._cipher
        credentials = {}
        
        # Try to get list of credentials
        # In practice, you'd need to maintain an index
        cred_names = self.list_credentials()
        
        for name in cred_names:
            if name == self.ENCRYPTION_KEY_NAME:
                continue
            value = self.get_credential(name)
            if value:
                credentials[name] = value
        
        # Generate new encryption key
        new_key = Fernet.generate_key()
        keyring.set_password(self.SERVICE_NAME, self.ENCRYPTION_KEY_NAME, new_key.decode())
        self._cipher = Fernet(new_key)
        
        # Re-encrypt all credentials
        for name, value in credentials.items():
            self.store_credential(name, value)


class CredentialError(Exception):
    """Raised when credential operations fail."""
    pass


# Environment variable fallback
class EnvCredentialManager:
    """
    Fallback credential manager that uses environment variables.
    
    Less secure than keyring, but useful for containerized environments
    where keyring may not be available.
    """
    
    ENV_PREFIX = "BEATBOT_CREDENTIAL_"
    
    def store_credential(self, name: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store credential in environment (session only)."""
        env_name = f"{self.ENV_PREFIX}{name.upper()}"
        os.environ[env_name] = value
    
    def get_credential(self, name: str) -> Optional[str]:
        """Retrieve credential from environment."""
        env_name = f"{self.ENV_PREFIX}{name.upper()}"
        return os.getenv(env_name)
    
    def delete_credential(self, name: str) -> bool:
        """Delete credential from environment."""
        env_name = f"{self.ENV_PREFIX}{name.upper()}"
        if env_name in os.environ:
            del os.environ[env_name]
            return True
        return False
    
    def list_credentials(self) -> list[str]:
        """List all credential names from environment."""
        prefix_len = len(self.ENV_PREFIX)
        return [
            key[prefix_len:].lower()
            for key in os.environ.keys()
            if key.startswith(self.ENV_PREFIX)
        ]


def get_credential_manager(prefer_keyring: bool = True) -> CredentialManager:
    """
    Get appropriate credential manager for the environment.
    
    Args:
        prefer_keyring: Prefer keyring over env vars if available
    
    Returns:
        CredentialManager or EnvCredentialManager instance
    """
    if prefer_keyring:
        try:
            # Test if keyring is available
            backend = keyring.get_keyring()
            if backend.priority > 0:  # Valid backend
                return CredentialManager()
        except Exception:
            pass
    
    # Fall back to environment variables
    return EnvCredentialManager()
