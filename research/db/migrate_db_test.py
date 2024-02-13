import sqlite3
from sqlalchemy import create_engine, inspect
from datetime import datetime, timedelta
import unittest


DATABASE_FILE = '../../src/user_database.db'
DATABASE_TEST_FILE = f'sqlite:///{DATABASE_FILE}'


def migrate_errors_database(db_file):
    # Create the ErrorLog table if it does not exist
    create_error_log_table = """
    CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        error_message TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """

    # Connect to the SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Execute the SQL statement
    cursor.execute(create_error_log_table)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    print("Database migrated successfully.")


def add_premium_expiration_column():
    """Func to add new column to the db"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('ALTER TABLE users ADD COLUMN premium_expiration DATE')
    thirty_days = datetime.now() + timedelta(days=30)
    cursor.execute('''
        UPDATE users
        SET premium_expiration = ?
        WHERE status = 'premium'
    ''', (thirty_days.date(),))

    conn.commit()
    conn.close()


class TestDatabaseMigration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Class-level setup to run database migrations before any tests."""
        # Migrate the database to include the error_logs table
        migrate_errors_database(DATABASE_FILE)
        # Add the premium_expiration column to users table if not exists
        add_premium_expiration_column()

    def setUp(self):
        """Set up the test environment by connecting to the test database."""
        self.engine = create_engine(DATABASE_TEST_FILE)
        self.conn = sqlite3.connect(DATABASE_FILE)
        self.cursor = self.conn.cursor()

        # Ensure the test environment is clean and set up
        self.add_sample_premium_users()

    def tearDown(self):
        """Clean up the test environment."""
        self.conn.close()

    def add_sample_premium_users(self):
        """Add sample premium users for testing."""
        try:
            self.cursor.execute('''
                INSERT INTO users (username, first_name, last_name, status, premium_expiration)
                VALUES ('testuser', 'Test', 'User', 'premium', ?)
            ''', (datetime.now() + timedelta(days=30),))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # User already exists or other constraint failed

    @staticmethod
    def check_column_exists(engine, table_name, column_name):
        """Check if a specific column exists in a given table."""
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

    def test_premium_expiration_column_exists(self):
        """Test if the premium_expiration column exists in the users table."""
        self.assertTrue(self.check_column_exists(self.engine, 'users', 'premium_expiration'))

    def test_error_log_table_exists(self):
        """Test if the error_logs table exists and has the correct structure."""
        for column in ['id', 'user_id', 'error_message', 'details', 'timestamp']:
            self.assertTrue(self.check_column_exists(self.engine, 'error_logs', column))

    def test_insert_and_retrieve_error_log(self):
        """Test inserting and retrieving an error log."""
        self.cursor.execute("""
            INSERT INTO error_logs (user_id, error_message, details)
            VALUES (?, ?, ?)
        """, (None, 'Test Error', 'Details of the test error'))
        self.conn.commit()

        self.cursor.execute("SELECT * FROM error_logs WHERE error_message = ?", ('Test Error',))
        error_log = self.cursor.fetchone()
        self.assertIsNotNone(error_log)
        self.assertEqual('Test Error', error_log[2])
        self.assertEqual('Details of the test error', error_log[3])


if __name__ == '__main__':
    # add_premium_expiration_column()
    unittest.main()
    # migrate_errors_database(DATABASE_FILE)
