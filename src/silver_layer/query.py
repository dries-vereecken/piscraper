#!/usr/bin/env python3
"""
Silver Layer Query Utility
Provides helpful queries to explore and monitor the silver layer data.
"""

import os
from datetime import datetime, timezone, timedelta
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

class SilverQueryUtility:
    """Utility for querying and monitoring silver layer data"""
    
    def __init__(self):
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")
    
    def get_summary_stats(self):
        """Get high-level summary statistics"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            
            # Total classes by source
            cur.execute("""
                SELECT 
                    source,
                    COUNT(*) as total_classes,
                    COUNT(*) FILTER (WHERE is_cancelled) as cancelled_classes,
                    COUNT(*) FILTER (WHERE is_past) as past_classes,
                    COUNT(*) FILTER (WHERE start_ts > NOW()) as future_classes
                FROM silver_classes
                GROUP BY source
                ORDER BY source
            """)
            
            by_source = cur.fetchall()
            
            # Overall stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_classes,
                    COUNT(*) FILTER (WHERE is_cancelled) as cancelled_classes,
                    COUNT(*) FILTER (WHERE is_past) as past_classes,
                    COUNT(*) FILTER (WHERE start_ts > NOW()) as future_classes,
                    MIN(start_ts) as earliest_class,
                    MAX(start_ts) as latest_class
                FROM silver_classes
            """)
            
            overall = cur.fetchone()
            
            return {
                'overall': overall,
                'by_source': by_source
            }
    
    def get_recent_aggregations(self, limit=10):
        """Get recent aggregation run logs"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT *
                FROM silver_aggregation_log
                ORDER BY started_at DESC
                LIMIT %s
            """, (limit,))
            
            return cur.fetchall()
    
    def get_upcoming_classes(self, hours_ahead=24, limit=20):
        """Get upcoming classes in the next N hours"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            future_time = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
            
            cur.execute("""
                SELECT 
                    source,
                    class_name,
                    instructor,
                    location,
                    start_ts,
                    spots_available,
                    capacity,
                    status
                FROM silver_classes
                WHERE start_ts > NOW() 
                AND start_ts <= %s
                AND is_cancelled = FALSE
                ORDER BY start_ts
                LIMIT %s
            """, (future_time, limit))
            
            return cur.fetchall()
    
    def get_availability_summary(self):
        """Get availability summary for upcoming classes"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    source,
                    COUNT(*) as total_classes,
                    AVG(spots_available::float / NULLIF(capacity, 0) * 100) as avg_availability_pct,
                    COUNT(*) FILTER (WHERE spots_available = 0) as fully_booked,
                    COUNT(*) FILTER (WHERE spots_available::float / NULLIF(capacity, 0) > 0.8) as high_availability
                FROM silver_classes
                WHERE start_ts > NOW()
                AND is_cancelled = FALSE
                AND capacity > 0
                GROUP BY source
                ORDER BY source
            """)
            
            return cur.fetchall()
    
    def get_classes_by_location_time(self, location_filter=None):
        """Get class distribution by location and time"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            where_clause = "WHERE start_ts > NOW() AND is_cancelled = FALSE"
            params = []
            
            if location_filter:
                where_clause += " AND location ILIKE %s"
                params.append(f"%{location_filter}%")
            
            cur.execute(f"""
                SELECT 
                    location,
                    EXTRACT(dow FROM start_ts) as day_of_week,
                    EXTRACT(hour FROM start_ts) as hour_of_day,
                    COUNT(*) as class_count,
                    AVG(spots_available::float / NULLIF(capacity, 0) * 100) as avg_availability_pct
                FROM silver_classes
                {where_clause}
                GROUP BY location, day_of_week, hour_of_day
                ORDER BY location, day_of_week, hour_of_day
            """, params)
            
            return cur.fetchall()
    
    def search_classes(self, search_term, limit=50):
        """Search classes by name, instructor, or location"""
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    source,
                    class_name,
                    instructor,
                    location,
                    start_ts,
                    end_ts,
                    spots_available,
                    capacity,
                    status,
                    is_cancelled
                FROM silver_classes
                WHERE (
                    class_name ILIKE %s
                    OR instructor ILIKE %s
                    OR location ILIKE %s
                )
                AND start_ts > NOW() - INTERVAL '7 days'
                ORDER BY start_ts
                LIMIT %s
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", limit))
            
            return cur.fetchall()

def print_summary():
    """Print a comprehensive summary of the silver layer"""
    utility = SilverQueryUtility()
    
    print("=" * 60)
    print("🥈 SILVER LAYER SUMMARY")
    print("=" * 60)
    
    # Summary stats
    stats = utility.get_summary_stats()
    overall = stats['overall']
    
    print(f"\n📊 Overall Statistics:")
    print(f"  Total Classes: {overall['total_classes']:,}")
    print(f"  Past Classes: {overall['past_classes']:,}")
    print(f"  Future Classes: {overall['future_classes']:,}")
    print(f"  Cancelled Classes: {overall['cancelled_classes']:,}")
    print(f"  Date Range: {overall['earliest_class']} → {overall['latest_class']}")
    
    print(f"\n📈 By Source:")
    for source_stat in stats['by_source']:
        print(f"  {source_stat['source'].upper()}:")
        print(f"    Total: {source_stat['total_classes']:,}")
        print(f"    Future: {source_stat['future_classes']:,}")
        print(f"    Cancelled: {source_stat['cancelled_classes']:,}")
    
    # Availability summary
    print(f"\n🎯 Availability Summary (Upcoming Classes):")
    availability = utility.get_availability_summary()
    for avail in availability:
        print(f"  {avail['source'].upper()}:")
        print(f"    Total Classes: {avail['total_classes']:,}")
        print(f"    Avg Availability: {avail['avg_availability_pct']:.1f}%")
        print(f"    Fully Booked: {avail['fully_booked']:,}")
        print(f"    High Availability (>80%): {avail['high_availability']:,}")
    
    # Recent aggregations
    print(f"\n⚙️  Recent Aggregation Runs:")
    recent_runs = utility.get_recent_aggregations(5)
    for run in recent_runs:
        status_icon = "✅" if run['status'] == 'completed' else "❌"
        print(f"  {status_icon} {run['started_at']} - {run['run_id']}")
        if run['status'] == 'completed':
            print(f"    Processed: {run['records_processed']} | Inserted: {run['records_inserted']} | Updated: {run['records_updated']}")
    
    # Upcoming classes
    print(f"\n🔮 Next 10 Upcoming Classes:")
    upcoming = utility.get_upcoming_classes(hours_ahead=72, limit=10)
    for cls in upcoming:
        availability = f"{cls['spots_available']}/{cls['capacity']}" if cls['capacity'] else "Unknown"
        print(f"  {cls['start_ts']} | {cls['source'].upper()} | {cls['class_name']} | {availability}")

def interactive_search():
    """Interactive search interface"""
    utility = SilverQueryUtility()
    
    print("\n🔍 Interactive Class Search")
    print("Enter search terms to find classes by name, instructor, or location")
    print("Type 'quit' to exit")
    
    while True:
        search_term = input("\nSearch: ").strip()
        
        if search_term.lower() in ['quit', 'exit', 'q']:
            break
            
        if not search_term:
            continue
        
        results = utility.search_classes(search_term)
        
        if not results:
            print(f"No classes found matching '{search_term}'")
            continue
        
        print(f"\nFound {len(results)} classes matching '{search_term}':")
        print("-" * 80)
        
        for cls in results[:20]:  # Show first 20 results
            status = "❌ CANCELLED" if cls['is_cancelled'] else cls['status']
            availability = f"{cls['spots_available']}/{cls['capacity']}" if cls['capacity'] else "Unknown"
            
            print(f"{cls['start_ts']} | {cls['source'].upper()}")
            print(f"  {cls['class_name']} with {cls['instructor'] or 'Unknown instructor'}")
            print(f"  📍 {cls['location']} | 👥 {availability} | {status}")
            print()

def main():
    """Main CLI interface"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'summary':
            print_summary()
        elif command == 'search':
            interactive_search()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: summary, search")
    else:
        print_summary()

if __name__ == "__main__":
    main()
