#!/usr/bin/env python3
"""
Setup script for the Pilates Bookings Dashboard.
Installs dependencies and validates the environment.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"⏳ {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is adequate."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def check_env_file():
    """Check if .env file exists and has DATABASE_URL."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("⚠️  .env file not found")
        print("   Creating template .env file...")
        
        with open(".env", "w") as f:
            f.write("# Database configuration\n")
            f.write("DATABASE_URL=postgresql://username:password@host:port/database\n")
            f.write("\n# Optional: GitHub SHA for tracking\n")
            f.write("GITHUB_SHA=\n")
        
        print("📝 Created .env template file")
        print("   Please edit .env and add your actual DATABASE_URL")
        return False
    
    # Check if DATABASE_URL is set
    with open(".env", "r") as f:
        content = f.read()
        if "DATABASE_URL=" in content and "postgresql://" in content:
            print("✅ .env file found with DATABASE_URL")
            return True
        else:
            print("⚠️  DATABASE_URL not properly configured in .env")
            return False

def install_dependencies():
    """Install required Python packages."""
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", 
                      "Upgrading pip"):
        return False
    
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", 
                      "Installing dashboard dependencies"):
        return False
    
    return True

def test_imports():
    """Test if all required packages can be imported."""
    required_packages = [
        ("streamlit", "Streamlit web framework"),
        ("plotly", "Plotly charting library"),
        ("pandas", "Pandas data analysis"),
        ("psycopg", "PostgreSQL connector"),
        ("numpy", "NumPy numerical computing"),
        ("dotenv", "Environment variable loader")
    ]
    
    print("🔍 Testing package imports...")
    
    all_good = True
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package} - {description}")
        except ImportError:
            print(f"   ❌ {package} - {description} (not found)")
            all_good = False
    
    return all_good

def test_database_connection():
    """Test database connection."""
    print("🔗 Testing database connection...")
    
    try:
        from db_utils import test_connection
        if test_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Pilates Bookings Dashboard")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        print("❌ Some packages failed to import")
        print("   Try running: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check environment
    env_ok = check_env_file()
    
    # Test database if env is configured
    if env_ok:
        db_ok = test_database_connection()
    else:
        db_ok = False
        print("⏭️  Skipping database test (no DATABASE_URL)")
    
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")
    print(f"   Python: ✅")
    print(f"   Dependencies: ✅")
    print(f"   Environment: {'✅' if env_ok else '⚠️'}")
    print(f"   Database: {'✅' if db_ok else '⚠️'}")
    
    if env_ok and db_ok:
        print("\n🎉 Setup completed successfully!")
        print("\n🚀 Ready to launch dashboard:")
        print("   python run_dashboard.py")
        print("   or")
        print("   streamlit run dashboard.py")
    else:
        print("\n⚠️  Setup completed with warnings:")
        if not env_ok:
            print("   - Configure DATABASE_URL in .env file")
        if not db_ok:
            print("   - Check database connection")
        print("\n📖 See README_DASHBOARD.md for detailed instructions")

if __name__ == "__main__":
    main()
