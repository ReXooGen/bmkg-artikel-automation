import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict
import os

logger = logging.getLogger(__name__)


class UserDatabase:
    """Database for tracking bot users and their activities"""
    
    def __init__(self, db_path: str = "bot_users.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        # Adaptation for Vercel
        if os.environ.get('VERCEL') == '1':
             self.db_path = os.path.join('/tmp', os.path.basename(db_path))
        else:
             self.db_path = db_path
             
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    total_commands INTEGER DEFAULT 0
                )
            """)
            
            # Create activity log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    name TEXT,
                    command TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON activity_log(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON activity_log(timestamp)
            """)
            
            # Create user sessions table for interactive state persistence
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    data TEXT,
                    updated_at TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    def log_user_activity(self, user_id: int, username: Optional[str], 
                         name: str, command: str):
        """
        Log user activity
        
        Args:
            user_id: Telegram user ID
            username: Telegram username (without @)
            name: User's full name
            command: Command executed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_time = datetime.now()
            
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                # Update existing user
                cursor.execute("""
                    UPDATE users 
                    SET username = ?, name = ?, last_seen = ?, 
                        total_commands = total_commands + 1
                    WHERE user_id = ?
                """, (username, name, current_time, user_id))
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (user_id, username, name, first_seen, last_seen, total_commands)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (user_id, username, name, current_time, current_time))
            
            # Log activity
            cursor.execute("""
                INSERT INTO activity_log (user_id, username, name, command, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, name, command, current_time))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging user activity: {str(e)}")
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting total users: {str(e)}")
            return 0
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, name, first_seen, last_seen, total_commands
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'first_seen': row[3],
                    'last_seen': row[4],
                    'total_commands': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, name, first_seen, last_seen, total_commands
                FROM users
                ORDER BY last_seen DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'first_seen': row[3],
                    'last_seen': row[4],
                    'total_commands': row[5]
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []
    
    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user activity history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, timestamp
                FROM activity_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            activities = []
            for row in rows:
                activities.append({
                    'command': row[0],
                    'timestamp': row[1]
                })
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return []
    
    def get_most_active_users(self, limit: int = 10) -> List[Dict]:
        """Get most active users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, name, total_commands, last_seen
                FROM users
                ORDER BY total_commands DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'total_commands': row[3],
                    'last_seen': row[4]
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting most active users: {str(e)}")
            return []
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict]:
        """Get recent activity across all users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, name, command, timestamp
                FROM activity_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            activities = []
            for row in rows:
                activities.append({
                    'user_id': row[0],
                    'username': row[1],
                    'name': row[2],
                    'command': row[3],
                    'timestamp': row[4]
                })
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")
            return []
    
    def get_command_stats(self) -> Dict[str, int]:
        """Get statistics for each command"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, COUNT(*) as count
                FROM activity_log
                GROUP BY command
                ORDER BY count DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            stats = {}
            for row in rows:
                stats[row[0]] = row[1]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting command stats: {str(e)}")
            return {}
    
    def export_to_csv(self, output_file: str = "users_export.csv"):
        """Export users data to CSV"""
        try:
            import csv
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, name, first_seen, last_seen, total_commands
                FROM users
                ORDER BY user_id
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['User ID', 'Username', 'Name', 'First Seen', 'Last Seen', 'Total Commands'])
                writer.writerows(rows)
            
            logger.info(f"Data exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return False

    def update_session(self, user_id: int, data: Dict) -> bool:
        """Update user session data"""
        try:
            import json
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_time = datetime.now()
            json_data = json.dumps(data)
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_sessions (user_id, data, updated_at)
                VALUES (?, ?, ?)
            """, (user_id, json_data, current_time))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            return False

    def get_session(self, user_id: int) -> Dict:
        """Get user session data"""
        try:
            import json
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM user_sessions WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            return {}
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return {}

    def clear_session(self, user_id: int) -> bool:
        """Clear user session data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return False



if __name__ == "__main__":
    # Test database
    db = UserDatabase()
    
    # Test logging
    db.log_user_activity(123456789, "testuser", "Test User", "start")
    
    # Get stats
    print(f"Total users: {db.get_total_users()}")
    print(f"\nCommand stats: {db.get_command_stats()}")
    
    # Get all users
    users = db.get_all_users()
    print(f"\nAll users:")
    for user in users:
        username_display = f"@{user['username']}" if user['username'] else "N/A"
        print(f"  - {user['name']} ({username_display}) - {user['total_commands']} commands")
