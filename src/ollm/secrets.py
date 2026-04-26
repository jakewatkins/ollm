"""Azure Key Vault secrets management for ollm."""

import re
import logging
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import AzureCliCredential
    from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError, HttpResponseError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    SecretClient = None
    AzureCliCredential = None
    ResourceNotFoundError = Exception
    ClientAuthenticationError = Exception
    HttpResponseError = Exception

# Use basic logging instead of importing logging setup to avoid circular imports
logger = logging.getLogger(__name__)

# Pattern for secret references: {SecretName} or {SecretName:default_value}
SECRET_PATTERN = re.compile(r'\{([a-zA-Z0-9-]+)(?::([^}]*))?\}')


class SecretsManager:
    """Manages Azure Key Vault secrets for ollm."""
    
    def __init__(self, keyvault_name: Optional[str] = None, verbose: bool = False):
        self.keyvault_name = keyvault_name
        self.verbose = verbose
        self.vault_url = f"https://{keyvault_name}.vault.azure.net/" if keyvault_name else None
        self.client: Optional[SecretClient] = None
        self.secret_cache: Dict[str, str] = {}
        self.vault_accessible = False
        
        if keyvault_name and AZURE_AVAILABLE:
            self._initialize_client()
        elif keyvault_name and not AZURE_AVAILABLE:
            self._log_warning("Azure dependencies not installed. Install with: pip install azure-keyvault-secrets azure-identity")
        
    def _log_warning(self, message: str) -> None:
        """Log warning message and optionally print to console."""
        if self.verbose:
            # Use warning level for console output when verbose
            logger.warning(message)
        else:
            # Use info level to avoid console output when not verbose
            logger.info(f"Warning: {message}")
    
    def _initialize_client(self) -> None:
        """Initialize the Azure Key Vault client."""
        try:
            credential = AzureCliCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
            self.vault_accessible = True
            logger.info(f"Azure Key Vault client initialized for vault: {self.keyvault_name}")
        except Exception as e:
            self._log_warning(f"Failed to initialize Key Vault client for '{self.keyvault_name}': {e}")
            self.vault_accessible = False
    
    def test_vault_access(self) -> bool:
        """Test access to the Key Vault at startup with retry logic."""
        if not self.client:
            self._log_warning(f"Key Vault '{self.keyvault_name}' client not initialized. Secret references will fail unless defaults are provided.")
            return False
            
        # If we already know the vault is accessible, return quickly
        if self.vault_accessible:
            return True
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try to list secrets to test connectivity
                list(self.client.list_properties_of_secrets())
                self.vault_accessible = True
                logger.info(f"Successfully connected to Key Vault: {self.keyvault_name}")
                return True
                
            except ClientAuthenticationError:
                if attempt == max_retries - 1:
                    self._log_warning(f"Authentication failed for Key Vault '{self.keyvault_name}' after {max_retries} attempts. Please ensure you're logged in with 'az login'.")
                    self.vault_accessible = False
                    return False
                else:
                    logger.debug(f"Authentication attempt {attempt + 1} failed for Key Vault '{self.keyvault_name}', retrying...")
                    
            except HttpResponseError as e:
                self._log_warning(f"Access denied to Key Vault '{self.keyvault_name}': {e}")
                self.vault_accessible = False
                return False
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self._log_warning(f"Failed to connect to Key Vault '{self.keyvault_name}' after {max_retries} attempts: {e}")
                    self.vault_accessible = False
                    return False
                else:
                    logger.debug(f"Connection attempt {attempt + 1} failed for Key Vault '{self.keyvault_name}': {e}, retrying...")
        
        # This should never be reached, but just in case
        self.vault_accessible = False
        return False
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieve a secret from Azure Key Vault.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value if found, None otherwise
        """
        # Check cache first
        if secret_name in self.secret_cache:
            return self.secret_cache[secret_name]
        
        if not self.client or not self.vault_accessible:
            self._log_warning(f"Cannot fetch secret '{secret_name}': vault not accessible")
            return None
            
        try:
            secret = self.client.get_secret(secret_name)
            secret_value = secret.value
            # Cache the secret
            self.secret_cache[secret_name] = secret_value
            logger.debug(f"Successfully retrieved secret: {secret_name}")
            return secret_value
        except ResourceNotFoundError:
            self._log_warning(f"Secret '{secret_name}' not found in Key Vault '{self.keyvault_name}'")
            return None
        except Exception as e:
            self._log_warning(f"Failed to retrieve secret '{secret_name}': {e}")
            return None
    
    def validate_secret_references(self, text: str) -> Tuple[bool, str]:
        """Validate that secret references have proper syntax.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for unclosed braces
        open_braces = text.count('{')
        close_braces = text.count('}')
        
        if open_braces != close_braces:
            return False, f"Mismatched braces in secret references: {open_braces} opening, {close_braces} closing"
        
        # Check for invalid secret names
        matches = SECRET_PATTERN.findall(text)
        
        # Check if there are braces but no matches (invalid format)
        if '{' in text and '}' in text and not matches:
            return False, "Invalid secret reference format found"
        
        for secret_name, default_value in matches:
            if not secret_name:
                return False, "Empty secret name found in reference"
            # Azure Key Vault secret names can only contain alphanumeric characters and dashes
            if not re.match(r'^[a-zA-Z0-9-]+$', secret_name):
                return False, f"Invalid secret name '{secret_name}': must contain only alphanumeric characters and dashes"
        
        return True, ""
    
    def process_secrets(self, text: str) -> str:
        """Process secret references in text, replacing them with actual values.
        
        Args:
            text: Text containing secret references
            
        Returns:
            Text with secret references replaced
        """
        if not text or not isinstance(text, str):
            return text
            
        # Validate secret syntax first
        is_valid, error_msg = self.validate_secret_references(text)
        if not is_valid:
            self._log_warning(f"Invalid secret reference syntax: {error_msg}")
            return text
        
        def replace_secret(match) -> str:
            secret_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else None
            
            # Try to get the secret value
            secret_value = self.get_secret(secret_name)
            
            if secret_value is not None:
                return secret_value
            elif default_value is not None:
                logger.info(f"Using default value for secret '{secret_name}'")
                return default_value
            else:
                self._log_warning(f"Secret '{secret_name}' not found and no default provided")
                return match.group(0)  # Return original reference
        
        # Replace all secret references
        result = SECRET_PATTERN.sub(replace_secret, text)
        return result
    
    def process_dict_recursively(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively process secrets in a dictionary structure.
        
        Args:
            data: Dictionary to process
            
        Returns:
            Dictionary with secret references replaced
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.process_secrets(value)
            elif isinstance(value, dict):
                result[key] = self.process_dict_recursively(value)
            elif isinstance(value, list):
                result[key] = self._process_list_recursively(value)
            else:
                result[key] = value
        return result
    
    def _process_list_recursively(self, data: list) -> list:
        """Recursively process secrets in a list structure.
        
        Args:
            data: List to process
            
        Returns:
            List with secret references replaced
        """
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.process_secrets(item))
            elif isinstance(item, dict):
                result.append(self.process_dict_recursively(item))
            elif isinstance(item, list):
                result.append(self._process_list_recursively(item))
            else:
                result.append(item)
        return result


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> Optional[SecretsManager]:
    """Get the global secrets manager instance."""
    return _secrets_manager


def initialize_secrets_manager(keyvault_name: Optional[str], verbose: bool = False) -> Optional[SecretsManager]:
    """Initialize the global secrets manager.
    
    Args:
        keyvault_name: Name of the Azure Key Vault
        verbose: Whether to show secret warnings to console
        
    Returns:
        Initialized secrets manager or None if no vault specified
    """
    global _secrets_manager
    
    if keyvault_name:
        _secrets_manager = SecretsManager(keyvault_name, verbose=verbose)
        _secrets_manager.test_vault_access()
    else:
        _secrets_manager = None
        logger.debug("No Key Vault configured")
    
    return _secrets_manager


def process_secrets_in_text(text: str) -> str:
    """Process secret references in text using the global secrets manager.
    
    Args:
        text: Text to process
        
    Returns:
        Text with secrets replaced
    """
    if _secrets_manager:
        return _secrets_manager.process_secrets(text)
    return text


def process_secrets_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process secret references in a dictionary using the global secrets manager.
    
    Args:
        data: Dictionary to process
        
    Returns:
        Dictionary with secrets replaced
    """
    if _secrets_manager:
        return _secrets_manager.process_dict_recursively(data)
    return data