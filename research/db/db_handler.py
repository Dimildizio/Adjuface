import aiosqlite


DATABASE_FILE = 'user_db.sqlite'


async def initialize_database():
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.cursor()

        await cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                mode INTEGER DEFAULT 1,
                text_data TEXT,
                input_path TEXT,
                output_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create a table to log user button clicks
        await cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                button_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')


async def get_current_mode(user_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.cursor()
        await cursor.execute(
            "SELECT mode FROM user_data WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
            (user_id,)
        )
        mode = await cursor.fetchone()
        return mode[0] if mode else 1


async def log_user_info(message, data_type, *args):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    mode = await get_current_mode(user_id)

    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.cursor()

        if data_type == 'text':
            text_data = message.text
            print('User said:', text_data)
            # Log text message data
            await cursor.execute(
                "INSERT INTO user_data (user_id, username, first_name, last_name, mode, text_data) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, first_name, last_name, mode, text_data)
            )
        elif data_type == 'image':
            input_path = args[0] if args else None
            output_paths = args[1] if args else None
            for output_path in output_paths:
                await cursor.execute(
                    "INSERT INTO user_data (user_id, username, first_name, last_name, mode, input_path, output_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, username, first_name, last_name, mode, input_path, output_path)
                )

        # Insert button click log into the user_logs table
        await cursor.execute(
            "INSERT INTO user_logs (user_id, username, first_name, last_name, button_text) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, first_name, last_name, data_type)
        )
        await db.commit()


async def fetch_user_data(user_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.cursor()
        await cursor.execute(
            "SELECT user_id, username, first_name, last_name, mode, text_data, input_path, output_path FROM user_data WHERE user_id = ?",
            (user_id,)
        )
        user_data = await cursor.fetchone()

        if user_data:
            user_id, username, first_name, last_name, mode, text_data, input_path, output_path = user_data
            print(f"User ID: {user_id}")
            print(f"Username: {username}")
            print(f"First Name: {first_name}")
            print(f"Last Name: {last_name}")
            print(f"Mode: {mode}")
            print(f"Text Data: {text_data}")

            if input_path and output_path:
                print(f"Input Path: {input_path}")
                print(f"Output Path: {output_path}")
        else:
            print("User not found in the database")
