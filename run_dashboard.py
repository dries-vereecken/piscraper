#!/usr/bin/env python3
"""
Convenience script to run dashboard from project root.
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import streamlit and run dashboard directly
import os
import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit dashboard."""
    
    # Get paths
    project_root = Path(__file__).parent
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
        # Add src to Python path and launch Streamlit
        env = dict(os.environ)
        env['PYTHONPATH'] = str(project_root / "src") + os.pathsep + env.get('PYTHONPATH', '')
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8501",
            "--server.address", "localhost"
        ], check=True, env=env)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error launching dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()