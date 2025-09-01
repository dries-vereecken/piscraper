"""
Database Models

Dataclasses representing database entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ScrapeRun:
    """Represents a scraping run."""
    run_id: str
    source: str
    started_at: datetime
    git_sha: Optional[str] = None


@dataclass
class ScheduleSnapshot:
    """Represents a snapshot of a class/session."""
    id: Optional[int]
    run_id: str
    source: str
    item_uid: Optional[str]
    class_name: Optional[str]
    instructor: Optional[str]
    location: Optional[str]
    start_ts: Optional[datetime]
    end_ts: Optional[datetime]
    capacity: Optional[int]
    spots_available: Optional[int]
    status: Optional[str]
    url: Optional[str]
    scraped_at: datetime
    raw: Dict[str, Any]
