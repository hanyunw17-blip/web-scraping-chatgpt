-- apps table
CREATE TABLE IF NOT EXISTS apps (
    app_id INTEGER PRIMARY KEY,
    app_name TEXT NOT NULL,
    platform TEXT NOT NULL
);

-- reviews table
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY,
    app_id INTEGER NOT NULL,
    user_name TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    review_date DATE,
    year_month TEXT,
    app_version TEXT,
    text_length INTEGER,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);
