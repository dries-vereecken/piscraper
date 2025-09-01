# Schedule Scraper

A comprehensive fitness schedule scraping and analysis system with proper Python package structure.

## 🏗️ Project Structure

```
schedule-scraper/
├── src/                           # Source code packages
│   ├── scrapers/                  # Web scrapers for fitness studios
│   │   ├── __init__.py
│   │   ├── base.py               # Base scraper class
│   │   ├── cli.py                # Command-line interface
│   │   ├── koepel.py             # Koepel studio scraper
│   │   ├── coolcharm.py          # CoolCharm studio scraper
│   │   ├── rite.py               # Rite studio scraper
│   │   └── rowreformer.py        # RowReformer studio scraper
│   ├── dashboard/                 # Streamlit dashboard
│   │   ├── __init__.py
│   │   └── app.py                # Main dashboard application
│   ├── database/                  # Database utilities and models
│   │   ├── __init__.py
│   │   ├── utils.py              # Database connection and operations
│   │   ├── models.py             # Data models
│   │   └── schema.sql            # Database schema
│   └── silver_layer/              # Data processing and aggregation
│       ├── __init__.py
│       ├── aggregator.py         # Silver layer aggregation logic
│       └── query.py              # Query utilities
├── scripts/                       # Utility scripts
│   ├── run_dashboard.py          # Dashboard launcher
│   ├── setup_dashboard.py        # Dashboard setup
│   ├── migrate_existing_jsons.py # Data migration
│   ├── create_demo_data.py       # Demo data creation
│   └── run_initial_silver_migration.py
├── tests/                         # Test suite
├── docs/                          # Documentation
│   ├── README_DASHBOARD.md
│   ├── README_DATABASE.md
│   └── README_SILVER_LAYER.md
├── config/                        # Configuration files
│   └── requirements.txt
├── notebooks/                     # Jupyter notebooks (kept for analysis)
├── scraped_data/                  # Scraped data storage (fallback)
├── pyproject.toml                # Modern Python project configuration
├── run_scrapers.py               # Convenience script for scrapers
├── run_dashboard.py              # Convenience script for dashboard
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database (optional, falls back to JSON files)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd "Schedule scraper"
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **For development:**
   ```bash
   pip install -e ".[dev]"
   ```

### Configuration

1. **Environment Setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your database URL
   ```

2. **Database Setup (optional):**
   - See `docs/README_DATABASE.md` for detailed setup instructions

### Usage

#### Running Scrapers

**Using the CLI:**
```bash
# Run specific scraper
schedule-scraper koepel

# Run all scrapers
schedule-scraper --all

# List available scrapers
schedule-scraper --list

# Run with visible browser (debugging)
schedule-scraper koepel --no-headless
```

**Using convenience script:**
```bash
# From project root
python run_scrapers.py koepel
```

#### Running Dashboard

```bash
# Using convenience script
python run_dashboard.py

# Or directly
streamlit run src/dashboard/app.py
```

## 📦 Package Structure Benefits

### ✅ What's Improved

1. **Proper Python Packaging:**
   - Clear separation of concerns with dedicated packages
   - Proper `__init__.py` files with explicit exports
   - Modern `pyproject.toml` configuration

2. **Inheritance Hierarchy:**
   - `BaseScraper` class provides common functionality
   - Individual scrapers inherit and implement specific logic
   - Consistent error handling and data saving

3. **Configuration Management:**
   - Centralized configuration in `pyproject.toml`
   - Environment-specific settings via `.env`
   - Proper dependency version ranges

4. **Script Organization:**
   - Utility scripts separated from source code
   - Convenience scripts in project root
   - Clear CLI interface

5. **Documentation Structure:**
   - All documentation in `docs/` directory
   - Comprehensive README files
   - Clear usage examples

### 🔧 Development Workflow

**Setup development environment:**
```bash
pip install -e ".[dev]"
pre-commit install  # (when pre-commit config is added)
```

**Run tests:**
```bash
pytest
```

**Code formatting:**
```bash
black src/
isort src/
```

**Type checking:**
```bash
mypy src/
```

## 🗃️ Database Architecture

The system uses a three-layer approach:

1. **Bronze Layer:** Raw scraped data in `schedule_snapshots` table
2. **Silver Layer:** Cleaned, deduplicated business-ready data
3. **Gold Layer:** Dashboard views and analytics

See `docs/README_DATABASE.md` and `docs/README_SILVER_LAYER.md` for details.

## 📊 Dashboard

Interactive Streamlit dashboard with:
- Real-time booking metrics
- Revenue analysis
- Fill rate heatmaps
- Multi-studio comparisons

See `docs/README_DASHBOARD.md` for details.

## 🤝 Contributing

1. **Code Style:** Follow PEP 8, use Black and isort
2. **Testing:** Add tests for new features
3. **Documentation:** Update relevant README files
4. **Type Hints:** Use type hints for all new code

## 📝 Migration Guide

If you're migrating from the old flat structure:

1. **Update import statements** in your scripts to use the new package structure
2. **Use the CLI** instead of running individual Python files
3. **Environment variables** remain the same
4. **Database schema** is unchanged

## 🚧 Next Steps

To complete the modernization:

1. **Add comprehensive tests** (see `tests/` directory)
2. **Implement pre-commit hooks** for code quality
3. **Add CI/CD pipeline** improvements
4. **Create Docker containers** for deployment
5. **Add monitoring and logging** infrastructure

## 📖 Documentation

- [Dashboard Setup](docs/README_DASHBOARD.md)
- [Database Configuration](docs/README_DATABASE.md) 
- [Silver Layer Architecture](docs/README_SILVER_LAYER.md)