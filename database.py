import aiosqlite

DB_PATH = "db.sqlite"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish TEXT,
                score INTEGER,
                text TEXT
            )
        """)
        await db.commit()

async def save_review(dish, score, text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO reviews (dish, score, text) VALUES (?, ?, ?)", (dish, score, text))
        await db.commit()

async def get_reviews(dish):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT score, text FROM reviews WHERE dish = ?", (dish,))
        return await cursor.fetchall()
