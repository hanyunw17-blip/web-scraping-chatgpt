import sqlite3
from pathlib import Path

# Database file
DB_PATH = Path("reviews.db")

# SQL schema file
SCHEMA_PATH = Path("create_tables.sql")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

    print("Database and tables created successfully.")

if __name__ == "__main__":
    main()
