import yaml
import subprocess
import os

# Define Promtool tests
tests = {
    "rule_files": ["../prometheus/alert_rules.yml"],
    "evaluation_interval": "1m",
    "tests": [
        {
            "interval": "1m",
            "input_series": [
                {
                    "series": 'heartbeat_timestamp{component="ingest"}',
                    "values": '0 0 0 0 0 0 0 0 0 0' # Old timestamp (0) implies missing updates if time() advances? 
                                                    # time() in promtool starts at 0. If current time is 0, difference is 0. 
                                                    # We need to simulate time passing or old value.
                                                    # Promtool syntax: values are at 0m, 1m, 2m...
                                                    # If we put '0', at 1m (time=60), 60-0 = 60 > 30 -> Alert!
                },
                {
                    "series": 'signals_total{symbol="BTCUSDT"}',
                    "values": '0 10 20 60 60' # Increase: 0->60 in ~3m. Rate > 30/h? 
                                               # increase[1h] of 60 is 60. > 30 -> Alert.
                }
            ],
            "alert_rule_test": [
                {
                    "eval_time": "5m",
                    "alertname": "HeartbeatMissingCritical",
                    "exp_alerts": [
                        {
                            "exp_labels": {"severity": "critical", "component": "ingest"},
                            "exp_annotations": {"summary": "CRITICAL: Heartbeat missing for ingest"}
                        }
                    ]
                },
                {
                    "eval_time": "5m",
                    "alertname": "SignalRateSpike",
                    "exp_alerts": [
                        {
                            "exp_labels": {"severity": "warning", "symbol": "BTCUSDT"},
                            "exp_annotations": {"summary": "Signal Rate Spike > 3x Baseline (BTCUSDT)"}
                        }
                    ]
                }
            ]
        }
    ]
}

if not os.path.exists("tests"):
    os.makedirs("tests")
    
with open("tests/alert_test.yml", "w") as f:
    yaml.dump(tests, f)

PROMETHEUS_HOME = os.path.abspath("tools/prometheus-2.45.0.windows-amd64")
promtool = os.path.join(PROMETHEUS_HOME, "promtool.exe")

print("Running Promtool Unit Tests...")
cmd = [promtool, "test", "rules", "tests/alert_test.yml"]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
print(res.stderr)

with open("alert_test_log.txt", "w") as f:
    f.write(res.stdout + "\n" + res.stderr)
