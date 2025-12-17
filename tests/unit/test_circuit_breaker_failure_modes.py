import unittest
import os
from unittest.mock import MagicMock, patch
import pytest

# Adjust path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.circuit_breaker_service import CircuitBreakerService
from workers.common.models import CircuitBreakerState

class TestCircuitBreakerFailureModes(unittest.TestCase):
    
    @patch("services.circuit_breaker_service.SessionLocal")
    def test_s3_unavailable_raises_critical_error(self, mock_session_cls):
        """
        Verify that if S3 is unavailable (SIMULATE_S3_FAILURE=1), 
        the service blocks state transitions (Zero Tolerance).
        """
        # Setup
        os.environ["SIMULATE_S3_FAILURE"] = "1"
        
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        # Mock finding breaker
        mock_breaker = CircuitBreakerState(breaker_id="test-fail", state="CLOSED")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_breaker
        
        service = CircuitBreakerService(mock_db)
        
        # Act & Assert
        with self.assertRaises(RuntimeError) as cm:
            service.transition_state(
                breaker_id="test-fail", 
                new_state="OPEN", 
                actor="test", 
                reason="fail trip"
            )
            
        self.assertIn("CRITICAL: S3 Audit Store Unavailable", str(cm.exception))
        
        # Cleanup
        del os.environ["SIMULATE_S3_FAILURE"]

if __name__ == "__main__":
    unittest.main()
