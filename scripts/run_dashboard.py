#!/usr/bin/env python3
"""
Launch script for the Pilates Bookings Dashboard.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the Streamlit dashboard."""
    
    # Get the directory containing this script and find the dashboard
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    dashboard_path = project_root / "src" / "dashboard" / "app.py"
    
    if not dashboard_path.exists():
        print(f"Error: Dashboard file not found at {dashboard_path}")
        sys.exit(1)
    
    # Check if .env file exists
    env_path = project_root / ".env"
    if not env_path.exists():
        print("Warning: .env file not found. Make sure DATABASE_URL is set.")
    
    print("Starting Pilates Bookings Dashboard...")
    print(f"Dashboard will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop the dashboard")
    
    try:
        # Launch Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8501",
            "--server.address", "localhost"
        ], check=True)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error launching dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
