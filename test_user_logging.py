"""
Test to verify database logging works properly
"""

# Simulate bot environment
print("\n" + "="*70)
print("TESTING DATABASE LOGGING")
print("="*70 + "\n")

# Test 1: Import and initialize
print("Test 1: Import UserDatabase")
try:
    from database import UserDatabase
    print("✅ UserDatabase imported successfully")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    exit(1)

# Test 2: Initialize database
print("\nTest 2: Initialize UserDatabase")
try:
    user_db = UserDatabase()
    print(f"✅ UserDatabase initialized")
    print(f"   Database path: {user_db.db_path}")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit(1)

# Test 3: Log a test user (user 7695047849 - L F)
print("\nTest 3: Log user 7695047849 (L F)")
try:
    user_db.log_user_activity(7695047849, None, "L F", "cuacakota None")
    print("✅ User activity logged successfully")
except Exception as e:
    print(f"❌ Failed to log activity: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Verify user was saved
print("\nTest 4: Verify user in database")
try:
    import sqlite3
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, username, name, total_commands FROM users WHERE user_id = ?', (7695047849,))
    result = cursor.fetchone()
    
    if result:
        print(f"✅ User found in database:")
        print(f"   User ID: {result[0]}")
        print(f"   Username: @{result[1] if result[1] else 'N/A'}")
        print(f"   Name: {result[2]}")
        print(f"   Total Commands: {result[3]}")
    else:
        print("❌ User NOT found in database")
    
    # Check activity log
    cursor.execute('SELECT command, timestamp FROM activity_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1', (7695047849,))
    log = cursor.fetchone()
    
    if log:
        print(f"\n✅ Latest activity log:")
        print(f"   Command: {log[0]}")
        print(f"   Timestamp: {log[1]}")
    else:
        print("\n❌ No activity log found")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Failed to verify: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETED")
print("="*70 + "\n")
