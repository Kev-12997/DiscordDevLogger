import os
from supabase import create_client, Client
from typing import Optional, Dict, Any

class Database:
    def __init__(self):
        '''
        Initialize Supabase client
        '''
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError('SUPABASE_URL and SUPABASE_KEY environment variables must be set')
        
        self.supabase: Client = create_client(url, key)
    
    async def add_user(self, discord_user_id: int) -> Dict[str, Any]:
        '''
        Add a new user to the database and return their API key.
        
        Args:
            discord_user_id: The Discord user's ID
            
        Returns:
            Dict containing user data including the generated API key
            
        Raises:
            Exception: If user already exists or database error occurs
        '''
        try:
            # Insert new user (api_key will be auto-generated)
            response = self.supabase.table('users').insert({
                'discord_user_id': discord_user_id
            }).execute()
            
            if response.data:
                return response.data[0]
            else:
                raise Exception('Failed to create user')
                
        except Exception as e:
            # Check if it's a unique constraint violation (user already exists)
            if 'duplicate key value violates unique constraint' in str(e):
                raise Exception('User is already subscribed!')
            else:
                raise Exception(f'Database error: {str(e)}')
    
    async def get_user_by_discord_id(self, discord_user_id: int) -> Optional[Dict[str, Any]]:
        '''
        Get user data by Discord ID.
        
        Args:
            discord_user_id: The Discord user's ID
            
        Returns:
            User data dict or None if not found
        '''
        try:
            response = self.supabase.table('users').select('*').eq('discord_user_id', discord_user_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f'Database error getting user: {e}')
            return None
    
    async def deactivate_user(self, discord_user_id: int) -> bool:
        '''
        Deactivate a user (set is_active to false).
        
        Args:
            discord_user_id: The Discord user's ID
            
        Returns:
            True if successful, False otherwise
        '''
        try:
            response = self.supabase.table('users').update({
                'is_active': False
            }).eq('discord_user_id', discord_user_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f'Database error deactivating user: {e}')
            return False
        
    async def activate_user(self, discord_user_id: int) -> bool:
        '''
        Activate a user (set is_active to true).
        
        Args:
            discord_user_id: The Discord user's ID
            
        Returns:
            True if successful, False otherwise
        '''
        try:
            response = self.supabase.table('users').update({
                'is_active': True
            }).eq('discord_user_id', discord_user_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f'Database error deactivating user: {e}')
            return False

    async def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        '''
        Get user data by API key.
        
        Args:
            api_key: The user's API key
            
        Returns:
            User data dict or None if not found
        '''
        try:
            response = self.supabase.table('users').select('*').eq('api_key', api_key).eq('is_active', True).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f'Database error getting user by API key: {e}')
            return None