#!/usr/bin/env bash
# 🐺 Termux Master Ultra (TMU) - One-Click Deployment Script
# Branding: Official Husky/Malamute Swarm Control Plane
set -euo pipefail

MASTER_STORAGE="${MASTER_STORAGE:-$HOME/.termux_master}"
VERSION="1.0.0"

COLOR_RESET="\033[0m"
COLOR_GREEN="\033[32m"
COLOR_RED="\033[31m"
COLOR_BLUE="\033[34m"

log_info()    { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"; }
log_success() { echo -e "${COLOR_GREEN}[OK]${COLOR_RESET} $1"; }
log_error()   { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"; }

show_banner() {
    echo "=========================================================="
    echo "  🐺 Termux Master Ultra (TMU) v${VERSION}              "
    echo "  Official Husky/Malamute Swarm Control Plane           "
    echo "=========================================================="
}

do_install() {
    show_banner
    log_info "Starting TMU installation..."
    
    # Create secure directories
    for dir in "$MASTER_STORAGE"/{logs,state,locks,dags,cluster/metrics}; do
        mkdir -p "$dir"
        chmod 700 "$dir"
    done
    log_success "Directories created at $MASTER_STORAGE"
    
    # Install dependencies
    pkg install python-flask -y 2>/dev/null || pip install flask
    
    # Generate secrets
    export TM_DASHBOARD_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    export TM_HMAC_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Write env file
    echo "TM_DASHBOARD_TOKEN=$TM_DASHBOARD_TOKEN" > "$MASTER_STORAGE/.env"
    echo "TM_HMAC_SECRET=$TM_HMAC_SECRET" >> "$MASTER_STORAGE/.env"
    log_warn "Secrets generated! View with: cat $MASTER_STORAGE/.env"
    
    # Write dashboard.py (full implementation)
    cat > "$MASTER_STORAGE/dashboard.py" << 'PYEOF'
#!/usr/bin/env python3
"""🐺 TMU Swarm Control Plane & Dashboard"""
import os, sys, time, json, hmac, hashlib, secrets, threading
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, abort, Response, render_template_string

MASTER_STORAGE = Path(os.environ.get("MASTER_STORAGE", str(Path.home() / ".termux_master"))).resolve()
STATE_DIR = MASTER_STORAGE / "state"
METRICS_DIR = MASTER_STORAGE / "cluster/metrics"

for d in (MASTER_STORAGE, STATE_DIR, METRICS_DIR):
    d.mkdir(parents=True, exist_ok=True)
    try: os.chmod(d, 0o700)
    except: pass

AUTH_TOKEN = os.environ.get("TM_DASHBOARD_TOKEN", secrets.token_hex(16))
HMAC_SECRET = os.environ.get("TM_HMAC_SECRET", secrets.token_hex(32)).encode('utf-8')

node_states = {}
ticket_lock = threading.Lock()
active_tickets = {}

def generate_ticket():
    with ticket_lock:
        t = secrets.token_urlsafe(32)
        active_tickets[t] = time.time() + 30.0
        return t

def consume_ticket(t):
    with ticket_lock:
        exp = active_tickets.pop(t, None)
        return bool(exp and time.time() < exp)

def sign(p):
    return hmac.new(HMAC_SECRET, json.dumps(p, sort_keys=True).encode(), hashlib.sha256).hexdigest()

def ledger(etype, pl):
    e = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "event": etype, "payload": pl, "sig": sign({"event": etype, "payload": pl})}
    p = STATE_DIR / "history.jsonl"
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps(e) + "\n"); f.flush(); os.fsync(f.fileno())
    except: pass

def battery_vel(nid, bat):
    sf = METRICS_DIR / f".bat_prev_{nid}"
    pb = float(sf.read_text().strip()) if sf.exists() else bat
    sf.write_text(str(bat))
    return bat - pb

def process_telem(nid, pl):
    pv = node_states.get(nid, {})
    cpu = float(pl.get("cpu", 0)); bat = float(pl.get("battery", 100)); tmp = float(pl.get("temp", 30))
    db = battery_vel(nid, bat)
    st = (0.4 * tmp) + (0.6 * pv.get("temp", tmp))
    sl = st - pv.get("tmp_prev", st)
    
    sc = max(0, min(100, ((100-cpu)*0.2)+(bat*0.4)-(30 if st>40 else 0)-(60 if st>45 else 0)-(sl*15 if sl>0 else 0)+(20 if db>0 else (-15 if db<0 else 0))))
    stt = "demoted" if st > 45 else "operational"
    if st > 45: ledger("BREACH", {"node_id": nid, "temp": st}); sc = 0
    
    node_states[nid] = {"node_id": nid, "cpu": round(cpu,1), "mem": 30, "battery": int(bat), "delta_bat": int(db), "temp": round(st,2), "slope": round(sl,2), "score": round(sc,2), "status": stt, "ts": time.time()}
    ledger("HEARTBEAT", {"node_id": nid, "status": stt, "score": sc})

app = Flask(__name__)

@app.route("/")
def idx(): return render_template_string('<h1>🐺 TMU Dashboard</h1><p>Status: <span id="st">Checking...</span></p><script>const t=sessionStorage.getItem("t");fetch("/api/sse-ticket",{headers:{"X-TM-Token":t}}).then(r=>r.json()).then(d=>{const e=new EventSource(`/api/events?ticket=${d.ticket}`);e.onopen=()=>document.getElementById("st").textContent="LIVE";e.addEventListener("telemetry",t=>console.log(t.data))})</script>')

@app.route("/api/status")
def stat():
    t = request.headers.get("X-TM-Token")
    if t != AUTH_TOKEN: return jsonify({"error":"Unauthorized"}), 401
    return jsonify({"nodes": node_states})

@app.route("/api/sse-ticket", methods=["POST"])
def ticket():
    t = request.headers.get("X-TM-Token")
    if t != AUTH_TOKEN: return jsonify({"error":"Unauthorized"}), 401
    return jsonify({"ticket": generate_ticket()})

@app.route("/api/events")
def evts():
    t = request.args.get("ticket")
    if not consume_ticket(t): abort(403)
    def gen():
        ls = {}
        while True:
            time.sleep(1)
            for n, s in node_states.items():
                if ls.get(n) != s["ts"]: ls[n] = s["ts"]; yield f"data: {json.dumps(s)}\n\n"
    return Response(gen(), mimetype="text/event-stream")

@app.route("/api/telemetry", methods=["POST"])
def tele():
    ct = request.content_type
    if ct and "json" not in ct.lower(): return jsonify({"error":"application/json required"}), 415
    t = request.headers.get("X-TM-Token")
    if t != AUTH_TOKEN: return jsonify({"error":"Unauthorized"}), 401
    data = request.get_json() or {}; nid = data.get("node_id")
    if not nid: return jsonify({"error":"Missing node_id"}), 400
    process_telem(nid, data)
    return jsonify({"status":"received"})

if __name__ == "__main__":
    ledger("BOOT", {"host": "127.0.0.1", "port": 8080})
    print(f"🐺 TMU Active on http://127.0.0.1:8080")
    app.run(host="127.0.0.1", port=8080, threaded=True)
PYEOF
    chmod +x "$MASTER_STORAGE/dashboard.py"
    
    # Write CLI launcher
    cat > "$MASTER_STORAGE/tm-master" << 'CLIEOF'
#!/usr/bin/env bash
case "$1" in
    up) nohup python3 "$HOME/.termux_master/dashboard.py" > "$HOME/.termux_master/logs/app.log" 2>&1 & sleep 2; echo "✅ Started dashboard on http://127.0.0.1:8080";;
    down) pkill -f dashboard.py; echo "✅ Stopped";;
    logs) tail -f "$HOME/.termux_master/logs/app.log";;
    *) echo "Usage: tm-master {up|down|logs}";;
esac
CLIEOF
    chmod +x "$MASTER_STORAGE/tm-master"
    ln -sf "$MASTER_STORAGE/tm-master" ~/tm-master 2>/dev/null || true
    
    log_success "Installation complete!"
    echo ""
    echo "Start services: ~/.termux_master/tm-master up"
    echo "View dashboard: http://127.0.0.1:8080"
    echo "Credentials: cat $MASTER_STORAGE/.env"
}

case "${1:-help}" in
    install) do_install;;
    *) show_banner; echo "Usage: $0 {install}";;
esac
