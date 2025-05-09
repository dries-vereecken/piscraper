# Schedule Scraper

A collection of web scrapers for various fitness schedules.

## Scrapers
- Koepel
- Cool Charm
- Rite
- Row Reformer
- Yoko

## Setup
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install jupyter pandas requests beautifulsoup4
```

## Usage
Each scraper is implemented as a Jupyter notebook. Run them individually to scrape the respective schedules.

## Automated Scraping
The scrapers are scheduled to run daily using GitHub Actions. The scraped data is automatically committed to the repository. 