#!/usr/bin/env python3
"""TMU Dashboard v1.3.0 - Full Telemetry Storage to Ledger"""
import os, json, hmac, hashlib, time
from pathlib import Path
from threading import Lock
from flask import Flask, request, jsonify, Response

STATE_DIR = Path.home() / ".termux_master" / "state"
KEY_FILE = STATE_DIR / "auth.key"
LOCK = Lock()
node_states = {}

def ensure_dirs(): 
    STATE_DIR.mkdir(parents=True, exist_ok=True); KEY_FILE.touch(exist_ok=True)
ensure_dirs()

AUTH_TOKEN = os.environ.get("TM_DASHBOARD_TOKEN", "")
if not AUTH_TOKEN:
    AUTH_TOKEN = "".join([chr(ord("A")+i%26) for i in range(16)])
    os.environ["TM_DASHBOARD_TOKEN"] = AUTH_TOKEN
    print(f"[WARN] TM_DASHBOARD_TOKEN not set; generated: {AUTH_TOKEN[:8]}...")

def sign(data): return hmac.new(b"TMU_SECRET", json.dumps(data).encode(), hashlib.sha256).hexdigest()
def ledger(etype, pl):
    print(f"DEBUG LEDGER ~/: keys={list(pl.keys())}")
    print(f"\047DEBUG: Ledger called with event '\047\047{etype}\047\047, keys: {list(pl.keys())}\047")
    print(f"047DEBUG: Ledger received event 047047047{etype}047047 with payload keys: {list(pl.keys())}")
    global LOCK
    e = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "event": etype, "payload": pl, "sig": sign({"event": etype, "payload": pl})}
    p = STATE_DIR / "history.jsonl"
    with LOCK:
        with open(p, "a") as f: f.write(json.dumps(e)+"\n"); f.flush()

# Pre-computed weights  
CPU_W, BAT_W, TEMP_W, SLOPE_W = 0.2, 0.5, 0.2, 0.3

def process_telem(nid, data):
    """Process incoming telemetry and store FULL data in ledger."""
    cpu = float(data.get("cpu", 0)); bat = float(data.get("battery", 100))
    temp = float(data.get("temp", 35)); mem = int(data.get("mem", 50))
    
    ns = node_states.setdefault(nid, {"cpu":cpu, "bat":bat, "temp":temp, "score":0, "status":"operational","delta_bat":0,"slope":0,"ts":time.time()})
    prev_sat = ns.copy(); delta_bat = bat - prev_sat.get("bat", bat)
    
    # Score calculation (unchanged from original)
    base = ((100-cpu)*CPU_W + bat*BAT_W); thermal_pen = 30 if temp>40 else 0
    slope = abs(temp - prev_sat.get("temp", temp)); slope_pen = slope*SLOPE_W
    power_adj = 20 if delta_bat>0 else (-15 if delta_bat<0 else 0)
    score = max(0, min(100, base - thermal_pen - slope_pen + power_adj))
    
    # Thermal breach
    stat = "demoted" if temp>=45 else ("overheated" if temp>=40 else "operational")
    if temp>=45: score=0
    
    # Update state with FULL telemetry data
    ns.update({"cpu":cpu, "battery":bat, "temp":temp, "mem":mem, "score":round(score,1),"status":stat,"delta_bat":delta_bat,"slope":round(slope,1),"ts":time.time()})
    
    # 🐺 CRITICAL FIX: Log COMPLETE telemetry to ledger (including cpu, temp, battery!)
    ledger("telemetry", {
        "node_id": nid,
        "cpu": cpu,           # ← ADDED
        "battery": bat,       # ← ADDED  
        "temp": temp,         # ← ADDED
        "mem": mem,           # ← ADDED
        "score": round(score,1),
        "status": stat
    })

tickets = {}; TICKET_TTL = 30
def generate_ticket():
    t = "".join(["ABCDEF0123456789"[int(c)%16] for c in str(time.time()).replace(".","")]); tickets[t]=time.time(); return t
def consume_ticket(t):
    if t not in tickets or time.time()-tickets[t]>TICKET_TTL: return False; del tickets[t]; return True

app = Flask(__name__)

@app.route("/")
def root(): return "🐺 TMU Active"

@app.route("/api/status")
def status(): 
    with LOCK: s = node_states.copy()
    return jsonify({"data": {k: {**v} for k, v in s.items()}, "count": len(s)})

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
        ls = {}; time.sleep(1)
        for n, st in node_states.items():
            if ls.get(n) != st["ts"]: ls[n] = st["ts"]; yield f"data: {json.dumps(st)}\n\n"
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
