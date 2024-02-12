import sqlite3
from sqlalchemy import create_engine, inspect
from datetime import datetime, timedelta
import unittest


DATABASE_FILE = 'user_database.db'
DATABASE_TEST_FILE = f'sqlite:///{DATABASE_FILE}'


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

    def setUp(self):
        """Set up the test environment."""
        self.engine = create_engine(DATABASE_TEST_FILE)
        self.conn = sqlite3.connect(DATABASE_FILE)
        self.cursor = self.conn.cursor()

        # Ensure the premium_expiration column and sample data are added for testing
        self.add_premium_expiration_column()
        self.add_sample_premium_users()

    def tearDown(self):
        """Clean up the test environment."""
        self.conn.close()

    def add_premium_expiration_column(self):
        """Add the premium_expiration column to the users table."""
        try:
            self.cursor.execute('ALTER TABLE users ADD COLUMN premium_expiration DATE')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    def add_sample_premium_users(self):
        """Add sample premium users for testing."""
        # This method should insert sample premium users with known expiration dates for testing
        pass  # Pass so far

    @staticmethod
    def check_column_exists(engine, table_name, column_name):
        """Check if a specific column exists in a given table."""
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

    def test_premium_expiration_column_exists(self):
        """Test if the premium_expiration column exists in the users table."""
        self.assertTrue(self.check_column_exists(self.engine, 'users', 'premium_expiration'))

    def test_premium_user_expirations(self):
        """Test the premium_expiration dates for premium users."""
        self.cursor.execute('''
            SELECT user_id, username, first_name, last_name, premium_expiration
            FROM users
            WHERE status = 'premium'
        ''')

        premium_users = self.cursor.fetchall()
        self.assertTrue(premium_users, "No premium users found.")

        for user in premium_users:
            user_id, username, first_name, last_name, premium_expiration = user
            if premium_expiration is not None:
                expiration_date = datetime.strptime(premium_expiration, "%Y-%m-%d").date()
                days_remaining = (expiration_date - datetime.now().date()).days
                self.assertTrue(days_remaining >= 0, f"Premium expiration for user {user_id} has passed.")
                print(f'\nPremium expiration for user {user_id} {first_name} {last_name} has passed '
                      f'with {premium_expiration}')
            else:
                self.fail(
                    f"User ID: {user_id}, Username: {username} {first_name} {last_name} does not have a premium "
                    f"expiration date set.")


if __name__ == '__main__':
    #  add_premium_expiration_column()
    unittest.main()
