import unittest
import os
import sys
from sqlalchemy import text

class TestSmoke(unittest.TestCase):
    def test_database_connection(self):
        # Allow simulation of failure
        if os.environ.get("SIMULATE_SMOKE_FAILURE") == "true":
            self.fail("Simulated smoke failure")

        # In a real smoke test this would hit the health endpoint which checks DB
        # For this standalone script we verify we can import and connect
        try:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../workers')))
            from common.database import get_db
            with next(get_db()) as db:
                db.execute(text("SELECT 1"))
        except Exception as e:
            self.fail(f"Database connection failed: {e}")

if __name__ == '__main__':
    unittest.main()
