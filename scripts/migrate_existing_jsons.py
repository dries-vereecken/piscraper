#!/usr/bin/env python3
"""
Migration script to load all existing JSON files into PostgreSQL database.
Run this once to migrate your historical data.

Usage:
    python migrate_existing_jsons.py

Make sure DATABASE_URL is set in your .env file.
"""

import os
import json
import uuid
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCRAPED_DIR = Path("scraped_data").resolve()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Please set it in your .env file.", file=sys.stderr)
    sys.exit(1)

# Regex to extract timestamp from filename like "coolcharm_schedule_20250626_100932.json"
TS_RE = re.compile(r".*_(\d{8})_(\d{6})\.json$")

def parse_ts_from_name(name: str) -> datetime | None:
    """Parse timestamp from filename."""
    m = TS_RE.match(name)
    if not m:
        return None
    d, t = m.group(1), m.group(2)
    # Treat timestamps as UTC
    return datetime.strptime(d + t, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

def coalesce(d: Dict[str, Any], *keys, default=None):
    """Return the first non-None, non-empty value from the dict."""
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

def parse_availability(availability_str: str) -> tuple[int | None, int | None]:
    """Parse availability string like '3 / 5' into (spots_available, capacity)."""
    if not availability_str or availability_str in ("Not specified", "Unknown"):
        return None, None
    
    try:
        # Handle formats like "3 / 5", "3/5", "3 of 5"
        availability_str = availability_str.replace(" of ", " / ")
        if "/" in availability_str:
            parts = availability_str.split("/")
            if len(parts) == 2:
                available = int(parts[0].strip())
                capacity = int(parts[1].strip())
                return available, capacity
    except (ValueError, IndexError):
        pass
    
    return None, None

def parse_datetime_from_date_time(date_str: str, time_str: str) -> datetime | None:
    """Parse date and time strings into a datetime object."""
    if not date_str or not time_str:
        return None
    
    try:
        # Handle date format like "26/06/2025"
        if "/" in date_str:
            day, month, year = date_str.split("/")
            date_part = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            date_part = date_str
        
        # Handle time format like "17:30 - 18:25" (take start time)
        if " - " in time_str:
            start_time = time_str.split(" - ")[0].strip()
        else:
            start_time = time_str.strip()
        
        # Combine date and time
        datetime_str = f"{date_part} {start_time}"
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None

def parse_end_datetime_from_date_time(date_str: str, time_str: str) -> datetime | None:
    """Parse date and time strings into an end datetime object."""
    if not date_str or not time_str:
        return None
    
    try:
        # Handle date format like "26/06/2025"
        if "/" in date_str:
            day, month, year = date_str.split("/")
            date_part = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            date_part = date_str
        
        # Handle time format like "17:30 - 18:25" (take end time)
        if " - " in time_str:
            end_time = time_str.split(" - ")[1].strip()
            # Combine date and time
            datetime_str = f"{date_part} {end_time}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        pass
    
    return None

def ensure_schema(conn: psycopg.Connection):
    """Create tables if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
          run_id TEXT PRIMARY KEY,
          source TEXT NOT NULL,
          started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          git_sha TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule_snapshots (
          id BIGSERIAL PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES scrape_runs(run_id) ON DELETE CASCADE,
          source TEXT NOT NULL,
          item_uid TEXT,
          class_name TEXT,
          instructor TEXT,
          location TEXT,
          start_ts TIMESTAMPTZ,
          end_ts TIMESTAMPTZ,
          capacity INTEGER,
          spots_available INTEGER,
          status TEXT,
          url TEXT,
          scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          raw JSONB NOT NULL
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_source_start ON schedule_snapshots(source, start_ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_uid ON schedule_snapshots(source, item_uid, start_ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_scraped ON schedule_snapshots(scraped_at);")

def insert_run(conn: psycopg.Connection, source: str, git_sha: str | None) -> str:
    """Insert a new scrape run and return the run_id."""
    run_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (run_id, source, git_sha) VALUES (%s,%s,%s)",
            (run_id, source, git_sha),
        )
    return run_id

# Import the fixed field mapping function from db_utils
from db_utils import as_rows

def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load JSON file and return list of items."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common containers
        for key in ("data", "items", "results", "classes"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Fallback: treat dict as one item
        return [data]
    return []

def main():
    """Main migration function."""
    git_sha = os.getenv("GITHUB_SHA") or "migration"
    files = sorted(SCRAPED_DIR.rglob("*.json"))
    
    if not files:
        print(f"No JSON files found under: {SCRAPED_DIR}")
        return

    print(f"Found {len(files)} JSON files to migrate...")
    
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn:
        ensure_schema(conn)
        total = 0
        
        for fp in files:
            name = fp.name
            # Extract source from filename (e.g., "coolcharm_schedule_..." -> "coolcharm")
            source = name.split("_", 1)[0].lower()
            
            # Map row -> rowreformer to match scraper source names
            if source == 'row':
                source = 'rowreformer'
            
            # Parse timestamp from filename or use file modification time
            scraped_at = parse_ts_from_name(name) or datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc)
            
            # Insert scrape run
            run_id = insert_run(conn, source, git_sha)
            
            # Load and process items
            items = load_json(fp)
            
            # Handle RowReformer's nested structure (flatten like the scraper does)
            if source == 'rowreformer':  # RowReformer files (mapped from 'row_')
                flattened_items = []
                if isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict):
                    # This is likely a single nested object, treat it as the whole data
                    data = items[0]
                elif isinstance(items, list):
                    # Multiple items, likely already processed
                    data = {f'week_{i}': {'classes': [item], 'date': item.get('date', '')} for i, item in enumerate(items)}
                else:
                    data = items if isinstance(items, dict) else {}
                
                for week_day, week_data in data.items():
                    if isinstance(week_data, dict) and 'classes' in week_data:
                        for class_item in week_data['classes']:
                            class_item['week_day'] = week_day
                            class_item['date'] = week_data.get('date', '')
                            flattened_items.append(class_item)
                items = flattened_items
            
            rows = list(as_rows(source, run_id, scraped_at, items))
            
            if not rows:
                print(f"{fp}: No valid items found, skipping")
                continue
            
            # Insert into database
            with conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO schedule_snapshots
                    (run_id, source, item_uid, class_name, instructor, location, start_ts, end_ts,
                     capacity, spots_available, status, url, scraped_at, raw)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, rows)
            
            total += len(rows)
            print(f"{fp}: inserted {len(rows)} rows as run {run_id}")
        
        print(f"Migration complete! Inserted {total} rows total across {len(files)} files.")

if __name__ == "__main__":
    main()
