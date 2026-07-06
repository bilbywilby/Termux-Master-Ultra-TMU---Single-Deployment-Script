#!/usr/bin/env bash
set -euo pipefail

MASTER_STORAGE="${MASTER_STORAGE:-$HOME/.termux_master}"
VERSION="1.0.0"

log_info() { echo "[INFO] $1"; }
log_success() { echo "[OK] $1"; }
log_warn() { echo "[WARN] $1"; }

do_install() {
    echo "=========================================================="
    echo "  🐺 Termux Master Ultra (TMU) v${VERSION}              "
    echo "  Official Husky/Malamute Swarm Control Plane           "
    echo "=========================================================="
    
    log_info "Starting installation..."
    
    for dir in "$MASTER_STORAGE"/{logs,state,locks,dags,cluster/metrics}; do
        mkdir -p "$dir"
        chmod 700 "$dir"
    done
    log_success "Directories created at $MASTER_STORAGE"
    
    pkg install python-flask -y 2>/dev/null || pip install flask
    
    if [ ! -f "$MASTER_STORAGE/.env" ]; then
        TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))")
        HMAC=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "TM_DASHBOARD_TOKEN=$TOKEN" > "$MASTER_STORAGE/.env"
        echo "TM_HMAC_SECRET=$HMAC" >> "$MASTER_STORAGE/.env"
        log_warn "Secrets generated! Saved to $MASTER_STORAGE/.env"
    else
        log_info "Existing configuration preserved..."
    fi
    
    if [ -f "dashboard.py" ]; then
        cp dashboard.py "$MASTER_STORAGE/dashboard.py"
        chmod +x "$MASTER_STORAGE/dashboard.py"
        log_success "Dashboard copied"
    else
        log_warn "dashboard.py not found!"
    fi
    
    if [ -f "tm-master" ]; then
        cp tm-master "$MASTER_STORAGE/tm-master"
        chmod +x "$MASTER_STORAGE/tm-master"
        ln -sf "$MASTER_STORAGE/tm-master" ~/tm-master 2>/dev/null || true
        log_success "CLI launcher copied"
    else
        log_warn "tm-master not found!"
    fi
    
    log_success "Installation complete!"
    echo "Start:   ~/.termux_master/tm-master up"
    echo "Web:     http://127.0.0.1:8080"
    echo "Config:  $MASTER_STORAGE/.env"
}

case "${1:-help}" in
    install) do_install;;
    *) echo "Usage: $0 {install}";;
esac
