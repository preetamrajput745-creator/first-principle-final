import sys
import os

workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Automation

def check_status():
    with next(get_db()) as db:
        auto = db.query(Automation).filter(Automation.slug == "first-principle-strategy").first()
        print(f"Automation Status: {auto.status}")

if __name__ == "__main__":
    check_status()
