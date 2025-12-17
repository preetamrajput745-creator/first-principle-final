import unittest
import sys
import os
import importlib
from unittest.mock import MagicMock, patch

# Ensure we can import workers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class MockColumn:
    def __init__(self, name="col"):
        self.name = name
    def __ge__(self, other): return True
    def __gt__(self, other): return True
    def __le__(self, other): return True
    def __lt__(self, other): return True
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def desc(self): return self
    def asc(self): return self

class MockModel:
    created_at = MockColumn("created_at")
    timestamp = MockColumn("timestamp")
    pnl = MockColumn("pnl")
    status = "active"
    id = "12345678-1234-5678-1234-567812345678"
    exit_time = None
    realized_slippage = 0.0
    price = 100.0
    regime_volatility = "normal"

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        # Patch sys.modules
        self.patch_modules = patch.dict(sys.modules, {
            'common.models': MagicMock(),
            'common.database': MagicMock(),
            'workers.risk.safety_logger': MagicMock()
        })
        self.patch_modules.start()

        # Patch Logger
        self.patch_logger = patch('workers.risk.safety_logger.SafetyLogger')
        self.mock_logger_cls = self.patch_logger.start()
        
        # Configure DB Mock on the module mock
        self.mock_db_module = sys.modules['common.database']
        
        # Setup DB Session and Query
        self.mock_query = MagicMock()
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.all.return_value = []
        self.mock_query.count.return_value = 0
        self.mock_query.scalar.return_value = 0.0
        self.mock_query.first.return_value = None
        
        self.mock_db_session = MagicMock()
        self.mock_db_session.query.return_value = self.mock_query
        self.mock_db_session.query.side_effect = None
        self.mock_db_session.__enter__.return_value = self.mock_db_session
        self.mock_db_session.__exit__.return_value = None
        
        self.mock_db_module.get_db.return_value.__iter__.return_value = [self.mock_db_session]
        self.mock_db_module.get_db.return_value.__next__.return_value = self.mock_db_session

        # Setup Models with Simple Classes (Non-Mocks) for Attributes
        self.mock_models = sys.modules['common.models']
        self.mock_models.Signal = MockModel
        self.mock_models.Order = MockModel
        self.mock_models.Automation = MockModel
        
        # RELOAD Module
        import workers.risk.circuit_breaker
        importlib.reload(workers.risk.circuit_breaker)
        self.CircuitBreaker = workers.risk.circuit_breaker.CircuitBreaker
        
        self.cb = self.CircuitBreaker()

    def tearDown(self):
        patch.stopall()
        self.patch_modules.stop()

    def test_check_signal_rate_ok(self):
        self.mock_query.count.return_value = 5
        result = self.cb.check_signal_rate(auto_pause=True)
        self.assertTrue(result)

    def test_check_signal_rate_exceeded(self):
        self.mock_query.count.return_value = 15
        with patch('builtins.print'):
            with patch.object(self.cb, 'pause_all_active_automations') as mock_pause:
                result = self.cb.check_signal_rate(auto_pause=True)
                self.assertFalse(result)
                mock_pause.assert_called_once()

    def test_check_error_rate_not_enough_data(self):
        self.mock_query.count.return_value = 2
        result = self.cb.check_error_rate()
        self.assertTrue(result)

    def test_check_concurrent_orders_ok(self):
        self.mock_query.count.return_value = 3
        result = self.cb.check_concurrent_orders("test_uuid")
        self.assertTrue(result)

    def test_check_concurrent_orders_fail(self):
        self.mock_query.count.return_value = 10
        result = self.cb.check_concurrent_orders("test_uuid")
        self.assertFalse(result)

    def test_check_pnl_health_ok(self):
        self.mock_query.scalar.return_value = -100.0
        result = self.cb.check_pnl_health()
        self.assertTrue(result)

    def test_check_pnl_health_fail(self):
        self.mock_query.scalar.return_value = -600.0
        with patch.object(self.cb, 'pause_all_active_automations') as mock_pause:
            result = self.cb.check_pnl_health(auto_pause=True)
            self.assertFalse(result)
            mock_pause.assert_called_once()
            
    def test_pause_all_active_automations(self):
        # Need to return objects that have .status
        m1 = MagicMock()
        m1.status = "active"
        m1.id = "auto1"
        m1.name = "A1"
        self.mock_query.all.return_value = [m1]
        
        self.cb.pause_all_active_automations("Reason")
        self.assertEqual(m1.status, "paused_risk")

    def test_check_slippage_health_ok(self):
        self.mock_query.all.return_value = []
        self.assertTrue(self.cb.check_slippage_health())

    def test_check_slippage_health_fail(self):
        orders = []
        for i in range(10):
            o = MagicMock()
            o.price = 100.0
            o.realized_slippage = 60.0 # 60%
            orders.append(o)
        self.mock_query.all.return_value = orders
        
        with patch.object(self.cb, 'pause_all_active_automations') as mock_pause:
            self.assertFalse(self.cb.check_slippage_health(auto_pause=True))
            mock_pause.assert_called()

    def test_check_market_regime_ok(self):
        sig = MagicMock()
        sig.regime_volatility = "normal"
        self.mock_query.first.return_value = sig
        self.assertTrue(self.cb.check_market_regime())
    
    def test_check_market_regime_fail(self):
        sig = MagicMock()
        sig.regime_volatility = "high_volatility"
        self.mock_query.first.return_value = sig
        
        with patch.object(self.cb, 'pause_all_active_automations') as mock_pause:
            self.assertFalse(self.cb.check_market_regime(auto_pause=True))
            mock_pause.assert_called()

    def test_trigger_pause(self):
        mock_auto = MagicMock()
        mock_auto.status = "active"
        self.mock_query.filter.return_value.first.return_value = mock_auto
        
        with patch('builtins.print'):
            self.cb.trigger_pause("12345678-1234-5678-1234-567812345678")
            
        self.assertEqual(mock_auto.status, "paused_risk")

if __name__ == '__main__':
    unittest.main()
