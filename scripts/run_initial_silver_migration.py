#!/usr/bin/env python3
"""
Initial Silver Migration (COMPLETED - for reference only)
This script was used to create the initial silver layer from historical bronze data.

⚠️  This has already been run successfully. Only run again if you need to rebuild 
the entire silver layer from scratch.

Result: Migrated 113,971 bronze records → 5,794 unique silver classes
"""

import os
from datetime import datetime, timezone, timedelta
import psycopg
from psycopg.rows import dict_row
from silver_aggregation import SilverAggregator
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration_by_date_range():
    """Run migration in date chunks to handle large dataset safely"""
    
    print("🚀 Starting Bronze → Silver migration in date chunks...")
    
    aggregator = SilverAggregator()
    
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        # Ensure schema exists
        aggregator.create_silver_schema(conn)
        
        # Get date range of data
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    MIN(scraped_at) as earliest,
                    MAX(scraped_at) as latest,
                    COUNT(*) as total_records
                FROM schedule_snapshots
            """)
            date_info = cur.fetchone()
            
        earliest, latest, total_records = date_info
        print(f"Data range: {earliest} → {latest}")
        print(f"Total records: {total_records:,}")
        
        # Process in 7-day chunks
        current_date = earliest
        chunk_size = timedelta(days=7)
        
        total_processed = 0
        total_inserted = 0
        total_updated = 0
        
        while current_date <= latest:
            end_date = min(current_date + chunk_size, latest + timedelta(days=1))
            
            print(f"\n📅 Processing chunk: {current_date.date()} → {end_date.date()}")
            
            # Get records for this date range
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT s.*, r.started_at as run_started_at, r.git_sha
                    FROM schedule_snapshots s
                    JOIN scrape_runs r ON s.run_id = r.run_id
                    WHERE s.scraped_at >= %s AND s.scraped_at < %s
                    ORDER BY s.source, s.scraped_at DESC
                """, (current_date, end_date))
                
                chunk_records = cur.fetchall()
            
            if not chunk_records:
                print(f"  No records in this chunk")
                current_date = end_date
                continue
                
            print(f"  Found {len(chunk_records):,} records")
            
            # Group by class_id and keep latest per class (like the original logic)
            class_groups = {}
            for record in chunk_records:
                class_id = aggregator.generate_class_id(record)
                
                # Keep the most recent record per class
                if class_id not in class_groups or record['scraped_at'] > class_groups[class_id]['scraped_at']:
                    class_groups[class_id] = record
            
            print(f"  Deduplicated to {len(class_groups):,} unique classes")
            
            # Process each class
            now = datetime.now(timezone.utc)
            chunk_inserted = 0
            chunk_updated = 0
            
            for class_id, latest_record in class_groups.items():
                # Enhance record with missing temporal/capacity data from raw JSON
                enhanced_record = aggregator.enhance_record_with_raw_data(latest_record)
                
                start_ts = enhanced_record['start_ts']
                is_past = start_ts < now if start_ts else False
                
                # Check if class already exists in silver
                existing = aggregator.get_existing_silver_record(conn, class_id)
                
                if existing:
                    # Only update if the new record is more recent
                    if enhanced_record['scraped_at'] > existing['last_scraped_at']:
                        if not existing['is_past']:  # Don't update past classes
                            aggregator.update_silver_record(conn, class_id, enhanced_record, is_past)
                            chunk_updated += 1
                else:
                    # New class - insert
                    aggregator.insert_silver_record(conn, class_id, enhanced_record, is_past)
                    chunk_inserted += 1
            
            total_processed += len(class_groups)
            total_inserted += chunk_inserted
            total_updated += chunk_updated
            
            print(f"  ✅ Chunk complete: {chunk_inserted} inserted, {chunk_updated} updated")
            
            current_date = end_date
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"📊 Final Statistics:")
        print(f"  • Total unique classes processed: {total_processed:,}")
        print(f"  • Classes inserted: {total_inserted:,}")
        print(f"  • Classes updated: {total_updated:,}")
        
        # Log the migration
        run_id = f"initial_migration_chunked_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        stats = {
            'processed': total_processed,
            'inserted': total_inserted,
            'updated': total_updated,
            'cancelled': 0
        }
        aggregator.log_aggregation_run(conn, run_id, 'all', stats, 'completed')

if __name__ == "__main__":
    run_migration_by_date_range()
