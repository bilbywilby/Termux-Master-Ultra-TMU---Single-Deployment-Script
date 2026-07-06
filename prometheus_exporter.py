#!/usr/bin/env python3
"""TMU Phase 6: Prometheus Metrics Exporter for Grafana/Monitoring"""
import os
import json
from pathlib import Path
from flask import Flask, Response

app = Flask(__name__)

MASTER_STORAGE = Path(os.environ.get("MASTER_STORAGE", f"{Path.home()}/.termux_master"))
LEDGER_FILE = MASTER_STORAGE / "state" / "history.jsonl"

def read_latest_state():
    """Reads JSONL ledger and extracts latest state per node."""
    nodes = {}
    if not LEDGER_FILE.exists():
        return nodes
        
    try:
        with open(LEDGER_FILE, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get('event') == 'HEARTBEAT_PROCESSED' and 'node_id' in str(data):
                    # Parse payload from ledger
                    payload = data.get('payload', {})
                    node_id = payload.get('node_id', 'unknown')
                    nodes[node_id] = payload
    except Exception as e:
        print(f"[ERROR] Failed to parse ledger: {e}")
        
    return nodes

@app.route('/metrics')
def metrics():
    """Generates Prometheus-formatted metrics."""
    latest_state = read_latest_state()
    lines = []
    
    lines.append("# HELP tmu_node_cpu_usage_percent Current CPU utilization per node")
    lines.append("# TYPE tmu_node_cpu_usage_percent gauge")
    for node_id, data in latest_state.items():
        cpu = data.get('cpu', 0)
        lines.append(f'tmu_node_cpu_usage_percent{{node_id="{node_id}"}} {cpu}')
        
    lines.append("# HELP tmu_node_temperature_celsius Current temperature in Celsius")
    lines.append("# TYPE tmu_node_temperature_celsius gauge")
    for node_id, data in latest_state.items():
        temp = data.get('temp', 0)
        lines.append(f'tmu_node_temperature_celsius{{node_id="{node_id}"}} {temp}')

    lines.append("# HELP tmu_node_battery_percent Current battery percentage")
    lines.append("# TYPE tmu_node_battery_percent gauge")
    for node_id, data in latest_state.items():
        bat = data.get('battery', 0)
        lines.append(f'tmu_node_battery_percent{{node_id="{node_id}"}} {bat}')

    lines.append("# HELP tmu_node_fitness_score Computed marathoner score for task assignment")
    lines.append("# TYPE tmu_node_fitness_score gauge")
    for node_id, data in latest_state.items():
        score = data.get('score', 0)
        lines.append(f'tmu_node_fitness_score{{node_id="{node_id}"}} {score}')
    
    return Response("\n".join(lines) + "\n", mimetype="text/plain")

if __name__ == '__main__':
    port = int(os.environ.get("METRICS_PORT", 9090))
    print(f"[INFO] Starting TMU Prometheus Exporter on port {port}...")
    app.run(host='0.0.0.0', port=port, threaded=True)
