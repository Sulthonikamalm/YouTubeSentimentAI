import os
import sys

# Add project root to sys.path so we can import backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.storage.db import get_db_connection
from backend.routes import get_db_url

def verify():
    print("Memeriksa integritas migrasi database...")
    db_url = get_db_url()
    
    with get_db_connection(db_url) as conn:
        count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        
    print(f"Total komentar saat ini: {count}")
    
    # 10482 is the baseline expected before migration according to the user's report
    if count >= 10482:
        print("✅ SUCCESS: Jumlah komentar aman dan tidak berkurang.")
    else:
        print(f"❌ ERROR: Kehilangan data terdeteksi! Jumlah komentar kurang dari 10482 (Baseline).")
        sys.exit(1)

if __name__ == "__main__":
    verify()
