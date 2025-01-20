# import sqlite3
import os
from threading import Lock

from supabase import create_client, Client

class DatabaseConfig:
    store_to_db = True

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class DatabaseHelper:
    _client: Client = None
    _lock = Lock()

    @staticmethod
    def initialize(supabase_url: str, supabase_key: str):
        """Initialize the Supabase client."""
        with DatabaseHelper._lock:
            if not DatabaseHelper._client:
                DatabaseHelper._client = create_client(supabase_url, supabase_key)

                # Creating tables if not exist is handled by Supabase directly,
                # so we skip explicit CREATE TABLE statements.
                # You can manage schema through Supabase dashboard or migration scripts.

    @staticmethod
    def store(table: str, data: dict):
        if not DatabaseConfig.store_to_db:
            # log("DB is disabled, skipping update")
            return None

        """
        Insert or update a record in the specified table.
        :param table: Name of the table.
        :param data: Dictionary containing the data to insert or update.
        """
        if not DatabaseHelper._client:
            raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
        with DatabaseHelper._lock:
            response = DatabaseHelper._client.table(table).upsert(data).execute()
            if not response.data:
                raise RuntimeError(f"Error occurred during store operation: {response.error}")
            return response.data

    @staticmethod
    def get_table_data(table_name: str):
        """Fetch all data from a table."""
        if not DatabaseHelper._client:
            raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
        with DatabaseHelper._lock:
            data = DatabaseHelper._client.table(table_name).select('*').execute()
            return data.data if data.data else []

    @staticmethod
    def get_client():
        if not DatabaseHelper._client:
            raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
        with DatabaseHelper._lock:
            return DatabaseHelper._client

_db_helper_instance = None

def get_database_helper():
    global _db_helper_instance
    if _db_helper_instance is None:
        _db_helper_instance = DatabaseHelper()
        _db_helper_instance.initialize(DatabaseConfig.SUPABASE_URL, DatabaseConfig.SUPABASE_KEY)

    return _db_helper_instance
