
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

class TestIngestSmoke(unittest.TestCase):
    """
    TRIPLE CHECK: Deployment Smoke Test (Ingest Component)
    Verifies that the Ingest API Endpoint accepts data and attempts to publish to Kafka/Redis.
    """
    
    def setUp(self):
        self.client = TestClient(app)
        
    @patch('api.main.producer')
    def test_webhook_ingest_flow(self, mock_producer):
        """
        Simulate a webhook POST to /ingest/webhook.
        Verify it transforms to 'market.tick.<symbol>' event.
        """
        print("\n[Test] Smoke Test: Ingest API -> Kafka/Bus")
        
        payload = {
            "symbol": "SMOKE_TEST",
            "price": 100.50,
            "volume": 100,
            "timestamp": "2025-12-09T10:00:00Z"
        }
        
        response = self.client.post("/ingest/webhook", json=payload)
        
        # 1. Check HTTP Response
        self.assertEqual(response.status_code, 200, f"API Failed: {response.text}")
        json_resp = response.json()
        self.assertEqual(json_resp['status'], 'received')
        self.assertEqual(json_resp['topic'], 'market.tick.SMOKE_TEST')
        
        # 2. Check Producer Send
        # The API code uses producer.send(topic, payload)
        self.assertTrue(mock_producer.send.called, "Kafka Producer was not called!")
        
        args = mock_producer.send.call_args
        topic = args[0][0]
        msg = args[0][1]
        
        self.assertEqual(topic, "market.tick.SMOKE_TEST")
        self.assertEqual(msg['price'], 100.50)
        
        print("PASS: Ingest API successfully accepted data and triggered Producer.")

if __name__ == "__main__":
    unittest.main()
