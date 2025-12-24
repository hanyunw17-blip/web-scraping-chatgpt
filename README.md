# Google Play Review Scraper - Chatgpt

This directory provides a local scraper based on gps. 
It supports interactive single-run scraping, configuration-driven historical backfill, and scheduled periodic jobs. 
Subdirectories are automatically created by mode/frequency for easier downstream management.
This project implements an automated pipeline to periodically fetch Google Play reviews, normalize them into a relational schema, and load them into a SQLite database for downstream analysis.

## Directory Structure
```
googleplay/
├── README.md                 # Project overview and usage
├── periodic.json             # Example configuration for scheduled scraping
├── default.json              # Default scraping configuration
│
├── scripts/                  # Scraping and execution scripts
│   ├── googleplay.py         # Interactive Google Play review scraper
│   ├── run_from_config.py    # Run scraping jobs from config files
│   ├── run_periodic.py       # Periodic (daily/weekly) scraping runner
│   └── logging_utils.py      # Shared logging utilities
│
├── output/                   # Auto-generated scraping outputs (CSV)
│   ├── single/               # One-off scraping results
│   ├── schedule/             # Scheduled scraping results
│   └── periodic/             # Periodic scraping results (daily / weekly)
│
├── vendor/gps/               # Local google-play-scraper dependency
│   ├── constants/
│   ├── features/
│   ├── utils/
│   ├── __init__.py
│   └── exceptions.py
│
├── create_tables.sql         # SQL schema definition (apps, reviews tables)
├── create_db.py              # Initialize SQLite database and schema
├── load_reviews.py           # Load and normalize CSV data into SQLite
├── analysis_queries.py       # Example analytical queries on the database
│
├── data_overview.ipynb       # Exploratory analysis notebook
├── merge_weekly_csv.ipynb    # Utility notebook for merging weekly CSVs
└── __init__.py

```

## Interactive Scraping
```bash
cd googleplay/scripts
python3 googleplay.py
```
After running, it will prompt you to enter a package name and the number of reviews needed.
The script will automatically create files such as ../output/<package>.csv.

## Config-Driven Batch Scraping
Suitable for servers or large-scale one-shot scraping.
Core scripts: scripts/run_from_config.py and scripts/run_periodic.py, both support custom output directories, logging, and pagination strategies.

### 1. Historical Interval Batch Scraping (scripts/run_from_config.py)
Specify apps to scrape using configuration files such as configs/default.json.
Key fields:
- lang / country: specify language and country code.
- output_dir: output directory (relative to googleplay/, default ./output).
- apps: list of applications:
 - package: app package name.
 - mode: single (scrape one batch of recent reviews) or schedule (scrape by time range defined by start/end).
 - count: number of reviews per request (default 1000, can be reduced to decrease load).
 - max_pages: max number of pages; can be left empty under schedule mode to allow auto-extension.
 - progress_interval: optional, prints progress after scraping N items.
 - auto_pages_start / auto_pages_multiplier / auto_pages_cap: auto-extension strategy when max_pages is not set (exponential growth).
 - auto_count_start / auto_count_multiplier / auto_count_cap: same, automatically increases count when scraping large batch requests.
 - frequency (schedule only): daily / weekly / monthly.
 - start_date / end_date (schedule only): define the scraping date interval.

Run Example：
```bash
cd googleplay/scripts
python3 run_from_config.py                         # default uses ../configs/default.json
python3 run_from_config.py ../configs/demo.json    # Specify config file
```
Output Structure：
- `mode=single`：`<output_dir>/single/<package>_single.csv`
- `mode=schedule`：`<output_dir>/schedule/<frequency>/<package>_<frequency>_<start>-<end>.csv`
An empty CSV will be generated and warnings will be recorded in logs if it contains no data.

### 2. Real-time periodic scraping（`scripts/run_periodic.py`）
Designed for cron/systemd to run with fixed frequency. Each run only scrapes the current window (current day/week/month).
It will not backfill history.
If backfilling is needed, use the schedule mode above.

Config example：`configs/periodic.json`
Field descriptions：
- `mode`: must be `periodic`.
- `frequency`: `daily` / `weekly` / `monthly`.
- `count` ：number of items to fetch per run.
- `max_pages` ：maximum pagination rounds.
- `ref_offset_days`：optional, used when “actual scraping should look back to previous day”.
  （e.g., -1 means scrape yesterday for each run.）
- `week_starts_on`：optional, define which weekday a week starts from (monday / sunday or number 0–6).
- `progress_interval`：optional, print progress periodically for long tasks.

Run example：
```bash
cd googleplay/scripts
python3 run_periodic.py                              
python3 run_periodic.py ../configs/my_periodic.json --date 2025-01-15
```
Generated output will be under <output_dir>/periodic/<frequency>/.

```
