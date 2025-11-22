import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
LIB_DIR = ROOT_DIR / "vendor"
CONFIG_DIR = ROOT_DIR / "configs"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from gps import Sort, reviews  # noqa: E402
from logging_utils import get_logger  # noqa: E402

LOGGER = get_logger(__name__)


def load_config(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_subdir(base: Path, *parts: str) -> Path:
    target = base.joinpath(*parts)
    ensure_output_dir(target)
    return target


def fetch_reviews(
    app_id: str,
    lang: str,
    country: str,
    count: int,
    max_pages: int = 1,
    stop_at_date: Optional[date] = None,
    progress_interval: Optional[int] = None,
    progress_label: str = "",
) -> List[Dict]:
    data_list: List[Dict] = []
    continuation_token: Optional[str] = None
    pages = 0
    total = 0

    while True:
        kwargs = {
            "lang": lang,
            "country": country,
            "sort": Sort.NEWEST,
            "count": count,
        }
        if continuation_token:
            kwargs["continuation_token"] = continuation_token
        result, continuation_token = reviews(app_id, **kwargs)

        batch: List[Dict] = []
        for data in result:
            batch.append(
                {
                    "name": data.get("userName"),
                    "content": data.get("content"),
                    "score": data.get("score"),
                    "at": data.get("at"),
                    "appversion": data.get("appVersion"),
                }
            )
        data_list.extend(batch)
        pages += 1
        total += len(batch)

        if progress_interval and progress_interval > 0 and total // progress_interval != (total - len(batch)) // progress_interval:
            label = f"[{progress_label}] " if progress_label else ""
            LOGGER.info("%s has fetched %d reviews", label, total)

        if not continuation_token:
            break
        if pages >= max_pages:
            break
        if stop_at_date:
            oldest = _oldest_date(batch)
            if oldest and oldest <= stop_at_date:
                break

    return data_list


def _oldest_date(rows: List[Dict]) -> Optional[date]:
    oldest: Optional[date] = None
    for row in rows:
        comment_at = row.get("at")
        if not comment_at:
            continue
        comment_date = comment_at.date() if hasattr(comment_at, "date") else comment_at
        if isinstance(comment_date, datetime):
            comment_date = comment_date.date()
        if not isinstance(comment_date, date):
            continue
        if oldest is None or comment_date < oldest:
            oldest = comment_date
    return oldest


def filter_rows_by_period(
    rows: List[Dict],
    period_start: date,
    period_end: date,
) -> List[Dict]:
    filtered: List[Dict] = []
    for row in rows:
        comment_at = row.get("at")
        if not comment_at:
            continue
        comment_date = comment_at.date() if hasattr(comment_at, "date") else comment_at
        if period_start <= comment_date <= period_end:
            filtered.append(row)
    return filtered


def save_to_csv(rows: List[Dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerow(["empty"])
    if rows:
        LOGGER.info("created %s", output_path)
    else:
        LOGGER.warning("%s did not retrieve any review data; an empty file has been generated.", output_path)


def current_period(freq: str, ref: date, week_start: int = 0) -> Tuple[date, date]:
    if freq == "daily":
        return ref, ref
    if freq == "weekly":
        offset = (ref.weekday() - week_start) % 7
        start = ref - timedelta(days=offset)
        end = start + timedelta(days=6)
        return start, end
    if freq == "monthly":
        start = ref.replace(day=1)
        if start.month == 12:
            next_month = date(start.year + 1, 1, 1)
        else:
            next_month = date(start.year, start.month + 1, 1)
        end = next_month - timedelta(days=1)
        return start, end
    raise ValueError(f"unsupported frequency: {freq}")


def parse_week_start(value: Optional[str]) -> int:
    if value is None:
        return 0
    value_str = str(value).strip()
    if value_str.isdigit():
        num = int(value_str)
        if 0 <= num <= 6:
            return num
        return 0
    mapping = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    return mapping.get(value_str.lower(), 0)


def run_periodic_app(
    app_cfg: Dict,
    base_output: Path,
    lang: str,
    country: str,
    ref_date: date,
) -> None:
    frequency = app_cfg.get("frequency", "daily")
    ref_offset = int(app_cfg.get("ref_offset_days", 0))
    week_start = parse_week_start(app_cfg.get("week_starts_on"))
    ref_for_period = ref_date + timedelta(days=ref_offset)
    period_start, period_end = current_period(frequency, ref_for_period, week_start=week_start)
    count = int(app_cfg.get("count", 100))
    max_pages = int(app_cfg.get("max_pages", 10))
    progress_interval = int(app_cfg.get("progress_interval", 0))
    package = app_cfg["package"]
    rows = fetch_reviews(
        package,
        lang,
        country,
        count,
        max_pages=max_pages,
        stop_at_date=period_start,
        progress_interval=progress_interval,
        progress_label=f"{package}-{frequency}",
    )
    rows = filter_rows_by_period(rows, period_start, period_end)
    suffix = f"{period_start:%Y%m%d}-{period_end:%Y%m%d}"
    periodic_dir = ensure_subdir(base_output, "periodic", frequency)
    output_file = periodic_dir / f"{package}_{frequency}_{suffix}.csv"
    save_to_csv(rows, output_file)


def run(config_path: Optional[str], ref_date: date) -> None:
    cfg_file = Path(config_path) if config_path else CONFIG_DIR / "periodic.json"
    config = load_config(cfg_file)
    lang = config.get("lang", "en")
    country = config.get("country", "us")
    output_dir = ROOT_DIR / config.get("output_dir", "output")
    ensure_output_dir(output_dir)

    for app_cfg in config.get("apps", []):
        mode = app_cfg.get("mode", "periodic")
        if mode == "periodic":
            run_periodic_app(app_cfg, output_dir, lang, country, ref_date)
        elif mode == "single":
            count = int(app_cfg.get("count", 100))
            max_pages = int(app_cfg.get("max_pages", 1))
            progress_interval = int(app_cfg.get("progress_interval", 0))
            rows = fetch_reviews(
                app_cfg["package"],
                lang,
                country,
                count,
                max_pages=max_pages,
                progress_interval=progress_interval,
                progress_label=f"{app_cfg['package']}-single",
            )
            single_dir = ensure_subdir(output_dir, "single")
            output_file = single_dir / f"{app_cfg['package']}_single.csv"
            save_to_csv(rows, output_file)
        else:
            LOGGER.warning("Unknown mode %s; skipping %s.", mode, app_cfg.get("package"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Google Play reviews based on the current date range (intended for use with external scheduled tasks)")
    parser.add_argument(
        "config",
        nargs="?",
        help="Path to the configuration file (default: ../configs/periodic.json)",
    )
    parser.add_argument(
        "--date",
        help="Specify the reference date (YYYY-MM-DD). Defaults to today; useful for backfilling or testing.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ref = date.today()
    if args.date:
        ref = datetime.strptime(args.date, "%Y-%m-%d").date()
    run(args.config, ref)
