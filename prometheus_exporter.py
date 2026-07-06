#!/usr/bin/env python3
"""TMU Prometheus Exporter - Production Ready v1.2.1"""
import os, json
from pathlib import Path
from flask import Flask, Response

app = Flask(__name__)
home = Path.home()
master_dir = Path(os.environ.get("MASTER_STORAGE", home / ".termux_master"))
ledger_file = master_dir / "state" / "history.jsonl"

@app.route('/metrics')
def get_metrics():
    """Export Prometheus metrics from TMU audit ledger."""
    nodes = {}
    
    # Read ledger if exists
    if ledger_file.exists():
        try:
            with open(ledger_file, 'r') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        item = json.loads(line)
                        payload = item.get('payload', item)
                        nid = payload.get('node_id')
                        if nid:
                            nodes[nid] = {
                                'cpu': float(payload.get('cpu', 0)),
                                'temp': float(payload.get('temp', 0)),
                                'battery': float(payload.get('battery', 0)),
                                'score': float(payload.get('score', 0)),
                                'status': payload.get('status', 'operational'),
                            }
                    except (json.JSONDecodeError, KeyError, TypeError): 
                        continue
        except IOError as e:
            print(f"[WARN] Cannot read ledger: {e}")
    
    # Build Prometheus format
    lines = []
    lines.append("# HELP tmu_node_cpu_usage_percent Current CPU utilization per node")
    lines.append("# TYPE tmu_node_cpu_usage_percent gauge")
    
    lines.append("# HELP tmu_node_temperature_celsius Current temperature in Celsius")
    lines.append("# TYPE tmu_node_temperature_celsius gauge")
    
    lines.append("# HELP tmu_node_battery_percent Current battery percentage")
    lines.append("# TYPE tmu_node_battery_percent gauge")
    
    lines.append("# HELP tmu_node_fitness_score Computed marathoner score")
    lines.append("# TYPE tmu_node_fitness_score gauge")
    
    for node_id, n in nodes.items():
        lines.append(f'tmu_node_cpu_usage_percent{{node_id="{node_id}"}} {n["cpu"]}')
        lines.append(f'tmu_node_temperature_celsius{{node_id="{node_id}"}} {n["temp"]}')
        lines.append(f'tmu_node_battery_percent{{node_id="{node_id}"}} {n["battery"]}')
        lines.append(f'tmu_node_fitness_score{{node_id="{node_id}"}} {n["score"]}')
    
    return Response('\n'.join(lines) + '\n', mimetype='text/plain')

if __name__ == '__main__':
    port = int(os.environ.get("METRICS_PORT", 9090))
    print(f"[INFO] TMU MetricsExporter started on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
