# Data Directory

This directory contains all data files used by the schedule scraper system.

## Structure

```
data/
├── raw/                   # Raw scraped data (JSON files)
├── processed/             # Processed/cleaned data
├── temp/                  # Temporary files (not version controlled)
└── README.md             # This file
```

## Data Flow

1. **Raw Data (`raw/`)**: 
   - Contains JSON files from web scraping
   - Fallback storage when database is unavailable
   - Files named: `{source}_{timestamp}.json`

2. **Processed Data (`processed/`)**:
   - Cleaned and transformed data
   - Intermediate processing results
   - Export files for analysis

3. **Temporary Data (`temp/`)**:
   - Temporary processing files
   - Cache files
   - Not version controlled

## File Naming Convention

- Raw scrapes: `{source}_{YYYYMMDD_HHMMSS}.json`
- Processed exports: `{source}_processed_{YYYYMMDD}.csv`
- Analysis exports: `analysis_{type}_{YYYYMMDD}.xlsx`

## Storage Notes

- Raw JSON files are excluded from version control via `.gitignore`
- Database is the primary storage - files are fallback only
- Clean up old files periodically to manage disk space
