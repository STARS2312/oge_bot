import aiosqlite

DB_NAME = "history.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            total_tests INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER
        )
        """)

        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def save_result(user_id, score):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO results (user_id, score) VALUES (?, ?)",
            (user_id, score)
        )
        await db.execute("""
            UPDATE users
            SET total_tests = total_tests + 1,
                total_score = total_score + ?
            WHERE user_id = ?
        """, (score, user_id))
        await db.commit()

async def get_stats(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT total_tests, total_score
            FROM users
            WHERE user_id = ?
        """, (user_id,)) as cursor:
            return await cursor.fetchone()