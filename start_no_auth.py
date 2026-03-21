#!/usr/bin/env python3
"""
Start SRS Engine without authentication for testing live traces.
Run: python start_no_auth.py
"""

import subprocess
import sys
import os

def main():
    """Start the application without authentication requirements."""
    print("🚀 Starting SRS Engine without authentication...")
    print("📡 Live execution traces will be available for testing")
    print("🌐 Application will be available at: http://127.0.0.1:8000")
    print("📊 Traces panel will appear during SRS generation")
    print("\n" + "="*50)
    print("⚠️  NOTE: Authentication is temporarily disabled")
    print("⚠️  This is for testing the live traces feature only")
    print("⚠️  Do not use this configuration in production!")
    print("="*50 + "\n")
    
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Start uvicorn
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "srs_engine.main:app", 
            "--reload", 
            "--host", "127.0.0.1", 
            "--port", "8000"
        ]
        
        print(f"🔧 Running command: {' '.join(cmd)}")
        print("📝 Press Ctrl+C to stop the server\n")
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
