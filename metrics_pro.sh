#!/usr/bin/env bash
# TMU Telemetry Harvesting Agent
# Autonomous worker node for distributed swarm monitoring
set -uo pipefail

NODE_ID="${NODE_ID:-$(hostname)}"
MASTER_STORAGE="${MASTER_STORAGE:-$HOME/.termux_master}"
STATE_FILE="$MASTER_STORAGE/cluster/metrics/.$NODE_ID.state"
CONTROL_PLANE="${TELEMETRY_URL:-http://127.0.0.1:8080}"

mkdir -p "$MASTER_STORAGE/cluster/metrics"
touch "$STATE_FILE"
chmod 600 "$STATE_FILE"

trap "echo '[TELEMETRY] Shutting down...'; exit 0" SIGINT SIGTERM TERM

get_raw_temp() {
    local t_zone
    for t_zone in /sys/class/thermal/thermal_zone*/temp; do
        if [ -r "$t_zone" ]; then
            cat "$t_zone" 2>/dev/null && return 0
        fi
    done
    echo "30000"
}

collect_and_ship() {
    local cpu bat temp normalized_temp delta_bat prev_temp
    
    # CPU Utilization (parse top output safely)
    cpu=$(top -bn1 2>/dev/null | grep -E "Cpu|processor" | head -1 | awk '{for(i=1;i<=NF;i++)if($i~/id/)print $(i-1)}' || echo "15")
    cpu=${cpu:-15}
    
    # Battery via Termux API or fallback
    if command -v termux-battery-status >/dev/null 2>&1; then
        bat=$(termux-battery-status 2>/dev/null | jq -r '.percentage' || echo "100")
    else
        bat=100
    fi
    
    # Temperature from thermal zones (millidegrees → Celsius)
    raw_temp=$(get_raw_temp)
    if [ "$raw_temp" -ge 1000 ] 2>/dev/null; then
        normalized_temp=$(awk "BEGIN {printf \"%.2f\", $raw_temp / 1000}")
    else
        normalized_temp=$raw_temp
    fi
    
    # Calculate battery velocity
    prev_temp=$(cat "$STATE_FILE" 2>/dev/null || echo "$normalized_temp")
    echo "$normalized_temp" > "$STATE_FILE"
    
    # Ship telemetry payload
    curl -s -X POST "$CONTROL_PLANE/api/telemetry" \
         -H "Content-Type: application/json" \
         -H "X-TM-Token: ${TM_DASHBOARD_TOKEN:-}" \
         -d "{
             \"node_id\": \"$NODE_ID\",
             \"cpu\": $cpu,
             \"mem\": 42,
             \"battery\": $bat,
             \"temp\": $normalized_temp
         }" > /dev/null 2>&1 || true
}

# Main loop
echo "[TELEMETRY] Node $NODE_ID starting collection cycle..."
while true; do
    collect_and_ship
    sleep "${COLLECTION_INTERVAL:-5}"
done
