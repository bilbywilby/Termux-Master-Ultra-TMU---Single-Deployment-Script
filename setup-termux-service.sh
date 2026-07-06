#!/usr/bin/env bash
# Configures Termux-services for TMU auto-start and crash resilience

set -euo pipefail

SERVICE_DIR="$PREFIX/var/service/tmu-dashboard"
RUN_SCRIPT="$SERVICE_DIR/run"
LOG_DIR="$SERVICE_DIR/log"
LOG_RUN_SCRIPT="$LOG_DIR/run"

echo "[INFO] Installing termux-services..."
pkg install termux-services -y > /dev/null 2>&1

echo "[INFO] Creating service directories..."
mkdir -p "$SERVICE_DIR"
mkdir -p "$LOG_DIR"

echo "[INFO] Writing run script..."
cat << 'EOF' > "$RUN_SCRIPT"
#!/data/data/com.termux/files/usr/bin/sh
# Redirect stderr to stdout for svlogd
exec 2>&1

# Source environment variables
ENV_FILE="$HOME/.termux_master/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Exec replaces the shell with the python process (required for correct PID tracking by sv)
exec python3 "$HOME/.termux_master/dashboard.py"
EOF

echo "[INFO] Writing log run script..."
cat << 'EOF' > "$LOG_RUN_SCRIPT"
#!/data/data/com.termux/files/usr/bin/sh
# Log output with automatic rotation using svlogd
exec svlogd -tt "$HOME/.termux_master/logs"
EOF

chmod +x "$RUN_SCRIPT"
chmod +x "$LOG_RUN_SCRIPT"

echo "[OK] Service configured. To enable on boot and start immediately:"
echo "  sv up tmu-dashboard"
echo "  sv-enable tmu-dashboard"
