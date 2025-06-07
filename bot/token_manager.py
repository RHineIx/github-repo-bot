import sqlite3  
import asyncio  
from typing import Optional, Dict  
from cryptography.fernet import Fernet  
import os  
  
class TokenManager:  
    """Manages user GitHub tokens with SQLite storage."""  
      
    def __init__(self, db_path: str = "user_tokens.db"):  
        self.db_path = db_path  
        self.encryption_key = self._get_or_create_key()  
        self.cipher = Fernet(self.encryption_key)  
        self._init_database()  
      
    def _get_or_create_key(self) -> bytes:  
        """Get or create encryption key for tokens."""  
        key_file = "token_encryption.key"  
        if os.path.exists(key_file):  
            with open(key_file, 'rb') as f:  
                return f.read()  
        else:  
            key = Fernet.generate_key()  
            with open(key_file, 'wb') as f:  
                f.write(key)  
            return key  
      
    def _init_database(self):  
        """Initialize SQLite database."""  
        conn = sqlite3.connect(self.db_path)  
        cursor = conn.cursor()  
        cursor.execute('''  
            CREATE TABLE IF NOT EXISTS user_tokens (  
                user_id INTEGER PRIMARY KEY,  
                encrypted_token TEXT NOT NULL,  
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
            )  
        ''')  
        conn.commit()  
        conn.close()  
      
    async def store_token(self, user_id: int, token: str) -> bool:  
        """Store encrypted GitHub token for user."""  
        try:  
            encrypted_token = self.cipher.encrypt(token.encode()).decode()  
              
            conn = sqlite3.connect(self.db_path)  
            cursor = conn.cursor()  
            cursor.execute('''  
                INSERT OR REPLACE INTO user_tokens (user_id, encrypted_token)  
                VALUES (?, ?)  
            ''', (user_id, encrypted_token))  
            conn.commit()  
            conn.close()  
            return True  
        except Exception as e:  
            print(f"Error storing token: {e}")  
            return False  
      
    async def get_token(self, user_id: int) -> Optional[str]:  
        """Retrieve decrypted GitHub token for user."""  
        try:  
            conn = sqlite3.connect(self.db_path)  
            cursor = conn.cursor()  
            cursor.execute(  
                'SELECT encrypted_token FROM user_tokens WHERE user_id = ?',  
                (user_id,)  
            )  
            result = cursor.fetchone()  
            conn.close()  
              
            if result:  
                encrypted_token = result[0]  
                return self.cipher.decrypt(encrypted_token.encode()).decode()  
            return None  
        except Exception as e:  
            print(f"Error retrieving token: {e}")  
            return None  
      
    async def remove_token(self, user_id: int) -> bool:  
        """Remove user's GitHub token."""  
        try:  
            conn = sqlite3.connect(self.db_path)  
            cursor = conn.cursor()  
            cursor.execute('DELETE FROM user_tokens WHERE user_id = ?', (user_id,))  
            conn.commit()  
            conn.close()  
            return True  
        except Exception as e:  
            print(f"Error removing token: {e}")  
            return False