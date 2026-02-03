"""
Test script untuk Auto Key Recovery System
"""
from ai_generator import GeminiAIGenerator
from auto_key_generator import AutoKeyGenerator
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🧪 Testing Auto Key Recovery System")
print("=" * 60)

# Test 1: Check Auto Key Generator standalone
print("\n1️⃣ Testing AutoKeyGenerator standalone...")
try:
    gen = AutoKeyGenerator()
    if gen.is_available():
        print("   ✅ AutoKeyGenerator available")
        print(f"   📝 Using credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    else:
        print("   ❌ AutoKeyGenerator not available")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Check integration dengan GeminiAIGenerator
print("\n2️⃣ Testing GeminiAIGenerator with Auto Recovery...")
api_keys = os.getenv('GOOGLE_GEMINI_API_KEYS', '').split(',')
api_keys = [k.strip() for k in api_keys if k.strip()]

if not api_keys:
    print("   ⚠️  No API keys found in .env")
    api_keys = ["dummy_key_for_testing"]

try:
    ai_gen = GeminiAIGenerator(api_keys=api_keys)
    print(f"   ✅ GeminiAIGenerator initialized")
    print(f"   📊 Total API keys: {len(ai_gen.api_keys)}")
    print(f"   🤖 AI available: {ai_gen.is_available()}")
    
    if ai_gen.auto_key_generator:
        print(f"   🔄 Auto recovery: {'✓ Ready' if ai_gen.auto_key_generator.is_available() else '✗ Not available'}")
    else:
        print("   ⚠️  Auto Key Generator not initialized")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Manual recovery test (optional - commented out to avoid creating actual projects)
print("\n3️⃣ Manual Recovery Test (Dry Run)")
print("   ℹ️  To test manual recovery:")
print("   >>> from ai_generator import GeminiAIGenerator")
print("   >>> gen = GeminiAIGenerator(api_keys=['your_key'])")
print("   >>> gen.trigger_manual_recovery(num_keys=3)")

print("\n" + "=" * 60)
print("✅ Test completed!")
print("=" * 60)
