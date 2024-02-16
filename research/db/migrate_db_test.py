import sqlite3
# from sqlalchemy import create_engine, inspect
from datetime import datetime, timedelta
# import unittest


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


def add_premium_class():
    """Migrates the database to include a PremiumPurchases table and initializes it based on existing premium users."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create the PremiumPurchases table for tracking multiple purchases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PremiumPurchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            purchase_date DATE NOT NULL,
            expiration_date DATE NOT NULL,
            targets_increment INTEGER DEFAULT 10,
            requests_increment INTEGER DEFAULT 100,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    # Fetch existing premium users along with their premium_expiration
    cursor.execute('''
        SELECT user_id, premium_expiration FROM users WHERE status = 'premium' AND premium_expiration IS NOT NULL
    ''')
    premium_users = cursor.fetchall()

    for user_id, premium_expiration in premium_users:
        # Use the existing premium_expiration date for the expiration_date in PremiumPurchases
        # Assuming the purchase_date is 30 days before the expiration_date
        expiration_date = datetime.strptime(premium_expiration, "%Y-%m-%d").date()
        purchase_date = expiration_date - timedelta(days=30)

        cursor.execute('''
          INSERT INTO PremiumPurchases (user_id, purchase_date, expiration_date, targets_increment, requests_increment)
          VALUES (?, ?, ?, 10, 100)
        ''', (user_id, purchase_date, expiration_date))

    conn.commit()
    conn.close()
    print("Database migration to include PremiumPurchases table completed.")


def add_timestamp_column_to_image_names():
    """Function to add a timestamp column to the ImageName table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('ALTER TABLE image_names ADD COLUMN timestamp TIMESTAMP')
    current_timestamp = datetime.now()
    cursor.execute('''
        UPDATE image_names
        SET timestamp = ?
    ''', (current_timestamp,))
    conn.commit()
    conn.close()


def show_all_image_names():
    """Fetch and print all ImageName instances using SQLite."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM image_names')
    image_names = cursor.fetchall()

    for image_name in image_names:
        print(f"ID: {image_name[0]}, User ID: {image_name[1]}, "
              f"Input Image Name: '{image_name[2]}', "
              f"Output Image Names: '{image_name[3]}', "
              f"Timestamp: {image_name[4]}")
    conn.close()


if __name__ == '__main__':
    print()
    # add_timestamp_column_to_image_names()
    # add_premium_class()
    # show_all_image_names()
    # add_premium_expiration_column()
    # unittest.main()
    # migrate_errors_database(DATABASE_FILE)
