import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
LIB_DIR = ROOT_DIR / "vendor"
CONFIG_DIR = ROOT_DIR / "configs"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from gps import Sort, reviews  # noqa: E402
from logging_utils import get_logger  # noqa: E402

LOGGER = get_logger("chatgpt_review_pipeline")


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
            LOGGER.info("%s Got %d comments", label, total)

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
        LOGGER.warning("%s No reviews found; an empty file was created", output_path)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_periods(freq: str, start: date, end: date) -> Iterable[Tuple[date, date]]:
    if start > end:
        return []

    periods: List[Tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        if freq == "daily":
            period_end = cursor
            next_cursor = cursor + timedelta(days=1)
        elif freq == "weekly":
            period_end = min(cursor + timedelta(days=6), end)
            next_cursor = cursor + timedelta(days=7)
        elif freq == "monthly":
            # the first day of next month
            if cursor.month == 12:
                next_month = date(cursor.year + 1, 1, 1)
            else:
                next_month = date(cursor.year, cursor.month + 1, 1)
            period_end = min(next_month - timedelta(days=1), end)
            next_cursor = next_month
        else:
            raise ValueError(f"unsupported frequency: {freq}")

        periods.append((cursor, period_end))
        cursor = next_cursor
    return periods


def run_single(app_cfg: Dict, base_output: Path, lang: str, country: str) -> None:
    count = int(app_cfg.get("count", 1000))
    max_pages = int(app_cfg.get("max_pages", 1))
    progress_interval = int(app_cfg.get("progress_interval", 0))
    package = app_cfg["package"]
    rows = fetch_reviews(
        package,
        lang,
        country,
        count,
        max_pages=max_pages,
        progress_interval=progress_interval,
        progress_label=f"{package}-single",
    )
    single_dir = ensure_subdir(base_output, "single")
    output_file = single_dir / f"{package}_single.csv"
    save_to_csv(rows, output_file)


def run_schedule(app_cfg: Dict, base_output: Path, lang: str, country: str) -> None:
    base_count = int(app_cfg.get("count", 1000))
    max_pages_cfg = app_cfg.get("max_pages")
    max_pages = int(max_pages_cfg) if max_pages_cfg is not None else None
    progress_interval = int(app_cfg.get("progress_interval", 0))
    auto_pages_start = max(1, int(app_cfg.get("auto_pages_start", 5)))
    auto_pages_multiplier = float(app_cfg.get("auto_pages_multiplier", 2.0))
    auto_pages_cap = int(app_cfg.get("auto_pages_cap", 200))
    auto_count_start = max(1, int(app_cfg.get("auto_count_start", base_count)))
    auto_count_multiplier = float(app_cfg.get("auto_count_multiplier", 2.0))
    auto_count_cap = int(app_cfg.get("auto_count_cap", max(base_count, base_count * 20)))
    package = app_cfg["package"]
    frequency = app_cfg.get("frequency", "daily")
    start_date = parse_date(app_cfg["start_date"])
    end_date = parse_date(app_cfg["end_date"])
    periods = list(iter_periods(frequency, start_date, end_date))
    if not periods:
        LOGGER.warning("No time window found; skipping %s", package)
        return

    earliest_start = periods[0][0]
    rows = collect_reviews_for_periods(
        package=package,
        lang=lang,
        country=country,
        count=base_count,
        stop_at=earliest_start,
        max_pages=max_pages,
        auto_start=auto_pages_start,
        auto_multiplier=auto_pages_multiplier,
        auto_cap=auto_pages_cap,
        auto_count_start=auto_count_start,
        auto_count_multiplier=auto_count_multiplier,
        auto_count_cap=auto_count_cap,
        progress_interval=progress_interval,
        progress_label=f"{package}-{earliest_start:%Y%m%d}-{periods[-1][1]:%Y%m%d}",
    )

    schedule_dir = ensure_subdir(base_output, "schedule", frequency)
    for period_start, period_end in periods:
        period_rows = filter_rows_by_period(rows, period_start, period_end)
        suffix = f"{period_start:%Y%m%d}-{period_end:%Y%m%d}"
        output_file = schedule_dir / f"{package}_{frequency}_{suffix}.csv"
        save_to_csv(period_rows, output_file)


def collect_reviews_for_periods(
    package: str,
    lang: str,
    country: str,
    count: int,
    stop_at: date,
    max_pages: Optional[int],
    auto_start: int,
    auto_multiplier: float,
    auto_cap: int,
    auto_count_start: int,
    auto_count_multiplier: float,
    auto_count_cap: int,
    progress_interval: int,
    progress_label: str,
) -> List[Dict]:

    if max_pages is not None:
        return fetch_reviews(
            package,
            lang,
            country,
            count,
            max_pages=max_pages,
            stop_at_date=stop_at,
            progress_interval=progress_interval,
            progress_label=progress_label,
        )

    pages = max(1, auto_start)
    multiplier = auto_multiplier if auto_multiplier > 1 else 2.0
    cap = max(pages, auto_cap)
    count_current = max(1, auto_count_start, count)
    count_mul = auto_count_multiplier if auto_count_multiplier > 1 else 2.0
    count_cap = max(count_current, auto_count_cap)

    rows: List[Dict] = []
    while True:
        LOGGER.info("Attempting to fetch up to %d pages, %d reviews per page, covering %s.", pages, count_current, stop_at)
        rows = fetch_reviews(
            package,
            lang,
            country,
            count_current,
            max_pages=pages,
            stop_at_date=stop_at,
            progress_interval=progress_interval,
            progress_label=f"{progress_label}-p{pages}",
        )
        oldest = _oldest_date(rows)
        if not oldest:
            LOGGER.warning("Attempting to fetch up to %d pages with %d reviews per page")
            return rows
        if oldest <= stop_at:
            return rows
        if count_current < count_cap:
            new_count = min(count_cap, int(max(count_current * count_mul, count_current + 1)))
            if new_count > count_current:
                LOGGER.info("Earliest review %s is later than target date %s; increasing per-request count to %d.", oldest, stop_at, new_count)
                count_current = new_count
                continue
        new_pages = min(cap, int(max(pages * multiplier, pages + 1)))
        if new_pages == pages:
            LOGGER.warning(
                "Even after auto-pagination up to the limit of %d pages, the target date %s was not reached (earliest review only goes back to %s)",
                pages,
                stop_at,
                oldest,
            )
            return rows
        pages = new_pages
        LOGGER.info("Earliest review %s is later than target date %s; expanding the number of pages to %d", oldest, stop_at, pages)


def run(config_path: Optional[str] = None) -> None:
    cfg_file = Path(config_path) if config_path else CONFIG_DIR / "default.json"
    config = load_config(cfg_file)
    lang = config.get("lang", "en")
    country = config.get("country", "us")
    output_dir = ROOT_DIR / config.get("output_dir", "output")
    ensure_output_dir(output_dir)

    for app_cfg in config.get("apps", []):
        mode = app_cfg.get("mode", "single")
        if mode == "single":
            run_single(app_cfg, output_dir, lang, country)
        elif mode == "schedule":
            run_schedule(app_cfg, output_dir, lang, country)
        else:
            LOGGER.warning("Unknown mode %s; skipping %s", mode, app_cfg.get("package"))


if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else None
    run(cfg_path)
