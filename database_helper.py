# import sqlite3

from threading import Lock
from supabase import create_client, Client


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

    # @staticmethod
    # def fetch_one(query: str, params: dict = None):
    #     """
    #     Execute a read query and return a single result.
    #     :param query: SQL query string with placeholders.
    #     :param params: Dictionary of parameters to bind to the query.
    #     :return: The first result row or None if no results.
    #     """
    #     if not DatabaseHelper._client:
    #         raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
    #     with DatabaseHelper._lock:
    #         response = DatabaseHelper._client.rpc(query, params)
    #         return response[0] if response else None

    # @staticmethod
    # def fetch_all(query: str, params: dict = None):
    #     """
    #     Execute a read query and return all results.
    #     :param query: SQL query string with placeholders.
    #     :param params: Dictionary of parameters to bind to the query.
    #     :return: List of all result rows.
    #     """
    #     if not DatabaseHelper._client:
    #         raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
    #     with DatabaseHelper._lock:
    #         response = DatabaseHelper._client.rpc(query, params)
    #         return response

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


#
# import sqlite3
# from threading import Lock
#
# class DatabaseHelper:
#     _connection = None
#     _lock = Lock()
#
#     @staticmethod
#     def initialize(db_path=":memory:"):
#         """Initialize the database connection."""
#         with DatabaseHelper._lock:
#             if not DatabaseHelper._connection:
#                 DatabaseHelper._connection = sqlite3.connect(db_path, check_same_thread=False)
#                 DatabaseHelper._connection.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys if needed
#
#
#             cursor = DatabaseHelper._connection.cursor()
#
#             cursor.execute("""
#                             CREATE TABLE IF NOT EXISTS users (
#                                 user_id INTEGER NOT NULL PRIMARY KEY,
#                                 username TEXT NOT NULL
#                             )
#                         """)
#
#             # Create user_config table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS user_config (
#                     user_id INTEGER NOT NULL,
#                     config_key TEXT NOT NULL,
#                     config_value TEXT NOT NULL,
#                     PRIMARY KEY (user_id, config_key)
#                 )
#             """)
#
#             # Create user_stats table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS user_stats (
#                     user_id INTEGER NOT NULL PRIMARY KEY,
#                     successful_trades INTEGER DEFAULT 0,
#                     unsuccessful_trades INTEGER DEFAULT 0
#                 )
#             """)
#
#             # Create position_state table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS position_state (
#                     user_id INTEGER NOT NULL PRIMARY KEY,
#                     long_position_opened BOOLEAN DEFAULT FALSE,
#                     short_position_opened BOOLEAN DEFAULT FALSE,
#                     long_entry_price REAL DEFAULT 0,
#                     long_entry_size REAL DEFAULT 0,
#                     long_positions INTEGER DEFAULT 0,
#                     short_entry_price REAL DEFAULT 0,
#                     short_entry_size REAL DEFAULT 0,
#                     short_positions INTEGER DEFAULT 0,
#                     position_qty REAL DEFAULT 0.0
#                 )
#             """)
#
#             # Create user_balance table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS user_balance (
#                     user_id INTEGER NOT NULL PRIMARY KEY,
#                     current_capital REAL DEFAULT 0,
#                     allocated_capital REAL DEFAULT 0,
#                     cumulative_profit_loss REAL DEFAULT 0,
#                     total_commission REAL DEFAULT 0.0
#                 )
#             """)
#
#             # Commit changes
#             DatabaseHelper._connection.commit()
#
#     @staticmethod
#     def store(query, params=None):
#         """
#         Execute a write (INSERT/UPDATE/DELETE) query.
#         :param query: SQL query string with placeholders.
#         :param params: Tuple of parameters to bind to the query.
#         """
#         if not DatabaseHelper._connection:
#             raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
#         with DatabaseHelper._lock:
#             cursor = DatabaseHelper._connection.cursor()
#             cursor.execute(query, params or ())
#             DatabaseHelper._connection.commit()
#
#     @staticmethod
#     def fetch_one(query, params=None):
#         """
#         Execute a read query and return a single result.
#         :param query: SQL query string with placeholders.
#         :param params: Tuple of parameters to bind to the query.
#         :return: The first result row or None if no results.
#         """
#         if not DatabaseHelper._connection:
#             raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
#         with DatabaseHelper._lock:
#             cursor = DatabaseHelper._connection.cursor()
#             cursor.execute(query, params or ())
#             return cursor.fetchone()
#
#     @staticmethod
#     def fetch_all(query, params=None):
#         """
#         Execute a read query and return all results.
#         :param query: SQL query string with placeholders.
#         :param params: Tuple of parameters to bind to the query.
#         :return: List of all result rows.
#         """
#         if not DatabaseHelper._connection:
#             raise ValueError("DatabaseHelper is not initialized. Call `initialize()` first.")
#         with DatabaseHelper._lock:
#             cursor = DatabaseHelper._connection.cursor()
#             cursor.execute(query, params or ())
#             return cursor.fetchall()


# class DatabaseHelper:
#     def __init__(self, db_name=":memory:"):
#         self.connection = sqlite3.connect(db_name, check_same_thread=False)
#         self.create_tables()
#
#     def create_tables(self):
#         with self.connection:
#             self.connection.execute(
#                 """CREATE TABLE IF NOT EXISTS users (
#                     id INTEGER PRIMARY KEY,
#                     user_id INTEGER UNIQUE NOT NULL,
#                     username TEXT
#                 )"""
#             )
#             self.connection.execute(
#                 """CREATE TABLE IF NOT EXISTS configurations (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     user_id INTEGER NOT NULL,
#                     key TEXT NOT NULL,
#                     value TEXT NOT NULL,
#                     UNIQUE(user_id, key),
#                     FOREIGN KEY(user_id) REFERENCES users(user_id)
#                 )"""
#             )
#
#     def add_user(self, user_id, username):
#         with self.connection:
#             self.connection.execute(
#                 "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
#                 (user_id, username),
#             )
#
#     def set_configuration(self, user_id, key, value):
#         with self.connection:
#             self.connection.execute(
#                 """INSERT INTO configurations (user_id, key, value)
#                    VALUES (?, ?, ?)
#                    ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value""",
#                 (user_id, key, value),
#             )
#
#     def get_configurations(self):
#         with self.connection:
#             return self.connection.execute(
#                 "SELECT user_id, key, value FROM configurations"
#             ).fetchall()
#
#     def get_users(self):
#         with self.connection:
#             return self.connection.execute("SELECT user_id, username FROM users").fetchall()
#
#     def execute_query(self, query):
#         with self.connection:
#             return self.connection.execute(query).fetchall()
