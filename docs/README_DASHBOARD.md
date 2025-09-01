# Pilates Bookings Dashboard

A comprehensive Streamlit-based dashboard for visualizing pilates class booking data from Belgian studios.

## Features

### 📊 Key Metrics
- **Total Classes**: Number of classes in selected period
- **Average Fill Rate**: Overall booking percentage across all classes
- **Fully Booked %**: Percentage of classes at 100% capacity
- **Cancelled %**: Percentage of cancelled classes

### 📍 Source Breakdown
- Individual metrics for each studio (Coolcharm, Koepel, Rite, RowReformer)
- Color-coded status indicators based on fill rates
- Comparative analysis across studios

### 💰 Revenue Analysis
- Daily revenue chart (stacked by studio)
- Cumulative revenue trend line
- Estimated revenue based on class capacity and pricing

### 🔥 Class Fill Heatmap
- Interactive heatmap showing fill percentages by day of week and hour
- Filter by specific studio or view all combined
- Color-coded visualization (blue = low fill, red = high fill)

### 🎛️ Interactive Filters
- **Date Range Selector**: Choose any date range for analysis
- **Source Filter**: Select specific studios to include/exclude
- **Real-time Updates**: Data refreshes automatically

## Setup and Installation

### Prerequisites
1. Python 3.8 or higher
2. PostgreSQL database with silver layer data
3. Environment variables configured

### Installation Steps

1. **Install Dependencies**
   ```bash
   cd "Schedule scraper"
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   
   Create a `.env` file in the `Schedule scraper` directory:
   ```
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

3. **Launch Dashboard**
   ```bash
   # Option 1: Using the launch script
   python run_dashboard.py
   
   # Option 2: Direct Streamlit command
   streamlit run dashboard.py --server.port 8501
   ```

4. **Access Dashboard**
   
   Open your browser and navigate to: `http://localhost:8501`

## Data Requirements

The dashboard expects data in the `silver_classes` table with the following schema:

```sql
CREATE TABLE silver_classes (
    class_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    class_name TEXT,
    instructor TEXT,
    location TEXT,
    start_ts TIMESTAMPTZ,
    end_ts TIMESTAMPTZ,
    capacity INTEGER,           -- Total spots in the class
    spots_available INTEGER,    -- IMPORTANT: Actually spots BOOKED (not available!)
    status TEXT,
    url TEXT,
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    last_scraped_at TIMESTAMPTZ,
    is_cancelled BOOLEAN,
    is_past BOOLEAN,
    source_run_id TEXT,
    source_snapshot_id BIGINT,
    raw_data JSONB
);
```

**⚠️ Important Data Interpretation:**
- `capacity`: Total number of spots in the class
- `spots_available`: **Actually represents spots BOOKED** (despite the confusing name)
- Fill percentage = `(spots_available / capacity) * 100`
- Remaining spots = `capacity - spots_available`

## Usage Guide

### Basic Navigation
1. **Sidebar Filters**: Use the left sidebar to filter by date range and studios
2. **KPI Cards**: Top row shows key performance indicators
3. **Source Breakdown**: Compare performance across different studios
4. **Charts**: Scroll down to see detailed visualizations

### Filter Options
- **Date Range**: Select start and end dates (defaults to last 3 months + next month)
- **Sources**: Choose which studios to include (all selected by default)

### Understanding the Visualizations

#### Revenue Chart
- **Bars**: Daily revenue stacked by studio (estimated based on bookings)
- **Line**: Cumulative revenue over time
- **Pricing Assumptions**: 
  - Coolcharm: €25/class
  - Koepel: €20/class  
  - Rite: €30/class
  - RowReformer: €28/class

#### Fill Heatmap
- **X-axis**: Hour of day (07:00 - 21:00)
- **Y-axis**: Day of week (Monday - Sunday)
- **Color**: Fill percentage (0% = blue, 100% = red)
- **Numbers**: Exact fill percentage in each cell

### Performance Tips
- Data is cached for 5 minutes to improve performance
- Narrow date ranges load faster
- Use source filters to focus on specific studios

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check your `DATABASE_URL` in `.env` file
   - Verify database is accessible and credentials are correct
   - Ensure PostgreSQL is running

2. **No Data Found**
   - Check if silver layer has been populated
   - Verify date range includes data
   - Ensure selected sources have data in the time period

3. **Performance Issues**
   - Reduce date range
   - Select fewer sources
   - Clear browser cache
   - Restart the dashboard

### Getting Help
- Check the silver layer aggregation logs: `SELECT * FROM silver_aggregation_log;`
- Verify data exists: `SELECT COUNT(*) FROM silver_classes;`
- Check source distribution: `SELECT source, COUNT(*) FROM silver_classes GROUP BY source;`

## Development

### File Structure
```
Schedule scraper/
├── dashboard.py           # Main dashboard application
├── run_dashboard.py       # Launch script
├── db_utils.py           # Database utilities
├── silver_aggregation.py # Data processing
├── requirements.txt      # Python dependencies
└── README_DASHBOARD.md   # This file
```

### Customization
- Modify revenue assumptions in `create_revenue_chart()`
- Adjust color schemes in chart functions
- Add new metrics in `calculate_booking_metrics()`
- Customize caching TTL (currently 5 minutes)

### Adding New Features
1. Create new analysis functions
2. Add UI components in the main() function
3. Update requirements.txt if new dependencies are needed
4. Test with various data scenarios
