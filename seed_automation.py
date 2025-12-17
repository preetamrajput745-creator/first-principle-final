import sys
import os
import uuid

# Add workers to path
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db, engine, Base
from common.models import Automation

# Create tables
Base.metadata.create_all(bind=engine)

def seed():
    with next(get_db()) as db:
        if not db.query(Automation).filter(Automation.slug == "first-principle-strategy").first():
            default_auto = Automation(
                name="First Principle Strategy",
                slug="first-principle-strategy",
                description="Default automation for First Principle Trading",
                status="active"
            )
            db.add(default_auto)
            db.commit()
            print("✅ Seeded default automation: First Principle Strategy")
        else:
            print("ℹ️ Automation already exists.")

if __name__ == "__main__":
    seed()
