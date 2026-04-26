#!/usr/bin/env python3
"""
Debug version of OLLM that focuses on telemetry initialization.
This replicates the exact startup sequence to identify where telemetry fails.
"""

import sys
import asyncio
import traceback
from src.ollm.config import load_config
from src.ollm.secrets import SecretsManager
from src.ollm.telemetry import initialize_telemetry, get_telemetry_manager
from src.ollm.logging_setup import setup_logging, get_logger

def main():
    print("🔍 OLLM Telemetry Debug Tool")
    print("=" * 50)
    
    try:
        # Step 1: Load configuration (same as OLLM)
        print("1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Config loaded from: {config}")
        print(f"   Key Vault: {config.keyvault}")
        print(f"   Telemetry enabled: {config.telemetry.send_telemetry}")
        print(f"   New Relic timeout: {config.telemetry.new_relic_timeout}")
        print()
        
        # Step 2: Setup logging (same as OLLM)
        print("2. Setting up logging...")
        setup_logging(config.logging)
        logger = get_logger(__name__)
        print("   ✓ Logging initialized")
        print()
        
        # Step 3: Initialize secrets manager (same as OLLM app.py)
        print("3. Initializing secrets manager...")
        if config.keyvault:
            secrets_manager = SecretsManager(config.keyvault, verbose=True)
            print(f"   ✓ SecretsManager created")
            print(f"   Initial vault_accessible: {secrets_manager.vault_accessible}")
            
            # Test vault access (same as OLLM app.py)
            vault_test_result = secrets_manager.test_vault_access()
            print(f"   test_vault_access() result: {vault_test_result}")
            print(f"   Final vault_accessible: {secrets_manager.vault_accessible}")
        else:
            secrets_manager = None
            print("   No Key Vault configured")
        print()
        
        # Step 4: Initialize telemetry (same as OLLM app.py)
        print("4. Initializing telemetry...")
        initialize_telemetry(config, secrets_manager)
        tm = get_telemetry_manager()
        
        if tm:
            print(f"   ✓ Telemetry manager created")
            print(f"   Enabled: {tm.enabled}")
            print(f"   Secrets manager: {tm.secrets_manager is not None}")
            print(f"   API key initialized: {tm._api_key is not None}")
            print(f"   Account ID initialized: {tm._account_id is not None}")
        else:
            print("   ❌ No telemetry manager created")
        print()
        
        # Step 5: Test recording an event (this triggers _initialize)
        print("5. Testing telemetry event recording...")
        if tm and tm.enabled:
            async def test_telemetry():
                try:
                    print("   Recording test inference event...")
                    await tm.record_inference(
                        model='debug-model',
                        prompt_text='debug prompt',
                        response_text='debug response', 
                        ollama_data={'prompt_eval_count': 5, 'eval_count': 10},
                        start_time=0,
                        end_time=1
                    )
                    print("   ✓ Inference event recorded successfully")
                    
                    print("   Recording test tool call...")
                    await tm.record_tool_call(
                        tool_name='debug-tool',
                        success=True,
                        duration_ms=100
                    )
                    print("   ✓ Tool call event recorded successfully")
                    
                    print("   Recording test skill usage...")
                    await tm.record_skill_usage(
                        skill_name='debug-skill',
                        success=True,
                        duration_ms=200
                    )
                    print("   ✓ Skill usage event recorded successfully")
                    
                except Exception as e:
                    print(f"   ❌ Error recording events: {e}")
                    traceback.print_exc()
                    return False
                return True
                
            # Run the async telemetry test
            success = asyncio.run(test_telemetry())
            if success:
                print("   🎉 All telemetry events recorded successfully!")
                
                # Flush any pending telemetry data to ensure it gets sent
                print("6. Flushing pending telemetry data...")
                if tm:
                    async def flush_data():
                        await tm.flush_pending()
                        print("   ✓ All telemetry data flushed successfully")
                    asyncio.run(flush_data())
            else:
                print("   ❌ Telemetry event recording failed")
                sys.exit(1)
        else:
            print("   ⚠️  Telemetry not enabled, skipping event test")
        
        print()
        print("✅ OLLM telemetry initialization completed successfully!")
        
        # Step 6: Show final state
        print("\n📊 Final State Summary:")
        print(f"   Config loaded: ✓")
        print(f"   Secrets manager: {'✓' if secrets_manager else '❌'}")
        print(f"   Vault accessible: {'✓' if secrets_manager and secrets_manager.vault_accessible else '❌'}")
        print(f"   Telemetry manager: {'✓' if tm else '❌'}")
        print(f"   Telemetry enabled: {'✓' if tm and tm.enabled else '❌'}")
        print(f"   API key: {'✓' if tm and tm._api_key else '❌'}")
        print(f"   Account ID: {'✓' if tm and tm._account_id else '❌'}")
        
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()