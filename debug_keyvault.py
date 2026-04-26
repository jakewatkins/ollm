#!/usr/bin/env python3
"""
Debug script for Key Vault access issues.
This script immediately tests Key Vault access and shows detailed errors.
"""

import sys
import traceback
from src.ollm.config import load_config
from src.ollm.secrets import SecretsManager
from azure.keyvault.secrets import SecretClient
from azure.identity import AzureCliCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ResourceNotFoundError

def main():
    print("🔍 OLLM Key Vault Debug Tool")
    print("=" * 50)
    
    try:
        # Step 1: Load configuration
        print("1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Config loaded")
        print(f"   Key Vault: {config.keyvault}")
        print(f"   Telemetry enabled: {config.telemetry.send_telemetry}")
        print()
        
        # Step 2: Check if Key Vault is configured
        if not config.keyvault:
            print("❌ ERROR: No Key Vault configured in config.json")
            print("   Set 'keyvault' field to your Azure Key Vault name")
            sys.exit(1)
            
        # Step 3: Test Azure CLI authentication
        print("2. Testing Azure CLI authentication...")
        try:
            credential = AzureCliCredential()
            vault_url = f"https://{config.keyvault}.vault.azure.net/"
            print(f"   Vault URL: {vault_url}")
            
            # Test getting a token
            token = credential.get_token("https://vault.azure.net/.default")
            print(f"   ✓ Azure CLI authentication successful")
            print(f"   Token expires: {token.expires_on}")
            print()
        except Exception as e:
            print(f"   ❌ Azure CLI authentication failed: {e}")
            print("   Please run 'az login' and try again")
            sys.exit(1)
            
        # Step 4: Create Secret Client
        print("3. Creating Key Vault client...")
        try:
            client = SecretClient(vault_url=vault_url, credential=credential)
            print(f"   ✓ Secret client created")
            print()
        except Exception as e:
            print(f"   ❌ Failed to create Secret client: {e}")
            traceback.print_exc()
            sys.exit(1)
            
        # Step 5: Test vault connectivity
        print("4. Testing vault connectivity...")
        try:
            secrets = list(client.list_properties_of_secrets())
            print(f"   ✓ Successfully connected to vault")
            print(f"   Found {len(secrets)} secrets")
            print()
        except ClientAuthenticationError as e:
            print(f"   ❌ Authentication error: {e}")
            print("   Check your Azure permissions for this Key Vault")
            sys.exit(1)
        except HttpResponseError as e:
            print(f"   ❌ HTTP error: {e}")
            print("   Check if the Key Vault exists and you have access")
            sys.exit(1)
        except Exception as e:
            print(f"   ❌ Connectivity error: {e}")
            traceback.print_exc()
            sys.exit(1)
            
        # Step 6: Test specific secrets
        print("5. Testing New Relic secrets...")
        secrets_to_test = ["NewRelicAPIKey", "NewRelicAccountId"]
        
        for secret_name in secrets_to_test:
            try:
                print(f"   Testing {secret_name}...")
                secret = client.get_secret(secret_name)
                if secret.value:
                    print(f"   ✓ {secret_name}: Found (value: {secret.value[:8]}...)")
                else:
                    print(f"   ⚠️  {secret_name}: Found but empty")
            except ResourceNotFoundError:
                print(f"   ❌ {secret_name}: Not found in vault")
                print(f"      Please add this secret to your Key Vault: {config.keyvault}")
            except Exception as e:
                print(f"   ❌ {secret_name}: Error retrieving: {e}")
                traceback.print_exc()
                
        print()
        
        # Step 7: Test SecretsManager
        print("6. Testing OLLM SecretsManager...")
        try:
            sm = SecretsManager(config.keyvault, verbose=True)
            print(f"   ✓ SecretsManager created")
            print(f"   Initial vault_accessible: {sm.vault_accessible}")
            
            # Test vault access
            test_result = sm.test_vault_access()
            print(f"   test_vault_access() result: {test_result}")
            print(f"   Final vault_accessible: {sm.vault_accessible}")
            
            if test_result:
                # Test getting secrets through SecretsManager
                for secret_name in secrets_to_test:
                    value = sm.get_secret(secret_name)
                    if value:
                        print(f"   ✓ {secret_name}: Retrieved (value: {value[:8]}...)")
                    else:
                        print(f"   ❌ {secret_name}: Not retrieved")
            else:
                print("   ❌ Vault access test failed")
                
        except Exception as e:
            print(f"   ❌ SecretsManager error: {e}")
            traceback.print_exc()
            sys.exit(1)
            
        print()
        print("🎉 All tests passed! Key Vault access should work.")
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()