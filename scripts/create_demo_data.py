#!/usr/bin/env python3
"""
Create demo data for dashboard testing.
Only use this if you don't have real data in your silver layer.
"""

import psycopg
from datetime import datetime, timezone, timedelta
import json
import random
from dotenv import load_dotenv
import os

load_dotenv()

def create_demo_data():
    """Create demo data in the silver_classes table."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set in .env file")
        return
    
    # Demo data configuration
    sources = ['coolcharm', 'koepel', 'rite', 'rowreformer']
    class_types = {
        'coolcharm': ['Reformer (All Levels)', 'Master Class Reformer', 'Reformer Mixed Level'],
        'koepel': ['Group Class', 'Private Session'],
        'rite': ['REFORM - GHENT NORTH', 'REFORM - GHENT SOUTH'],
        'rowreformer': ['REFORM', 'MAT pilates']
    }
    locations = {
        'coolcharm': ['Antwerp', 'Genk', 'Brussels'],
        'koepel': ['Unknown Location'],
        'rite': ['REFORM', 'Zuidstationstraat 18'],
        'rowreformer': ['Reformer studio', 'Mat studio']
    }
    instructors = ['Sophie', 'Kim', 'Laura V.', 'Nienke D.B.', 'Gilltumn Vanhauwaert', 'Viktoria']
    
    # Generate demo classes for the last 30 days and next 30 days
    start_date = datetime.now(timezone.utc) - timedelta(days=30)
    end_date = datetime.now(timezone.utc) + timedelta(days=30)
    
    demo_records = []
    class_id_counter = 1
    
    current_date = start_date
    while current_date <= end_date:
        # Skip some days randomly to make data more realistic
        if random.random() < 0.1:  # 10% chance to skip a day
            current_date += timedelta(days=1)
            continue
        
        # Generate 5-15 classes per day
        classes_per_day = random.randint(5, 15)
        
        for _ in range(classes_per_day):
            source = random.choice(sources)
            class_name = random.choice(class_types[source])
            location = random.choice(locations[source])
            instructor = random.choice(instructors) if random.random() > 0.2 else None
            
            # Random hour between 7 AM and 9 PM
            hour = random.randint(7, 21)
            start_ts = current_date.replace(hour=hour, minute=random.choice([0, 15, 30, 45]))
            end_ts = start_ts + timedelta(minutes=random.choice([45, 50, 60]))
            
            # Capacity and booking
            capacity = random.randint(4, 20)
            spots_booked = random.randint(0, capacity)  # This will go into spots_available column
            spots_remaining = capacity - spots_booked
            
            # Status
            if spots_booked == capacity:
                status = 'Fully Booked'
            elif spots_remaining <= 2:
                status = 'Almost Full'
            else:
                status = 'Book'
            
            # Create class ID
            class_id = f"{source}:{class_id_counter:012d}"
            class_id_counter += 1
            
            # Raw data
            raw_data = {
                'date': start_ts.strftime('%d/%m/%Y'),
                'time': f"{start_ts.strftime('%H:%M')} - {end_ts.strftime('%H:%M')}",
                'class_name': class_name,
                'location': location,
                'instructor': instructor,
                'availability': f"{spots_remaining} / {capacity}",  # remaining / total
                'status': status
            }
            
            demo_records.append((
                class_id, source, class_name, instructor, location,
                start_ts, end_ts, capacity, spots_booked, status, None,  # spots_booked goes to spots_available column
                start_ts, start_ts, start_ts,
                False, start_ts < datetime.now(timezone.utc),
                f"demo_run_{source}", 1, json.dumps(raw_data)
            ))
        
        current_date += timedelta(days=1)
    
    # Insert demo data
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            # Create silver_classes table if it doesn't exist
            with conn.cursor() as cur:
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
                    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_scraped_at TIMESTAMPTZ NOT NULL,
                    is_cancelled BOOLEAN DEFAULT FALSE,
                    is_past BOOLEAN DEFAULT FALSE,
                    source_run_id TEXT,
                    source_snapshot_id BIGINT,
                    raw_data JSONB
                );
                """)
            
            # Clear existing demo data
            with conn.cursor() as cur:
                cur.execute("DELETE FROM silver_classes WHERE source_run_id LIKE 'demo_run_%'")
                deleted_count = cur.rowcount
                if deleted_count > 0:
                    print(f"Deleted {deleted_count} existing demo records")
            
            # Insert new demo data
            with conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO silver_classes (
                        class_id, source, class_name, instructor, location,
                        start_ts, end_ts, capacity, spots_available, status, url,
                        first_seen_at, last_updated_at, last_scraped_at,
                        is_cancelled, is_past, source_run_id, source_snapshot_id, raw_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, demo_records)
            
            print(f"✅ Created {len(demo_records)} demo class records")
            print(f"   Date range: {start_date.date()} to {end_date.date()}")
            print(f"   Sources: {', '.join(sources)}")
            print("\n🚀 Demo data ready! You can now run the dashboard:")
            print("   python run_dashboard.py")
            
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")

def clean_demo_data():
    """Remove all demo data."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set in .env file")
        return
    
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM silver_classes WHERE source_run_id LIKE 'demo_run_%'")
                deleted_count = cur.rowcount
                print(f"✅ Deleted {deleted_count} demo records")
    except Exception as e:
        print(f"❌ Error cleaning demo data: {e}")

def main():
    """Main function with command-line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        print("🧹 Cleaning demo data...")
        clean_demo_data()
    else:
        print("🎭 Creating demo data for dashboard testing...")
        print("⚠️  This will replace any existing demo data")
        
        response = input("Continue? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            create_demo_data()
        else:
            print("Cancelled.")

if __name__ == "__main__":
    main()
