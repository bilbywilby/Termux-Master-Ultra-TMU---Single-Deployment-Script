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
        print(f"[WARN] Ledger file not found: {LEDGER_FILE}")
        return nodes
        
    try:
        with open(LEDGER_FILE, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Accept multiple event types: 'telemetry', 'HEARTBEAT_PROCESSED', etc.
                    event_type = data.get('event', '')
                    if event_type.lower() not in ['telemetry', 'heartbeat_processed', 'metric_update']:
                        continue
                    
                    # Try to extract node_id from payload first, then top-level
                    payload = data.get('payload', data)  # payload wrapper OR top-level
                    node_id = payload.get('node_id')
                    
                    if node_id:
                        # Extract all numeric fields that could become metrics
                        node_data = {}
                        for field in ['cpu', 'battery', 'temp', 'score', 'mem', 'delta_bat', 'slope']:
                            if field in payload:
                                node_data[field] = payload[field]
                        
                        # Store complete node state
                        nodes[node_id] = {
                            'node_id': node_id,
                            **node_data,
                            'status': payload.get('status', 'operational'),
                            'ts': data.get('ts', 0)
                        }
                except json.JSONDecodeError as e:
                    print(f"[WARN] Line {line_num} parse error: {e}")
                    continue
    except Exception as e:
        print(f"[ERROR] Failed to read ledger: {e}")
        
    if not nodes:
        print(f"[INFO] No nodes found in ledger ({list(LCDGER_FILE.glob('*.json*'))})")
    
    print(f"[DEBUG] Loaded {len(nodes)} nodes from ledger")
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
    
    if not lines:
        lines = ["# No nodes available"]
    
    return Response("\n".join(lines) + "\n", mimetype="text/plain")

if __name__ == '__main__':
    port = int(os.environ.get("METRICS_PORT", 9090))
    print(f"[INFO] Starting TMU Prometheus Exporter on port {port}...")
    print(f"[INFO] Reading ledger: {LEDGER_FILE}")
    app.run(host='0.0.0.0', port=port, threaded=True)
