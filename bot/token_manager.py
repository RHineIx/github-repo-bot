import asyncio  
import aiosqlite  
from typing import Optional, Dict  
from cryptography.fernet import Fernet  
import os  
import logging  
  
logger = logging.getLogger(__name__)  
  
class TokenManager:  
    """Manages user GitHub tokens with SQLite storage."""  
      
    def __init__(self, db_path: str = "user_tokens.db"):  
        self.db_path = db_path  
        self.encryption_key = self._get_or_create_key()  
        self.cipher = Fernet(self.encryption_key)  
        # Initialize database synchronously to avoid event loop issues  
        self._database_initialized = False  
      
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
      
    async def _ensure_database_initialized(self):  
        """Ensure database is initialized before operations."""  
        if not self._database_initialized:  
            await self._init_database()  
            self._database_initialized = True  
      
    async def _init_database(self):  
        """Initialize SQLite database asynchronously."""  
        try:  
            async with aiosqlite.connect(self.db_path) as conn:  
                await conn.execute('''  
                    CREATE TABLE IF NOT EXISTS user_tokens (  
                        user_id INTEGER PRIMARY KEY,  
                        encrypted_token TEXT NOT NULL,  
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
                    )  
                ''')  
                await conn.commit()  
                logger.info("Token database initialized successfully")  
        except Exception as e:  
            logger.error(f"Error initializing token database: {e}")  
            raise  
      
    async def store_token(self, user_id: int, token: str) -> bool:  
        """Store encrypted GitHub token for user."""  
        try:  
            await self._ensure_database_initialized()  
            encrypted_token = self.cipher.encrypt(token.encode()).decode()  
              
            async with aiosqlite.connect(self.db_path) as conn:  
                await conn.execute('''  
                    INSERT OR REPLACE INTO user_tokens (user_id, encrypted_token)  
                    VALUES (?, ?)  
                ''', (user_id, encrypted_token))  
                await conn.commit()  
              
            logger.info(f"Token stored successfully for user {user_id}")  
            return True  
        except Exception as e:  
            logger.error(f"Error storing token for user {user_id}: {e}")  
            return False  
      
    async def get_token(self, user_id: int) -> Optional[str]:  
        """Retrieve decrypted GitHub token for user."""  
        try:  
            await self._ensure_database_initialized()  
              
            async with aiosqlite.connect(self.db_path) as conn:  
                cursor = await conn.execute(  
                    'SELECT encrypted_token FROM user_tokens WHERE user_id = ?',  
                    (user_id,)  
                )  
                result = await cursor.fetchone()  
                  
                if result:  
                    encrypted_token = result[0]  
                    decrypted_token = self.cipher.decrypt(encrypted_token.encode()).decode()  
                    logger.debug(f"Token retrieved successfully for user {user_id}")  
                    return decrypted_token  
                  
                logger.debug(f"No token found for user {user_id}")  
                return None  
        except Exception as e:  
            logger.error(f"Error retrieving token for user {user_id}: {e}")  
            return None  
      
    async def remove_token(self, user_id: int) -> bool:  
        """Remove user's GitHub token."""  
        try:  
            await self._ensure_database_initialized()  
              
            async with aiosqlite.connect(self.db_path) as conn:  
                cursor = await conn.execute(  
                    'DELETE FROM user_tokens WHERE user_id = ?',   
                    (user_id,)  
                )  
                await conn.commit()  
                  
                if cursor.rowcount > 0:  
                    logger.info(f"Token removed successfully for user {user_id}")  
                    return True  
                else:  
                    logger.warning(f"No token found to remove for user {user_id}")  
                    return False  
        except Exception as e:  
            logger.error(f"Error removing token for user {user_id}: {e}")  
            return False  
      
    async def token_exists(self, user_id: int) -> bool:  
        """Check if user has a stored token."""  
        try:  
            await self._ensure_database_initialized()  
              
            async with aiosqlite.connect(self.db_path) as conn:  
                cursor = await conn.execute(  
                    'SELECT 1 FROM user_tokens WHERE user_id = ?',  
                    (user_id,)  
                )  
                result = await cursor.fetchone()  
                return result is not None  
        except Exception as e:  
            logger.error(f"Error checking token existence for user {user_id}: {e}")  
            return False  
      
    async def update_last_used(self, user_id: int) -> bool:  
        """Update last used timestamp for user's token."""  
        try:  
            await self._ensure_database_initialized()  
              
            async with aiosqlite.connect(self.db_path) as conn:  
                await conn.execute('''  
                    UPDATE user_tokens   
                    SET last_used = CURRENT_TIMESTAMP   
                    WHERE user_id = ?  
                ''', (user_id,))  
                await conn.commit()  
            return True  
        except Exception as e:  
            logger.error(f"Error updating last used for user {user_id}: {e}")  
            return False