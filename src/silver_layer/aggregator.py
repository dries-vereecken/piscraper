#!/usr/bin/env python3
"""
Silver Layer Aggregation: Bronze → Silver incremental processing
Transforms raw scraping data into clean, deduplicated class records.

Business Logic:
1. Past classes (start_ts < NOW): Immutable - keep final state
2. Future classes (start_ts > NOW): Always use latest scraped data  
3. New classes: Insert new silver records
4. Missing classes: Mark as cancelled (don't delete)
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

class SilverAggregator:
    """Handles Bronze → Silver data transformation and incremental updates"""
    
    def __init__(self):
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")
    
    def create_silver_schema(self, conn: psycopg.Connection):
        """Create silver layer tables if they don't exist"""
        with conn.cursor() as cur:
            # Silver classes table - one row per unique class
            cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_classes (
                class_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                class_name TEXT,
                instructor TEXT,
                location TEXT,
                start_ts TIMESTAMPTZ,
                end_ts TIMESTAMPTZ,
                capacity INTEGER,
                spots_available INTEGER,
                status TEXT,
                url TEXT,
                -- Metadata
                first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_scraped_at TIMESTAMPTZ NOT NULL,
                is_cancelled BOOLEAN DEFAULT FALSE,
                is_past BOOLEAN DEFAULT FALSE,
                -- Source tracking
                source_run_id TEXT,
                source_snapshot_id BIGINT,
                raw_data JSONB
            );
            """)
            
            # Indexes for performance
            cur.execute("CREATE INDEX IF NOT EXISTS ix_silver_source_start ON silver_classes(source, start_ts);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_silver_status ON silver_classes(is_cancelled, is_past);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_silver_updated ON silver_classes(last_updated_at);")
            
            # Silver aggregation log table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_aggregation_log (
                id BIGSERIAL PRIMARY KEY,
                run_id TEXT NOT NULL,
                source TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                records_processed INTEGER,
                records_inserted INTEGER,
                records_updated INTEGER,
                records_cancelled INTEGER,
                status TEXT DEFAULT 'running',
                error_message TEXT
            );
            """)
    
    def enhance_record_with_raw_data(self, record: Dict) -> Dict:
        """Enhance bronze record with missing temporal/capacity data from raw JSON"""
        enhanced = record.copy()
        
        try:
            raw_data = record.get('raw')
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            elif not isinstance(raw_data, dict):
                return enhanced
            
            source = record['source']
            
            # Extract temporal data based on source
            if source == 'coolcharm':
                # CoolCharm: Multiple date formats: "01/09/2025" or "SATURDAY 21 JUNE"
                if not enhanced.get('start_ts') and raw_data.get('date') and raw_data.get('time'):
                    try:
                        date_str = raw_data['date']
                        time_str = raw_data['time']
                        
                        # Parse date - handle multiple formats
                        date_obj = None
                        
                        # Try DD/MM/YYYY format first
                        try:
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                        except ValueError:
                            # Try "MONDAY DD MONTH" format
                            try:
                                # Extract day and month from "SATURDAY 21 JUNE"
                                import re
                                match = re.search(r'(\d{1,2})\s+(\w+)', date_str)
                                if match:
                                    day = int(match.group(1))
                                    month_name = match.group(2).upper()
                                    
                                    # Map month names to numbers
                                    months = {
                                        'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4,
                                        'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
                                        'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
                                    }
                                    
                                    if month_name in months:
                                        # Assume 2025 for future dates
                                        date_obj = datetime(2025, months[month_name], day)
                            except (ValueError, AttributeError):
                                pass
                        
                        if date_obj and ' - ' in time_str:
                            start_time_str, end_time_str = time_str.split(' - ')
                            start_hour, start_min = map(int, start_time_str.split(':'))
                            end_hour, end_min = map(int, end_time_str.split(':'))
                            
                            # Combine date and time
                            start_dt = date_obj.replace(hour=start_hour, minute=start_min, tzinfo=timezone.utc)
                            end_dt = date_obj.replace(hour=end_hour, minute=end_min, tzinfo=timezone.utc)
                            
                            enhanced['start_ts'] = start_dt
                            enhanced['end_ts'] = end_dt
                    except (ValueError, KeyError, TypeError):
                        pass
                        
                # Extract capacity from availability
                if not enhanced.get('capacity') and raw_data.get('availability'):
                    try:
                        avail = raw_data['availability']  # "4 / 5"
                        if ' / ' in avail:
                            spots, capacity = avail.split(' / ')
                            enhanced['capacity'] = int(capacity)
                            enhanced['spots_available'] = int(spots)
                    except (ValueError, TypeError):
                        pass
            
            elif source == 'rowreformer':
                # RowReformer: {"date": "18/05/2025", "details": ["REFORM", "9:00 AM" or "13:00", ...], ...}
                if not enhanced.get('start_ts') and raw_data.get('date'):
                    try:
                        date_str = raw_data['date']  # "18/05/2025"
                        details = raw_data.get('details', [])
                        
                        if len(details) > 1:
                            time_str = details[1]  # "9:00 AM" or "13:00"
                            
                            # Parse date (DD/MM/YYYY format)
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                            
                            # Parse time - handle both 12-hour and 24-hour formats
                            time_obj = None
                            
                            # Try 12-hour format first (H:MM AM/PM)
                            try:
                                time_obj = datetime.strptime(time_str, "%I:%M %p")
                            except ValueError:
                                # Try 24-hour format (HH:MM)
                                try:
                                    time_obj = datetime.strptime(time_str, "%H:%M")
                                except ValueError:
                                    pass
                            
                            if time_obj:
                                # Combine date and time (assume 50min classes)
                                start_dt = date_obj.replace(hour=time_obj.hour, minute=time_obj.minute, tzinfo=timezone.utc)
                                end_dt = start_dt + timedelta(minutes=50)
                                
                                enhanced['start_ts'] = start_dt
                                enhanced['end_ts'] = end_dt
                    except (ValueError, KeyError, IndexError):
                        pass
                        
                # Extract capacity from details
                if not enhanced.get('capacity'):
                    try:
                        details = raw_data.get('details', [])
                        if len(details) > 5:
                            avail = details[5]  # "8/10"
                            if '/' in avail:
                                spots, capacity = avail.split('/')
                                enhanced['capacity'] = int(capacity)
                                enhanced['spots_available'] = int(spots)
                    except (ValueError, TypeError, IndexError):
                        pass
            
            elif source == 'koepel':
                # Koepel: {"date": "zaterdag 17 mei", "time": "11:00 - 11:45", "capacity": "3 / 4", ...}
                
                # Extract temporal data from Dutch date format
                if not enhanced.get('start_ts') and raw_data.get('date') and raw_data.get('time'):
                    try:
                        date_str = raw_data['date']  # "zaterdag 12 juli"
                        time_str = raw_data['time']  # "11:00 - 11:45"
                        
                        # Extract day and month from Dutch date
                        import re
                        match = re.search(r'(\d{1,2})\s+(\w+)', date_str)
                        if match and ' - ' in time_str:
                            day = int(match.group(1))
                            month_name = match.group(2).lower()
                            
                            # Map Dutch month names to numbers
                            dutch_months = {
                                'januari': 1, 'februari': 2, 'maart': 3, 'april': 4,
                                'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
                                'september': 9, 'oktober': 10, 'november': 11, 'december': 12
                            }
                            
                            if month_name in dutch_months:
                                # Assume 2025 for future dates
                                date_obj = datetime(2025, dutch_months[month_name], day)
                                
                                # Parse time (HH:MM - HH:MM format)
                                start_time_str, end_time_str = time_str.split(' - ')
                                start_hour, start_min = map(int, start_time_str.split(':'))
                                end_hour, end_min = map(int, end_time_str.split(':'))
                                
                                # Combine date and time
                                start_dt = date_obj.replace(hour=start_hour, minute=start_min, tzinfo=timezone.utc)
                                end_dt = date_obj.replace(hour=end_hour, minute=end_min, tzinfo=timezone.utc)
                                
                                enhanced['start_ts'] = start_dt
                                enhanced['end_ts'] = end_dt
                    except (ValueError, KeyError, TypeError, AttributeError):
                        pass
                
                # Extract capacity from availability
                if not enhanced.get('capacity') and raw_data.get('capacity'):
                    try:
                        avail = raw_data['capacity']  # "3 / 4"
                        if ' / ' in avail:
                            spots, capacity = avail.split(' / ')
                            enhanced['capacity'] = int(capacity)
                            enhanced['spots_available'] = int(spots)
                    except (ValueError, TypeError):
                        pass
        
        except Exception:
            # If anything fails, return the original record
            pass
        
        return enhanced
    
    def generate_class_id(self, record: Dict[str, Any]) -> str:
        """Generate unique class ID based on source and class characteristics"""
        source = record['source']
        
        # Use different key combinations per source (matching your notebook logic)
        if source == 'coolcharm':
            keys = ['date', 'time', 'class_name', 'location']
        elif source == 'koepel':
            keys = ['date', 'time', 'instructor', 'description'] 
        elif source == 'rite':
            keys = ['name', 'date', 'hour', 'address', 'instructor']
        elif source == 'rowreformer':
            keys = ['week_day', 'details']  # Need to check the actual structure
        else:
            # Generic fallback
            keys = ['class_name', 'start_ts', 'location']
        
        # Extract values, handling missing keys gracefully
        raw_data = json.loads(record['raw']) if isinstance(record['raw'], str) else record['raw']
        
        key_values = []
        for key in keys:
            value = raw_data.get(key) or record.get(key) or 'unknown'
            key_values.append(str(value).lower().strip())
        
        # Create deterministic ID
        key_string = '|'.join(key_values)
        class_id = f"{source}:{hash(key_string) % (10**12):012d}"  # 12-digit hash
        
        return class_id
    
    def get_new_bronze_data(self, conn: psycopg.Connection, since_timestamp: Optional[datetime] = None) -> List[Dict]:
        """Get new bronze data since last aggregation"""
        with conn.cursor(row_factory=dict_row) as cur:
            if since_timestamp:
                cur.execute("""
                    SELECT s.*, r.started_at as run_started_at, r.git_sha
                    FROM schedule_snapshots s
                    JOIN scrape_runs r ON s.run_id = r.run_id
                    WHERE s.scraped_at > %s
                    ORDER BY s.source, s.scraped_at DESC
                """, (since_timestamp,))
            else:
                # First run - get last 24 hours of data
                since_timestamp = datetime.now(timezone.utc) - timedelta(hours=24)
                cur.execute("""
                    SELECT s.*, r.started_at as run_started_at, r.git_sha
                    FROM schedule_snapshots s
                    JOIN scrape_runs r ON s.run_id = r.run_id
                    WHERE s.scraped_at > %s
                    ORDER BY s.source, s.scraped_at DESC
                """, (since_timestamp,))
            
            return cur.fetchall()
    
    def get_latest_aggregation_timestamp(self, conn: psycopg.Connection) -> Optional[datetime]:
        """Get timestamp of last successful aggregation"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(completed_at)
                FROM silver_aggregation_log
                WHERE status = 'completed'
            """)
            result = cur.fetchone()
            return result[0] if result[0] else None
    
    def process_incremental_update(self, conn: psycopg.Connection) -> Dict[str, int]:
        """Main incremental processing logic"""
        
        stats = {
            'processed': 0,
            'inserted': 0, 
            'updated': 0,
            'cancelled': 0
        }
        
        # Get last aggregation time
        last_aggregation = self.get_latest_aggregation_timestamp(conn)
        
        # Get new bronze data
        new_records = self.get_new_bronze_data(conn, last_aggregation)
        
        if not new_records:
            print("No new bronze data to process")
            return stats
        
        print(f"Processing {len(new_records)} new bronze records...")
        
        # Group by class_id and keep latest per class
        class_groups = {}
        for record in new_records:
            class_id = self.generate_class_id(record)
            
            # Keep the most recent record per class
            if class_id not in class_groups or record['scraped_at'] > class_groups[class_id]['scraped_at']:
                class_groups[class_id] = record
        
        stats['processed'] = len(class_groups)
        
        # Current time for past/future logic
        now = datetime.now(timezone.utc)
        
        for class_id, latest_record in class_groups.items():
            # Enhance record with missing temporal/capacity data from raw JSON
            enhanced_record = self.enhance_record_with_raw_data(latest_record)
            
            start_ts = enhanced_record['start_ts']
            is_past = start_ts < now if start_ts else False
            
            # Check if class already exists in silver
            existing = self.get_existing_silver_record(conn, class_id)
            
            if existing:
                # Existing class - apply update logic
                if existing['is_past']:
                    # Past class - never update
                    print(f"Skipping past class: {class_id}")
                    continue
                else:
                    # Future class - update with latest data
                    self.update_silver_record(conn, class_id, enhanced_record, is_past)
                    stats['updated'] += 1
            else:
                # New class - insert
                self.insert_silver_record(conn, class_id, enhanced_record, is_past)
                stats['inserted'] += 1
        
        # Mark classes as cancelled if they're missing from recent scrapes
        cancelled_count = self.mark_cancelled_classes(conn, class_groups, now)
        stats['cancelled'] = cancelled_count
        
        return stats
    
    def get_existing_silver_record(self, conn: psycopg.Connection, class_id: str) -> Optional[Dict]:
        """Get existing silver record for a class"""
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM silver_classes WHERE class_id = %s", (class_id,))
            return cur.fetchone()
    
    def insert_silver_record(self, conn: psycopg.Connection, class_id: str, record: Dict, is_past: bool):
        """Insert new silver record"""
        # Convert raw data to JSON string if it's a dict
        raw_data = record['raw']
        if isinstance(raw_data, dict):
            raw_data = json.dumps(raw_data)
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO silver_classes (
                    class_id, source, class_name, instructor, location,
                    start_ts, end_ts, capacity, spots_available, status, url,
                    last_scraped_at, is_past, source_run_id, source_snapshot_id, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                class_id,
                record['source'],
                record['class_name'],
                record['instructor'], 
                record['location'],
                record['start_ts'],
                record['end_ts'],
                record['capacity'],
                record['spots_available'],
                record['status'],
                record['url'],
                record['scraped_at'],
                is_past,
                record['run_id'],
                record['id'],
                raw_data
            ))
    
    def update_silver_record(self, conn: psycopg.Connection, class_id: str, record: Dict, is_past: bool):
        """Update existing silver record"""
        # Convert raw data to JSON string if it's a dict
        raw_data = record['raw']
        if isinstance(raw_data, dict):
            raw_data = json.dumps(raw_data)
            
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE silver_classes SET
                    class_name = %s,
                    instructor = %s,
                    location = %s,
                    start_ts = %s,
                    end_ts = %s,
                    capacity = %s,
                    spots_available = %s,
                    status = %s,
                    url = %s,
                    last_updated_at = NOW(),
                    last_scraped_at = %s,
                    is_past = %s,
                    source_run_id = %s,
                    source_snapshot_id = %s,
                    raw_data = %s,
                    is_cancelled = FALSE
                WHERE class_id = %s
            """, (
                record['class_name'],
                record['instructor'],
                record['location'], 
                record['start_ts'],
                record['end_ts'],
                record['capacity'],
                record['spots_available'],
                record['status'],
                record['url'],
                record['scraped_at'],
                is_past,
                record['run_id'],
                record['id'],
                raw_data,
                class_id
            ))
    
    def mark_cancelled_classes(self, conn: psycopg.Connection, active_classes: Dict, now: datetime) -> int:
        """Mark classes as cancelled if they're missing from recent scrapes and still in future"""
        
        # Only mark as cancelled if:
        # 1. Class is in the future
        # 2. Class hasn't been seen in latest scrapes for its source
        # 3. Class isn't already marked as cancelled
        
        active_class_ids = set(active_classes.keys())
        
        with conn.cursor() as cur:
            # Get future classes that might need to be marked as cancelled
            cur.execute("""
                SELECT class_id, source
                FROM silver_classes 
                WHERE start_ts > %s 
                AND is_cancelled = FALSE
            """, (now,))
            
            future_classes = cur.fetchall()
        
        cancelled_count = 0
        
        # Group by source to check if we have recent data for each source
        sources_with_data = set(record['source'] for record in active_classes.values())
        
        for class_id, source in future_classes:
            # Only mark as cancelled if we have recent data for this source
            # but this specific class is missing
            if source in sources_with_data and class_id not in active_class_ids:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE silver_classes 
                        SET is_cancelled = TRUE, last_updated_at = NOW()
                        WHERE class_id = %s
                    """, (class_id,))
                cancelled_count += 1
        
        return cancelled_count
    
    def log_aggregation_run(self, conn: psycopg.Connection, run_id: str, source: str, stats: Dict[str, int], status: str = 'completed', error: str = None):
        """Log aggregation run results"""
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO silver_aggregation_log (
                    run_id, source, completed_at, records_processed, 
                    records_inserted, records_updated, records_cancelled, status, error_message
                ) VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s)
            """, (
                run_id, source, stats['processed'], stats['inserted'],
                stats['updated'], stats['cancelled'], status, error
            ))
    
    def run_aggregation(self, run_id: str = None) -> Dict[str, int]:
        """Main entry point for silver aggregation"""
        
        if not run_id:
            run_id = f"silver_agg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        print(f"Starting silver aggregation run: {run_id}")
        
        try:
            with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
                # Ensure schema exists
                self.create_silver_schema(conn)
                
                # Process incremental updates
                stats = self.process_incremental_update(conn)
                
                # Log success
                self.log_aggregation_run(conn, run_id, 'all', stats, 'completed')
                
                print(f"Aggregation completed: {stats}")
                return stats
                
        except Exception as e:
            print(f"Aggregation failed: {e}")
            try:
                with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
                    self.log_aggregation_run(conn, run_id, 'all', {}, 'failed', str(e))
            except:
                pass
            raise

def main():
    """Command line entry point"""
    aggregator = SilverAggregator()
    stats = aggregator.run_aggregation()
    
    print("\n=== Silver Aggregation Summary ===")
    print(f"Records processed: {stats['processed']}")
    print(f"Records inserted: {stats['inserted']}")  
    print(f"Records updated: {stats['updated']}")
    print(f"Records cancelled: {stats['cancelled']}")

if __name__ == "__main__":
    main()
