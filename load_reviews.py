# import pandas as pd
# from pathlib import Path
#
# CSV_PATH = Path("/Users/iwi.whyyy/Desktop/googleplay/output/merged_chatgpt_weekly.csv")
#
# def main():
#     df = pd.read_csv(CSV_PATH)
#     df = df.rename(columns={
#         "name": "user_name",
#         "content": "review_text",
#         "score": "rating",
#         "at": "review_date",
#         "appversion": "app_version"
#     })
#     df["app_id"] = 1
#
#     df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
#     df["year_month"] = df["review_date"].dt.to_period("M").astype(str)
#
#     df["text_length"] = df["review_text"].astype(str).str.split().str.len()
#
#     print(df.head())
#     print("Rows:", len(df))
#     print(df.columns.tolist())
# if __name__ == "__main__":
#     main()
#
# import sqlite3
#
# conn = sqlite3.connect("reviews.db")
#
# df.to_sql(
#     "reviews",
#     conn,
#     if_exists="append",
#     index=False
# )
#
# conn.close()
#
# print("Inserted rows into reviews table.")

import pandas as pd
import sqlite3
from pathlib import Path

CSV_PATH = Path("/Users/iwi.whyyy/Desktop/googleplay/output/merged_chatgpt_weekly.csv")

def main():
    df = pd.read_csv(CSV_PATH)

    df = df.rename(columns={
        "name": "user_name",
        "content": "review_text",
        "score": "rating",
        "at": "review_date",
        "appversion": "app_version"
    })

    df["app_id"] = 1
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df["year_month"] = df["review_date"].dt.to_period("M").astype(str)
    df["text_length"] = df["review_text"].astype(str).str.split().str.len()
    df = df.drop(columns=["source_file"])

    conn = sqlite3.connect("reviews.db")

    df.to_sql(
        "reviews",
        conn,
        if_exists="append",
        index=False
    )

    conn.close()
    print(f"Inserted {len(df)} rows into reviews table.")

if __name__ == "__main__":
    main()

