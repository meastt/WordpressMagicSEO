import os
import shutil
import glob
from datetime import datetime
import argparse

# Define source and destination
SOURCE_DIR = "."
DEST_DIR = "data/reports"

# Patterns to move
PATTERNS = [
    "*_audit.json",
    "*_audit_final.json",
    "*_audit_log.txt",
    "*_seo_report.txt",
    "*_seo_fixes.json",
    "automation_runs.json",
    "mock_gsc_*.csv",
    "*.xlsx" # GSC exports
]

# Files to specificially EXCLUDE from moving (config, scripts, etc.)
EXCLUDE = [
    "requirements.txt",
    "vercel.json",
    "package.json",
    "verify_fixes.py",
    "test_real_gsc.py",
    "test_phase2.py",
    "test_content_engine.py",
    "seo_audit_cli.py"
]

def cleanup_workspace(delete_old=False, days_old=7):
    """
    Moves report files to data/reports.
    If delete_old=True, deletes files in data/reports older than days_old.
    """
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"📁 Created directory: {DEST_DIR}")

    print(f"🧹 Cleaning up workspace...")
    count = 0
    
    # 1. Move Files
    for pattern in PATTERNS:
        files = glob.glob(os.path.join(SOURCE_DIR, pattern))
        for file_path in files:
            file_name = os.path.basename(file_path)
            
            if file_name in EXCLUDE or os.path.isdir(file_path):
                continue
                
            dest_path = os.path.join(DEST_DIR, file_name)
            
            # If exists in dest, overwrite or skip? Let's overwrite (move)
            try:
                shutil.move(file_path, dest_path)
                print(f"   Moved: {file_name} -> {DEST_DIR}/")
                count += 1
            except Exception as e:
                print(f"   ❌ Error moving {file_name}: {e}")

    print(f"✨ Moved {count} files to {DEST_DIR}/")

    # 2. Delete Old Files
    if delete_old:
        print(f"\n🗑️  Deleting files older than {days_old} days in {DEST_DIR}...")
        deleted_count = 0
        now = datetime.now()
        
        for file_name in os.listdir(DEST_DIR):
            file_path = os.path.join(DEST_DIR, file_name)
            if not os.path.isfile(file_path):
                continue
                
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            age_days = (now - file_mtime).days
            
            if age_days > days_old:
                os.remove(file_path)
                print(f"   Deleted: {file_name} ({age_days} days old)")
                deleted_count += 1
        
        print(f"✨ Deleted {deleted_count} old files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup project root.")
    parser.add_argument("--delete", action="store_true", help="Delete old files in data/reports")
    parser.add_argument("--days", type=int, default=7, help="Age in days to delete (default: 7)")
    
    args = parser.parse_args()
    cleanup_workspace(delete_old=args.delete, days_old=args.days)
