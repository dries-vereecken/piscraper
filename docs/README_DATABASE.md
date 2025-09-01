# Database Migration Guide

This document explains how to migrate from JSON file storage to PostgreSQL database for the schedule scrapers.

## Overview

The system has been updated to:
- Store scrape results in PostgreSQL instead of JSON files
- Support both database and fallback JSON storage
- Include historical data migration
- Use GitHub Actions with database integration

## 1. Database Setup

### Option A: Neon (Recommended)
1. Go to [Neon](https://neon.tech/) and create a free account
2. Create a new project
3. Copy the connection string (looks like `postgresql://username:password@host/database?sslmode=require`)

### Option B: Supabase
1. Go to [Supabase](https://supabase.com/) and create a free account
2. Create a new project
3. Go to Settings → Database → Connection string
4. Copy the connection string

### Option C: ElephantSQL
1. Go to [ElephantSQL](https://www.elephantsql.com/) and create a free account
2. Create a new "Tiny Turtle" (free) instance
3. Copy the connection URL

## 2. Environment Setup

Create a `.env` file in the `Schedule scraper/` directory:

```bash
DATABASE_URL=postgresql://username:password@host/database?sslmode=require
```

## 3. Install Dependencies

```bash
cd "Schedule scraper"
pip install -r requirements.txt
```

## 4. Initialize Database Schema

The database schema will be automatically created when you first run any scraper or the migration script.

Alternatively, you can manually run the SQL schema:
```bash
# Connect to your database and run:
psql $DATABASE_URL -f init_schema.sql
```

## 5. Migrate Existing Data

Run the migration script to load all existing JSON files into the database:

```bash
cd "Schedule scraper"
python migrate_existing_jsons.py
```

This will:
- Create all necessary tables
- Load all JSON files from `scraped_data/` 
- Parse timestamps from filenames
- Store everything in PostgreSQL

## 6. Test the Setup

Test the database connection:
```bash
cd "Schedule scraper"
python db_utils.py
```

Run a scraper to test database writes:
```bash
python scraper_coolcharm.py
```

## 7. GitHub Actions Setup

1. In your GitHub repository, go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `DATABASE_URL`
4. Value: Your PostgreSQL connection string
5. Save

The GitHub Actions workflow (`.github/workflows/scrape.yml`) will now:
- Run scrapers every 30 minutes
- Write results directly to PostgreSQL
- Provide fallback error handling

## Database Schema

### Tables

**scrape_runs**: Tracks each scraping session
- `run_id`: Unique identifier for each run
- `source`: Scraper source (coolcharm, koepel, rite, rowreformer)
- `started_at`: When the scrape started
- `git_sha`: Git commit hash (useful in CI)

**schedule_snapshots**: Individual class/session data
- `id`: Auto-incrementing primary key
- `run_id`: References the scrape run
- `source`: Scraper source
- `item_uid`: Unique identifier for the class/session
- `class_name`: Name of the class
- `instructor`: Instructor name
- `location`: Location/studio
- `start_ts`: Class start time
- `end_ts`: Class end time
- `capacity`: Total capacity
- `spots_available`: Available spots
- `status`: Booking status
- `url`: Class URL
- `scraped_at`: When this record was scraped
- `raw`: Complete original JSON data

### Views

**latest_schedule**: Shows the most recent data for each unique class
**latest_runs**: Shows the most recent run for each source

## Usage Examples

### Query the latest schedule data
```sql
SELECT source, class_name, location, start_ts, spots_available 
FROM latest_schedule 
WHERE start_ts > NOW() 
ORDER BY start_ts;
```

### See scraping run history
```sql
SELECT source, started_at, COUNT(*) as classes_scraped
FROM scrape_runs r
JOIN schedule_snapshots s ON r.run_id = s.run_id
GROUP BY source, started_at
ORDER BY started_at DESC;
```

### Find availability changes over time
```sql
SELECT class_name, start_ts, spots_available, scraped_at
FROM schedule_snapshots
WHERE item_uid = 'some-class-id'
ORDER BY scraped_at DESC;
```

## Troubleshooting

### Database connection issues
- Verify your DATABASE_URL is correct
- Check firewall/security group settings
- Ensure SSL is configured properly

### Migration issues
- Check file permissions in `scraped_data/`
- Verify JSON files are valid
- Look for parsing errors in the console output

### GitHub Actions issues
- Verify DATABASE_URL secret is set correctly
- Check the Actions logs for specific error messages
- Ensure your database accepts connections from GitHub's IP ranges

## Fallback Behavior

If DATABASE_URL is not set or database connection fails:
- Scrapers will fall back to saving JSON files
- No data is lost
- You can retry database operations later

## Data Retention

For free database tiers with storage limits:
- Consider implementing data retention policies
- Archive old data periodically
- Monitor database usage

## Next Steps

1. Set up monitoring/alerting for failed scrapes
2. Consider implementing deduplication logic
3. Add data quality checks
4. Create dashboards for schedule analysis
