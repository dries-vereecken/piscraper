#!/usr/bin/env python3
"""
Database utilities for storing scraper results in PostgreSQL.
"""

import os
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg
from psycopg import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def ensure_schema(conn: psycopg.Connection):
    """Create tables if they don't exist."""
    with conn.cursor() as cur:
        # Create scrape_runs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            run_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            git_sha TEXT
        );
        """)
        
        # Create schedule_snapshots table
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
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_source_start ON schedule_snapshots(source, start_ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_uid ON schedule_snapshots(source, item_uid, start_ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_snapshots_scraped ON schedule_snapshots(scraped_at);")

def insert_run(conn: psycopg.Connection, source: str, git_sha: Optional[str] = None) -> str:
    """Insert a new scrape run and return the run_id."""
    run_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (run_id, source, git_sha) VALUES (%s, %s, %s)",
            (run_id, source, git_sha),
        )
    return run_id

def coalesce(d: Dict[str, Any], *keys, default=None):
    """Return the first non-None, non-empty value from the dict for the given keys."""
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

def parse_availability(availability_str: str) -> tuple[Optional[int], Optional[int]]:
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

def parse_datetime_from_date_time(date_str: str, time_str: str) -> Optional[datetime]:
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

def parse_end_datetime_from_date_time(date_str: str, time_str: str) -> Optional[datetime]:
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

def as_rows(source: str, run_id: str, scraped_at: datetime, items: List[Dict[str, Any]]):
    """Convert items to database rows."""
    for item in items:
        # Parse availability
        availability_str = coalesce(item, "availability", "available", "spots_available", "free_spots")
        spots_available, capacity = parse_availability(availability_str) if availability_str else (None, None)
        
        # Parse datetime
        date_str = coalesce(item, "date", "start_date")
        time_str = coalesce(item, "time", "start_time", "hour")
        start_ts = parse_datetime_from_date_time(date_str, time_str) if date_str and time_str else None
        end_ts = parse_end_datetime_from_date_time(date_str, time_str) if date_str and time_str else None
        
        yield (
            run_id,
            source,
            coalesce(item, "id", "uid", "external_id", "slug"),
            coalesce(item, "class_name", "title", "name", "type"),
            coalesce(item, "instructor", "teacher"),
            coalesce(item, "location", "studio"),
            start_ts,
            end_ts,
            capacity,
            spots_available,
            coalesce(item, "status", "booking_status", "state"),
            coalesce(item, "url", "link"),
            scraped_at,
            json.dumps(item),
        )

def write_snapshots(source: str, items: List[Dict[str, Any]]):
    """Write schedule snapshots to the database."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set. Please set it in your .env file.")
    
    if not items:
        print(f"No items to write for source: {source}")
        return
    
    now = datetime.now(timezone.utc)
    git_sha = os.getenv("GITHUB_SHA")
    
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        ensure_schema(conn)
        run_id = insert_run(conn, source, git_sha)
        
        rows = list(as_rows(source, run_id, now, items))
        
        if rows:
            with conn.cursor() as cur:
                # Use executemany for psycopg 3
                cur.executemany("""
                    INSERT INTO schedule_snapshots
                    (run_id, source, item_uid, class_name, instructor, location, start_ts, end_ts,
                     capacity, spots_available, status, url, scraped_at, raw)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, rows)
            
            print(f"Successfully wrote {len(rows)} schedule snapshots for {source} (run_id: {run_id})")
        else:
            print(f"No valid rows generated for source: {source}")

def test_connection():
    """Test the database connection."""
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set. Please set it in your .env file.")
        return False
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result and result[0] == 1:
                    print("Database connection successful!")
                    return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
    return False

if __name__ == "__main__":
    # Test the connection when run directly
    test_connection()
