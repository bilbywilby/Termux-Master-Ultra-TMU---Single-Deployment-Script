"""TMU Marathoner Scoring Algorithm Tests"""
import sys
sys.path.insert(0, '.')

from dashboard import process_telemetry, node_states
import unittest
from datetime import timedelta

class TestScoringAlgorithm(unittest.TestCase):
    
    def setUp(self):
        """Clear node states before each test"""
        node_states.clear()
    
    def test_operational_node_baseline(self):
        """Normal conditions should yield positive score"""
        process_telemetry("test-node", {"cpu": 20, "battery": 90, "temp": 35})
        status = node_states.get("test-node", {})
        
        self.assertEqual(status["status"], "operational")
        self.assertGreater(status["score"], 40)
        self.assertLessEqual(status["score"], 100)
    
    def test_high_cpu_decreases_score(self):
        """CPU overload should penalize score"""
        process_telemetry("stress-test", {"cpu": 95, "battery": 90, "temp": 35})
        status = node_states.get("stress-test", {})
        
        self.assertLess(status["score"], 50)
    
    def test_thermal_threshold_under_40(self):
        """Temps under 40°C should not trigger thermal penalty"""
        process_telemetry("cool-node", {"cpu": 20, "battery": 90, "temp": 39})
        status = node_states.get("cool-node", {})
        
        self.assertNotEqual(status["status"], "demoted")
    
    def test_thermal_breach_over_45(self):
        """Temperature above 45°C forces demotion"""
        process_telemetry("hot-node", {"cpu": 20, "battery": 90, "temp": 47})
        status = node_states.get("hot-node", {})
        
        self.assertEqual(status["status"], "demoted")
        self.assertEqual(status["score"], 0.0)
    
    def test_charging_bonus_applied(self):
        """Positive battery delta should increase score"""
        process_telemetry("charging-node", {"cpu": 20, "battery": 50, "temp": 35})
        # Simulate charging state
        process_telemetry("charging-node", {"cpu": 20, "battery": 55, "temp": 35})
        status = node_states.get("charging-node", {})
        
        self.assertGreater(status["delta_bat"], 0)
        self.assertGreater(status["score"], 30)
    
    def test_discharging_penalty(self):
        """Negative battery delta should decrease score"""
        process_telemetry("draining-node", {"cpu": 20, "battery": 90, "temp": 35})
        process_telemetry("draining-node", {"cpu": 20, "battery": 85, "temp": 35})
        status = node_states.get("draining-node", {})
        
        self.assertLess(status["delta_bat"], 0)
        self.assertLess(status["score"], 50)
    
    def test_thermal_slope_penalty(self):
        """Rapid temperature rise should penalize more"""
        process_telemetry("spiking-temp", {"cpu": 20, "battery": 90, "temp": 30})
        process_telemetry("spiking-temp", {"cpu": 20, "battery": 90, "temp": 42})
        status = node_states.get("spiking-temp", {})
        
        self.assertGreater(status["slope"], 0)
    
    def test_state_persistence(self):
        """Node should retain state across multiple reports"""
        process_telemetry("persistent-node", {"cpu": 50, "battery": 80, "temp": 40})
        process_telemetry("persistent-node", {"cpu": 60, "battery": 75, "temp": 41})
        status = node_states.get("persistent-node", {})
        
        self.assertIn("ts", status)
        self.assertIn("slope", status)
        self.assertTrue(status["slope"] >= 0)

class TestSafetyMechanisms(unittest.TestCase):
    
    def setUp(self):
        node_states.clear()
    
    def test_circuit_breaker_at_critical_temp(self):
        """Absolute temperature cutoff at 45°C"""
        process_telemetry("critical-node", {"cpu": 10, "battery": 100, "temp": 46})
        status = node_states.get("critical-node", {})
        
        self.assertEqual(status["score"], 0.0)
        self.assertEqual(status["status"], "demoted")
    
    def test_score_bounds_clamped(self):
        """Scores should never exceed 0-100 range"""
        process_telemetry("perfect-node", {"cpu": 0, "battery": 100, "temp": 25})
        status = node_states.get("perfect-node", {})
        
        self.assertGreaterEqual(status["score"], 0)
        self.assertLessEqual(status["score"], 100)

if __name__ == '__main__':
    unittest.main(verbosity=2)
