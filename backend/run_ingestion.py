import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.database import SessionLocal
from app.services.data_ingestion import ingest_all

if __name__ == "__main__":
    print("Starting SmartRoute Data Ingestion Pipeline...")
    db = SessionLocal()
    try:
        ingest_all(db)
        print("SmartRoute Transit Database is Ready!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
