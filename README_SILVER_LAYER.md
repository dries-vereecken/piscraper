# 🥈 Silver Layer Architecture

The Silver Layer provides clean, deduplicated, and business-ready data from the raw Bronze layer. This implements a **data lakehouse pattern** with incremental processing optimized for fitness class scheduling data.

## 🏗️ Architecture Overview

```
📊 BRONZE LAYER (Raw Data)          🥈 SILVER LAYER (Business Ready)
┌─────────────────────────┐         ┌────────────────────────────┐
│ schedule_snapshots      │         │ silver_classes             │
│ - Raw scraping results │   ──►   │ - One row per unique class │
│ - Every scrape creates │         │ - Deduplication applied    │
│   new rows              │         │ - Business logic applied  │
│ - Historical data       │         │ - Incremental updates     │
└─────────────────────────┘         └────────────────────────────┘
```

## 🎯 Business Logic

### **Core Principles:**

1. **Past Classes (start_ts < NOW)**: 
   - ✅ **Immutable** - Never update once class has started
   - Preserves final availability state before class began

2. **Future Classes (start_ts > NOW)**:
   - 🔄 **Always use latest** scraped data
   - Classes can be cancelled, capacity changes, etc.

3. **Currently Running Classes**:
   - 🔄 **Use latest** data (real-time availability changes)

4. **New Classes**:
   - ➕ **Insert** new silver records immediately

5. **Missing Classes**:
   - ❌ **Mark as cancelled** (don't delete - preserve history)

### **Incremental Processing:**

- Runs automatically after each scraping session (3x daily)
- Only processes new bronze data since last successful aggregation
- Efficient: No full table scans, only delta processing
- Fault-tolerant: Failed runs don't affect previous aggregations

## 📊 Schema Design

### `silver_classes` Table

| Column | Type | Description |
|--------|------|-------------|
| `class_id` | TEXT | Unique identifier per class (source + hash of key fields) |
| `source` | TEXT | Scraper source (coolcharm, koepel, rite, rowreformer) |
| `class_name` | TEXT | Name/type of class |
| `instructor` | TEXT | Instructor name |
| `location` | TEXT | Studio/location |
| `start_ts` | TIMESTAMPTZ | Class start time |
| `end_ts` | TIMESTAMPTZ | Class end time |
| `capacity` | INTEGER | Total class capacity |
| `spots_available` | INTEGER | Available spots |
| `status` | TEXT | Booking status |
| `url` | TEXT | Booking URL |
| **Metadata** | | |
| `first_seen_at` | TIMESTAMPTZ | When class was first discovered |
| `last_updated_at` | TIMESTAMPTZ | Last time record was modified |
| `last_scraped_at` | TIMESTAMPTZ | Last time seen in bronze data |
| `is_cancelled` | BOOLEAN | Whether class was cancelled |
| `is_past` | BOOLEAN | Whether class has already occurred |
| **Source Tracking** | | |
| `source_run_id` | TEXT | Reference to bronze scrape run |
| `source_snapshot_id` | BIGINT | Reference to bronze snapshot |
| `raw_data` | JSONB | Complete original JSON data |

### `silver_aggregation_log` Table

Tracks every aggregation run for monitoring and debugging.

## 🚀 Getting Started

### 1. **Initial Setup (One-time)**

```bash
cd "Schedule scraper"

# Run initial migration of all bronze data to silver
python migrate_bronze_to_silver.py
```

This processes your entire historical dataset (~114k records) to create the initial silver layer.

### 2. **Ongoing Operations (Automatic)**

The silver aggregation runs automatically via GitHub Actions after each scraping session. No manual intervention needed.

### 3. **Manual Operations**

```bash
# Run incremental aggregation manually
python silver_aggregation.py

# View silver layer summary
python query_silver_layer.py summary

# Interactive class search
python query_silver_layer.py search
```

## 📈 Monitoring & Queries

### **Quick Status Check:**

```sql
-- Overall statistics
SELECT 
    COUNT(*) as total_classes,
    COUNT(*) FILTER (WHERE is_cancelled) as cancelled,
    COUNT(*) FILTER (WHERE is_past) as past,
    COUNT(*) FILTER (WHERE start_ts > NOW()) as future
FROM silver_classes;

-- By source breakdown
SELECT 
    source,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE start_ts > NOW() AND NOT is_cancelled) as upcoming
FROM silver_classes
GROUP BY source;
```

### **Business Queries:**

```sql
-- Most popular classes (by booking rate)
SELECT 
    class_name,
    location,
    COUNT(*) as occurrence_count,
    AVG((capacity - spots_available)::float / capacity * 100) as avg_booking_rate
FROM silver_classes
WHERE capacity > 0 AND start_ts > NOW() - INTERVAL '30 days'
GROUP BY class_name, location
ORDER BY avg_booking_rate DESC;

-- Availability trends
SELECT 
    DATE_TRUNC('week', start_ts) as week,
    source,
    AVG(spots_available::float / NULLIF(capacity, 0) * 100) as avg_availability_pct
FROM silver_classes
WHERE start_ts > NOW() - INTERVAL '8 weeks'
AND capacity > 0
GROUP BY week, source
ORDER BY week, source;

-- Peak times analysis
SELECT 
    EXTRACT(dow FROM start_ts) as day_of_week,
    EXTRACT(hour FROM start_ts) as hour,
    COUNT(*) as class_count,
    AVG((capacity - spots_available)::float / capacity * 100) as avg_booking_rate
FROM silver_classes
WHERE start_ts > NOW() - INTERVAL '4 weeks'
AND capacity > 0
GROUP BY day_of_week, hour
ORDER BY day_of_week, hour;
```

### **Data Quality Monitoring:**

```sql
-- Check for data quality issues
SELECT 
    source,
    COUNT(*) FILTER (WHERE class_name IS NULL) as missing_class_name,
    COUNT(*) FILTER (WHERE start_ts IS NULL) as missing_start_time,
    COUNT(*) FILTER (WHERE capacity IS NULL OR capacity <= 0) as invalid_capacity,
    COUNT(*) FILTER (WHERE spots_available < 0) as negative_availability
FROM silver_classes
GROUP BY source;

-- Recent aggregation status
SELECT 
    run_id,
    started_at,
    completed_at,
    status,
    records_processed,
    records_inserted,
    records_updated
FROM silver_aggregation_log
ORDER BY started_at DESC
LIMIT 10;
```

## 🔧 Class ID Generation Logic

Each class gets a unique `class_id` based on source-specific key combinations:

- **CoolCharm**: `date + time + class_name + location`
- **Koepel**: `date + time + instructor + description` 
- **Rite**: `name + date + hour + address + instructor`
- **RowReformer**: `week_day + details`

This matches the deduplication logic from your `analyze_results.ipynb` notebook.

## ⚡ Performance Considerations

### **Indexes:**
- `ix_silver_source_start`: Fast filtering by source and time range
- `ix_silver_status`: Efficient cancelled/past class queries
- `ix_silver_updated`: Monitoring recent changes

### **Incremental Processing:**
- Only processes new bronze data since last successful run
- Typical incremental run processes <100 records vs 114k full scan
- ~10x faster than full reprocessing

### **Query Optimization:**
- Use `start_ts > NOW()` for future classes (uses index)
- Filter by `is_cancelled = FALSE` for active classes
- Source-specific queries are highly optimized

## 🚨 Troubleshooting

### **Common Issues:**

1. **Aggregation Fails**:
   ```bash
   # Check recent logs
   python query_silver_layer.py
   
   # Check specific error
   SELECT * FROM silver_aggregation_log WHERE status = 'failed' ORDER BY started_at DESC LIMIT 5;
   ```

2. **Missing Classes**:
   - Check bronze layer: `SELECT COUNT(*) FROM schedule_snapshots WHERE scraped_at > NOW() - INTERVAL '1 day'`
   - Verify scraper wrote to bronze successfully
   - Run manual aggregation: `python silver_aggregation.py`

3. **Duplicate Classes**:
   - Check class_id generation logic
   - May indicate changes in source data structure
   - Review raw_data field to understand source changes

### **Recovery:**

```bash
# Re-run specific aggregation
python silver_aggregation.py

# Full rebuild (nuclear option)
# 1. Truncate silver_classes
# 2. Run: python migrate_bronze_to_silver.py
```

## 🎯 Future Enhancements

1. **Gold Layer**: Analytics-ready aggregations (weekly summaries, trends)
2. **Real-time Alerts**: Notify when popular classes become available
3. **Capacity Predictions**: ML models for booking probability
4. **Data Quality Monitoring**: Automated anomaly detection
5. **API Layer**: REST API for accessing silver data

## 📚 Related Files

- `silver_aggregation.py` - Main aggregation logic
- `migrate_bronze_to_silver.py` - Initial migration script
- `query_silver_layer.py` - Query utility and monitoring
- `.github/workflows/scrape.yml` - Automated pipeline
- `analyze_results.ipynb` - Original analysis (reference for logic)
