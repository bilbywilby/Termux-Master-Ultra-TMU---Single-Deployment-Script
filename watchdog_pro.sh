#!/usr/bin/env bash
# TMU Sovereign Leader Election Watchdog
# Implements lease-based distributed arbitration
set -euo pipefail

NODE_ID="${NODE_ID:-$(hostname)}"
MASTER_STORAGE="${MASTER_STORAGE:-$HOME/.termux_master}"
FLAG_FILE="$MASTER_STORAGE/cluster/i_am_leader.flag"
LEASE_TIMEOUT=60

mkdir -p "$MASTER_STORAGE/cluster"

validate_and_claim() {
    local age
    if [ -f "$FLAG_FILE" ]; then
        age=$(($(date +%s) - $(stat -c %Y "$FLAG_FILE")))
        if [ "$age" -gt "$LEASE_TIMEOUT" ]; then
            rm -f "$FLAG_FILE"
            echo "[WATCHDOG] Stale leader lease detected ($age seconds), releasing..."
        else
            echo "[WATCHDOG] Active leader lease held (age: ${age}s)"
            return 0
        fi
    fi
    
    # Prevent race conditions with randomized delay
    sleep "0.$((RANDOM % 900 + 100))"
    
    # Claim leadership
    touch "$FLAG_FILE"
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ') Node $NODE_ID claiming leadership]" >> "$FLAG_FILE"
    
    # Signal leadership acquisition
    echo "👑 NODE $NODE_ID is now LEADER"
    
    # Physical notification (optional torch flash)
    if command -v termux-torch >/dev/null 2>&1; then
        termux-torch on && sleep 0.3 && termux-torch off 2>/dev/null || true
    fi
    
    return 0
}

trap 'rm -f "$FLAG_FILE"; echo "[WATCHDOG] Terminating..."; exit 0' SIGINT SIGTERM TERM

echo "[WATCHDOG] Starting sovereign election monitor..."
while true; do
    validate_and_claim
    sleep 15
done
