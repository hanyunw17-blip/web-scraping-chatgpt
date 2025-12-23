import sqlite3

def main():
    conn = sqlite3.connect("reviews.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM reviews;")
    print("Total reviews:", cur.fetchone()[0])

    cur.execute("""
        SELECT year_month, AVG(rating), COUNT(*)
        FROM reviews
        GROUP BY year_month
        ORDER BY year_month
        LIMIT 5;
    """)
    for row in cur.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
 